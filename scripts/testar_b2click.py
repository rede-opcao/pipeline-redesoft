"""Testa (somente leitura) os endpoints da API B2Click listados no documento "APIS - atualizadas".

Uso:  python scripts/testar_b2click.py [--data 2026-11-23]
Lê B2CLICK_* do .env. Grava as respostas em data/b2click_teste/ (fora do git) e um resumo
em data/b2click_teste/_resumo.json. O token nunca é impresso.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "b2click_teste"

# endpoint -> "cad" (sem datas) | "per" (qualquer período) | "mes" (mês fechado: dia 1 ao último dia) | "estoque"
ENDPOINTS = {
    "agente": "cad", "centroDeCusto": "cad", "empresa": "cad", "setoresEstoque": "cad",
    "formaPagamento": "cad", "grupo": "cad", "planoContas": "cad", "produtos": "cad",
    "produtosUsoConsumo": "cad", "produtosAtivoImobilizado": "cad", "tabeladepreco": "cad",
    "bicos": "cad", "tanque": "cad", "cartaoTaxa": "cad", "titulosPagarEmAberto": "cad",
    "titulosReceberEmAberto": "cad",
    "Caixa": "mes", "contaCorrenteECaixa": "per", "conciliacao": "mes", "divisaoDeAgente": "per",
    "documento": "per", "itensdocumento": "per", "extratoBancario": "mes", "faturamento": "mes",
    "pagamentosDeVendas": "per", "itensPedido": "mes", "aberturaBicos": "mes",
    "medicaoTanques": "mes", "opnfEmVenda": "per", "pedidos": "mes", "razao": "per",
    "tanqueLMC": "mes", "titulo": "mes", "titulosEmAberto": "mes", "titulosQuitados": "mes",
    "tipoOPNF": "per", "usuario": "per", "vendas": "per", "notasSemEntrada": "mes",
    "vendaPagamentoCartao": "per", "balancete": "mes", "valorEstoque": "mes",
    "estoque": "estoque",
    # no documento "ITENS VENDIDOS" aponta para /grupo (erro de cópia); testando o nome provável:
    "itensVendidos": "per",
}


def carregar_env() -> dict:
    env = {}
    for linha in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, _, v = linha.partition("=")
            env[k.strip()] = v.strip()
    return env


def contar_csv(texto: str) -> tuple[int, list[str]]:
    import csv, io
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    return max(len(linhas) - 1, 0), (linhas[0] if linhas else [])


def contar(dados) -> tuple[int | None, list[str]]:
    """Acha a lista principal de registros e devolve (quantidade, campos do 1º registro)."""
    if isinstance(dados, list):
        return len(dados), list(dados[0].keys()) if dados and isinstance(dados[0], dict) else []
    if isinstance(dados, dict):
        for v in dados.values():
            if isinstance(v, list):
                return contar(v)
        return 1, list(dados.keys())
    return None, []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=date.fromisoformat, default=date.today() - timedelta(days=1))
    ap.add_argument("--endpoints", nargs="*", help="testar só estes")
    ap.add_argument("--codEmpresas", default="1", help="usado no endpoint estoque")
    args = ap.parse_args()
    env = carregar_env()
    base = env["B2CLICK_URL"].rstrip("/")
    auth = {"entidade": env["B2CLICK_ENTIDADE"], "usuario": env["B2CLICK_USUARIO"], "token": env["B2CLICK_TOKEN"]}
    d = args.data.strftime("%d%m%Y")
    SAIDA.mkdir(parents=True, exist_ok=True)
    resumo = []
    print(f"Testando endpoints, dia {args.data:%d/%m/%Y}\n")
    alvo = {k: v for k, v in ENDPOINTS.items() if not args.endpoints or k in args.endpoints}
    anterior = {}
    arq = SAIDA / "_resumo.json"
    if args.endpoints and arq.exists():
        anterior = {x["endpoint"]: x for x in json.loads(arq.read_text(encoding="utf-8"))}
    for ep, tipo in alvo.items():
        params = dict(auth)
        if tipo == "per":
            params |= {"datainicial": d, "datafinal": d}
        elif tipo == "mes":
            ini = args.data.replace(day=1)
            fim = (ini + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            params |= {"datainicial": ini.strftime("%d%m%Y"), "datafinal": fim.strftime("%d%m%Y")}
            if ep in ("balancete", "valorEstoque"):
                params["codEmpresas"] = args.codEmpresas
        elif tipo == "estoque":
            params |= {"data": d, "somenteCaixasProcessados": "true", "codEmpresas": args.codEmpresas}
        url = f"{base}/{ep}?{urllib.parse.urlencode(params)}"
        r = {"endpoint": ep, "tipo": tipo}
        t0 = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                        timeout=180) as resp:
                corpo = resp.read()
                r["http"] = resp.status
                r["content_type"] = resp.headers.get("Content-Type")
        except urllib.error.HTTPError as e:
            corpo = e.read()
            r["http"] = e.code
        except Exception as e:  # rede/timeout
            corpo, r["http"], r["erro"] = b"", None, type(e).__name__ + ": " + str(e).replace(auth["token"], "***")
        r["segundos"] = round(time.time() - t0, 1)
        r["bytes"] = len(corpo)
        try:
            if r.get("http") != 200:
                raise ValueError("http")
            if "csv" in (r.get("content_type") or ""):
                texto = corpo.decode("utf-8-sig", "replace")
                r["registros"], r["campos"] = contar_csv(texto)
                (SAIDA / f"{ep}.csv.gz").write_bytes(gzip.compress(corpo))
            else:
                r["registros"], r["campos"] = contar(json.loads(corpo.decode("utf-8-sig")))
                (SAIDA / f"{ep}.json.gz").write_bytes(gzip.compress(corpo))
        except Exception:
            r["registros"], r["campos"] = None, []
            r["inicio_resposta"] = corpo[:200].decode("utf-8", "replace").replace(auth["token"], "***")
        resumo.append(r)
        status = "OK " if r.get("http") == 200 and r["registros"] is not None else "ERRO"
        print(f"{status} {ep:<26} http={r.get('http')} {r['segundos']:>6}s "
              f"registros={r['registros']} campos={len(r['campos'])}")
    anterior.update({x["endpoint"]: x for x in resumo})
    (SAIDA / "_resumo.json").write_text(json.dumps(list(anterior.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResumo: {SAIDA / '_resumo.json'}")


if __name__ == "__main__":
    main()
