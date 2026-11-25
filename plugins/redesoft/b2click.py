"""Extração da API REST do B2Click/Redesoft (retaguarda), somente leitura.

A API autentica por entidade/usuário/token na query string e responde CSV
(";" como separador, vírgula decimal, datas dd/mm/aaaa). Há três tipos de rota:

  cad  - cadastros, sem datas: carga completa a cada execução
  dia  - aceita qualquer período: buscada em blocos de até 7 dias e separada por dia (campo DATA)
  mes  - só aceita mês fechado (dia 1 ao último dia): extraído o mês inteiro

O raw guarda sempre a cópia mais recente de cada "fatia" (o cadastro inteiro,
um dia ou um mês): recarregar uma fatia apaga a versão anterior dela.

LIMITE DA API: 10 requisições por hora por serviço (endpoint) para a entidade inteira,
compartilhado com qualquer outro uso (ex.: relatórios do Power BI). Por isso o extrator
agrupa dias por chamada e, ao bater no limite, espera a próxima hora em vez de insistir.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FonteB2C:
    nome: str          # tabela raw_b2click.<nome> e pasta no bronze
    endpoint: str
    tipo: str          # "cad" | "dia" | "mes"
    descartar: frozenset = field(default_factory=frozenset)  # colunas que nunca são gravadas
    campo_data: str = "DATA"   # rotas "dia": coluna usada para separar o bloco por dia


FONTES_B2C = [
    FonteB2C("empresas", "empresa", "cad"),
    FonteB2C("produtos", "produtos", "cad"),
    FonteB2C("grupos_produto", "grupo", "cad"),
    FonteB2C("bicos", "bicos", "cad"),
    FonteB2C("tanques", "tanque", "cad"),
    FonteB2C("formas_pagamento", "formaPagamento", "cad"),
    FonteB2C("itens_vendidos", "itensVendidos", "dia"),
    FonteB2C("pagamentos_vendas", "pagamentosDeVendas", "dia"),
    FonteB2C("caixas", "Caixa", "mes"),
    FonteB2C("abertura_bicos", "aberturaBicos", "mes"),
    FonteB2C("tanque_lmc", "tanqueLMC", "mes"),
    FonteB2C("medicao_tanques", "medicaoTanques", "mes"),
]
FONTES_B2C_POR_NOME = {f.nome: f for f in FONTES_B2C}


class B2ClickError(Exception):
    pass


class B2ClickLimiteError(B2ClickError):
    """Limite de requisições por hora do serviço atingido."""


DIAS_POR_CHAMADA = 7
MAX_ESPERAS_LIMITE = 2


class B2ClickClient:
    def __init__(self, base_url: str, entidade: str, usuario: str, token: str,
                 timeout: int = 300, max_tentativas: int = 4):
        if not (entidade and usuario and token):
            raise ValueError("Defina B2CLICK_ENTIDADE, B2CLICK_USUARIO e B2CLICK_TOKEN.")
        self.base_url = base_url.rstrip("/")
        self._auth = {"entidade": entidade, "usuario": usuario, "token": token}
        self.timeout, self.max_tentativas = timeout, max_tentativas

    @classmethod
    def from_env(cls) -> "B2ClickClient":
        e = os.environ.get
        return cls(e("B2CLICK_URL", "https://retaguarda.b2click.com/b2click/rest/TModuloAPIb2click"),
                   e("B2CLICK_ENTIDADE", ""), e("B2CLICK_USUARIO", ""), e("B2CLICK_TOKEN", ""))

    def _ocultar(self, texto: str) -> str:
        return texto.replace(self._auth["token"], "***")

    def get_csv(self, endpoint: str, params: dict | None = None) -> bytes:
        """GET com espera automática até a próxima hora se o limite por hora for atingido."""
        for espera in range(MAX_ESPERAS_LIMITE + 1):
            try:
                return self._get_csv(endpoint, params)
            except B2ClickLimiteError:
                if espera == MAX_ESPERAS_LIMITE:
                    raise
                agora = datetime.now()
                prox = (agora + timedelta(hours=1)).replace(minute=1, second=30, microsecond=0)
                segundos = (prox - agora).total_seconds()
                log.warning("%s: limite de requisições/hora atingido; aguardando %.0f min", endpoint, segundos / 60)
                time.sleep(segundos)
        raise RuntimeError("inalcançável")

    def _get_csv(self, endpoint: str, params: dict | None = None) -> bytes:
        url = f"{self.base_url}/{endpoint}?" + urllib.parse.urlencode({**self._auth, **(params or {})})
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                req = urllib.request.Request(url, headers={"Accept": "text/csv"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    corpo = resp.read()
                    if "csv" not in (resp.headers.get("Content-Type") or ""):
                        raise B2ClickError(f"{endpoint}: resposta não é CSV: {self._ocultar(corpo[:200].decode('utf-8', 'replace'))}")
                    return corpo
            except urllib.error.HTTPError as e:
                msg = self._ocultar(e.read().decode("utf-8", "replace"))[:400]
                if "limite de" in msg.lower() and "requisi" in msg.lower():
                    raise B2ClickLimiteError(f"{endpoint}: {msg}") from None
                if e.code >= 500 and tentativa < self.max_tentativas:
                    log.warning("%s HTTP %s (tentativa %s): %s", endpoint, e.code, tentativa, msg)
                    time.sleep(5 * tentativa)
                    continue
                raise B2ClickError(f"{endpoint} HTTP {e.code}: {msg}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if tentativa < self.max_tentativas:
                    log.warning("%s falha de rede (tentativa %s): %s", endpoint, tentativa, self._ocultar(str(e)))
                    time.sleep(5 * tentativa)
                    continue
                raise B2ClickError(f"{endpoint}: {self._ocultar(str(e))}") from None
        raise RuntimeError("inalcançável")


def ler_csv(corpo: bytes, descartar: frozenset = frozenset()) -> list[dict]:
    texto = corpo.decode("utf-8-sig", "replace")
    return [{k: v for k, v in linha.items() if k not in descartar}
            for linha in csv.DictReader(io.StringIO(texto), delimiter=";")]


def _fmt(d: date) -> str:
    return d.strftime("%d%m%Y")


def chamadas(fonte: FonteB2C, inicio: date | None, fim: date | None) -> list[tuple[date | None, date | None, dict]]:
    """Lista de (inicio_bloco, fim_bloco, parâmetros), uma por requisição à API."""
    if fonte.tipo == "cad":
        return [(None, None, {})]
    if inicio is None or fim is None:
        raise ValueError(f"{fonte.nome} precisa de inicio e fim")
    if fim < inicio:
        raise ValueError(f"fim {fim} anterior a inicio {inicio}")
    out = []
    if fonte.tipo == "dia":
        a = inicio
        while a <= fim:
            b = min(a + timedelta(days=DIAS_POR_CHAMADA - 1), fim)
            out.append((a, b, {"datainicial": _fmt(a), "datafinal": _fmt(b)}))
            a = b + timedelta(days=1)
        return out
    mes = inicio.replace(day=1)
    while mes <= fim:
        ultimo = (mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        out.append((mes, mes, {"datainicial": _fmt(mes), "datafinal": _fmt(ultimo)}))
        mes = ultimo + timedelta(days=1)
    return out


def separar_por_dia(regs: list[dict], campo: str, a: date, b: date) -> dict[date, list[dict]]:
    """Agrupa os registros de um bloco por dia. Todo dia do bloco aparece (mesmo vazio),
    para que a substituição apague versões antigas de dias que ficaram sem registros."""
    dias = {a + timedelta(days=i): [] for i in range((b - a).days + 1)}
    for r in regs:
        try:
            d = datetime.strptime((r.get(campo) or "")[:10], "%d/%m/%Y").date()
        except ValueError:
            d = None
        dias.setdefault(d if d in dias else b, []).append(r)
    return dias


def gravar_bronze(corpo: bytes, fonte: FonteB2C, data_ref: date | None, run_id: str, bronze_uri: str) -> str:
    seguro = "".join(c if c.isalnum() or c in "-_." else "_" for c in run_id)
    dt = (data_ref or datetime.now(timezone.utc).date()).isoformat()
    chave = f"b2click/{fonte.nome}/dt={dt}/{seguro}.csv.gz"
    dados = gzip.compress(corpo)
    if bronze_uri.startswith("gs://"):
        from .destino_bigquery import gravar_gcs
        return gravar_gcs(bronze_uri, chave, dados)
    if bronze_uri.startswith("s3://"):
        import boto3
        bucket, _, prefixo = bronze_uri[5:].partition("/")
        key = f"{prefixo.rstrip('/')}/{chave}" if prefixo else chave
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=dados)
        return f"s3://{bucket}/{key}"
    destino = Path(bronze_uri) / chave
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return str(destino)


DDL = """
create schema if not exists raw_b2click;
create table if not exists raw_b2click.{t} (
    id           bigserial primary key,
    run_id       text not null,
    data_ref     date,
    carregado_em timestamptz not null default now(),
    payload      jsonb not null
);
create index if not exists {t}_ref_idx on raw_b2click.{t} (data_ref);
"""


def substituir_fatia(dsn: str, fonte: FonteB2C, data_ref: date | None, regs: list[dict], run_id: str) -> None:
    """Troca a fatia (cadastro inteiro, dia ou mês) de forma atômica."""
    import psycopg2
    from psycopg2.extras import Json, execute_values

    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(DDL.format(t=fonte.nome))
        if data_ref is None:
            cur.execute(f"delete from raw_b2click.{fonte.nome}")
        else:
            cur.execute(f"delete from raw_b2click.{fonte.nome} where data_ref = %s", (data_ref,))
        if regs:
            execute_values(cur, f"insert into raw_b2click.{fonte.nome} (run_id, data_ref, payload) values %s",
                           [(run_id, data_ref, Json(r)) for r in regs], page_size=2000)


def executar_fonte_b2c(nome: str, run_id: str, inicio: date | None, fim: date | None,
                       bronze_uri: str | None = None, dsn: str | None = None,
                       client: B2ClickClient | None = None) -> dict:
    fonte = FONTES_B2C_POR_NOME[nome]
    client = client or B2ClickClient.from_env()
    bronze_uri = bronze_uri or os.environ.get("BRONZE_URI", "data/bronze")
    destino = os.environ.get("DESTINO", "postgres").lower()
    bq = None
    if destino == "bigquery":
        from .destino_bigquery import DestinoBigQuery
        bq = DestinoBigQuery()
    else:
        dsn = dsn if dsn is not None else os.environ.get("WAREHOUSE_DSN")
    particao = {"cad": None, "dia": "DAY", "mes": "MONTH"}[fonte.tipo]
    total, partes = 0, []
    for a, b, params in chamadas(fonte, inicio, fim):
        corpo = client.get_csv(fonte.endpoint, params)
        regs = ler_csv(corpo, fonte.descartar)
        gravar_bronze(corpo, fonte, a, run_id, bronze_uri)
        fatias = separar_por_dia(regs, fonte.campo_data, a, b) if fonte.tipo == "dia" else {a: regs}
        for data_ref, parte in fatias.items():
            if bq is not None:
                bq.substituir_fatia(fonte.nome, particao, data_ref, parte, run_id)
            elif dsn:
                substituir_fatia(dsn, fonte, data_ref, parte, run_id)
            partes.append({"data_ref": str(data_ref) if data_ref else None, "registros": len(parte)})
        log.info("%s %s..%s: %s registros (1 requisição)", nome, a or "cadastro", b or "", len(regs))
        total += len(regs)
    return {"fonte": nome, "registros": total, "requisicoes": len(chamadas(fonte, inicio, fim)), "fatias": partes}


if __name__ == "__main__":  # teste rápido: python -m redesoft.b2click empresas
    import sys
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(executar_fonte_b2c(sys.argv[1], "manual", None, None, dsn=""), ensure_ascii=False))
