"""Extrai uma fonte da API, grava o JSON bruto no bronze e carrega no schema raw do warehouse."""
from __future__ import annotations

import gzip
import io
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .client import CadastrosClient
from .config import FONTES_POR_NOME, Fonte, Settings

log = logging.getLogger(__name__)
FMT = "%Y-%m-%dT%H:%M:%S"


def criar_client(s: Settings) -> CadastrosClient:
    if s.modo_api == "mock":
        from .mock import MockCadastrosClient
        log.warning("CADASTROS_API_MODE=mock: usando dados SIMULADOS (fictícios)")
        return MockCadastrosClient(page_size=s.page_size)
    return CadastrosClient(s.api_url, api_key=s.api_key, client_id=s.client_id,
                           client_secret=s.client_secret, token_url=s.token_url,
                           scope=s.scope, page_size=s.page_size)


def janelas(inicio: date, fim: date, max_dias: int | None) -> list[tuple[date, date]]:
    """Divide [inicio, fim] (inclusivo) em pedaços de até max_dias dias."""
    if fim < inicio:
        raise ValueError(f"fim {fim} anterior a inicio {inicio}")
    if not max_dias:
        return [(inicio, fim)]
    out, atual = [], inicio
    while atual <= fim:
        ate = min(atual + timedelta(days=max_dias - 1), fim)
        out.append((atual, ate))
        atual = ate + timedelta(days=1)
    return out


# Credenciais que a API devolve dentro de EmpresaDto (inclusive aninhado em tanques/bicos).
# Nunca saem da memória: são removidas antes de gravar bronze e raw.
CAMPOS_SENSIVEIS = {"veederRootPassword", "veederRootLogin"}


def _sanitizar(obj):
    if isinstance(obj, dict):
        return {k: _sanitizar(v) for k, v in obj.items() if k not in CAMPOS_SENSIVEIS}
    if isinstance(obj, list):
        return [_sanitizar(v) for v in obj]
    return obj


def _buscar(client: CadastrosClient, fonte: Fonte, path: str, params: dict) -> list[dict]:
    if fonte.paginado:
        regs: list[dict] = []
        for pagina in client.iter_pages(path, params):
            regs.extend(pagina)
    else:
        dados = client.get_json(path, params)
        regs = dados if isinstance(dados, list) else [dados]
    return [_sanitizar(r) for r in regs]


def extrair(client: CadastrosClient, fonte: Fonte, inicio: date | None = None,
            fim: date | None = None, empresas: list[int] | None = None) -> list[dict]:
    if fonte.modo == "snapshot":
        if fonte.por_empresa:
            regs = []
            for emp in empresas or []:
                regs.extend(_buscar(client, fonte, fonte.path.format(codEmpresa=emp), dict(fonte.extra_params)))
            return regs
        return _buscar(client, fonte, fonte.path, dict(fonte.extra_params))

    if inicio is None or fim is None:
        raise ValueError(f"fonte incremental {fonte.nome} precisa de inicio e fim")
    regs = []
    for a, b in janelas(inicio, fim, fonte.janela_max_dias):
        params = {**fonte.extra_params,
                  fonte.param_inicio: datetime.combine(a, datetime.min.time()).strftime(FMT),
                  fonte.param_fim: datetime.combine(b, datetime.max.time().replace(microsecond=0)).strftime(FMT)}
        parte = _buscar(client, fonte, fonte.path, params)
        log.info("%s %s..%s: %s registros", fonte.nome, a, b, len(parte))
        regs.extend(parte)
    return regs


def gravar_bronze(regs: list[dict], fonte: Fonte, dt: date, run_id: str, bronze_uri: str) -> str:
    """Grava JSON Lines compactado em <bronze>/<fonte>/dt=<data>/<run_id>.jsonl.gz (local ou S3)."""
    seguro = "".join(c if c.isalnum() or c in "-_." else "_" for c in run_id)
    chave = f"{fonte.nome}/dt={dt.isoformat()}/{seguro}.jsonl.gz"
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        for r in regs:
            gz.write((json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8"))
    if bronze_uri.startswith("s3://"):
        import boto3
        bucket, _, prefixo = bronze_uri[5:].partition("/")
        key = f"{prefixo.rstrip('/')}/{chave}" if prefixo else chave
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
        return f"s3://{bucket}/{key}"
    destino = Path(bronze_uri) / chave
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(buf.getvalue())
    return str(destino)


DDL_RAW = """
create schema if not exists raw;
create table if not exists raw.{t} (
    id            bigserial primary key,
    run_id        text not null,
    janela_inicio date,
    janela_fim    date,
    carregado_em  timestamptz not null default now(),
    payload       jsonb not null
);
create index if not exists {t}_run_idx on raw.{t} (run_id);
"""


def carregar_raw(dsn: str, fonte: Fonte, regs: list[dict], run_id: str,
                 inicio: date | None, fim: date | None) -> int:
    """Append-only e idempotente por run_id (retentativa apaga o que a mesma execução já gravou).
    A deduplicação entre execuções é feita no dbt (camada staging)."""
    import psycopg2
    from psycopg2.extras import Json, execute_values

    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(DDL_RAW.format(t=fonte.nome))
        cur.execute(f"delete from raw.{fonte.nome} where run_id = %s", (run_id,))
        if not regs:
            return 0
        execute_values(cur, f"insert into raw.{fonte.nome} (run_id, janela_inicio, janela_fim, payload) values %s",
                       [(run_id, inicio, fim, Json(r)) for r in regs], page_size=1000)
    return len(regs)


def executar_fonte(nome: str, run_id: str, inicio: date | None = None, fim: date | None = None,
                   settings: Settings | None = None) -> dict:
    s = settings or Settings.from_env()
    fonte = FONTES_POR_NOME[nome]
    client = criar_client(s)
    empresas = None
    if fonte.por_empresa:
        empresas = [e["codEmpresa"] for e in extrair(client, FONTES_POR_NOME["empresas"])]
    if fonte.modo == "snapshot":
        inicio = fim = None
    regs = extrair(client, fonte, inicio, fim, empresas)
    dt = fim or datetime.now(timezone.utc).date()
    caminho = gravar_bronze(regs, fonte, dt, run_id, s.bronze_uri)
    carregados = carregar_raw(s.warehouse_dsn, fonte, regs, run_id, inicio, fim) if s.warehouse_dsn else None
    resumo = {"fonte": nome, "registros": len(regs), "bronze": caminho, "raw": carregados,
              "inicio": str(inicio) if inicio else None, "fim": str(fim) if fim else None}
    log.info("concluído: %s", resumo)
    return resumo
