"""Teste do destino BigQuery e do SQL do dbt num emulador local do BigQuery (sem conta Google).

Usa as amostras reais salvas por scripts/testar_b2click.py (data/b2click_teste/*.csv.gz) e:
  1. grava as fatias no emulador com DestinoBigQuery (o mesmo código da produção);
  2. executa o SQL compilado do dbt (target bigquery) para staging e gold;
  3. mostra contagens e totais para conferir com o PostgreSQL.

Rodar dentro da imagem do Cloud Run, na mesma rede do emulador (ver README).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "/app/plugins")
from google.api_core.client_options import ClientOptions  # noqa: E402
from google.auth.credentials import AnonymousCredentials  # noqa: E402
from google.cloud import bigquery  # noqa: E402

from redesoft.b2click import FONTES_B2C_POR_NOME, ler_csv  # noqa: E402
from redesoft.destino_bigquery import DestinoBigQuery  # noqa: E402

PROJETO = os.environ.get("BQ_PROJETO", "teste-local")
EMULADOR = os.environ.get("BQ_EMULADOR", "http://bq-emu:9050")
AMOSTRAS = Path("/amostras")
COMPILADO = Path("/tmp/dbt_target/compiled/redesoft/models")

# arquivo de amostra -> (fonte, data_ref)
ARQUIVOS = {
    "empresa": ("empresas", None), "produtos": ("produtos", None), "grupo": ("grupos_produto", None),
    "bicos": ("bicos", None), "tanque": ("tanques", None), "formaPagamento": ("formas_pagamento", None),
    "itensVendidos": ("itens_vendidos", date(2026, 11, 1)),
    "pagamentosDeVendas": ("pagamentos_vendas", date(2026, 11, 1)),
    "Caixa": ("caixas", date(2026, 11, 1)), "aberturaBicos": ("abertura_bicos", date(2026, 11, 1)),
    "tanqueLMC": ("tanque_lmc", date(2026, 11, 1)), "medicaoTanques": ("medicao_tanques", date(2026, 11, 1)),
}
PARTICAO = {"cad": None, "dia": "DAY", "mes": "MONTH"}


def main() -> None:
    client = bigquery.Client(project=PROJETO, credentials=AnonymousCredentials(),
                             client_options=ClientOptions(api_endpoint=EMULADOR))
    for ds in ("raw_b2click", "staging", "gold"):
        client.create_dataset(f"{PROJETO}.{ds}", exists_ok=True)

    destino = DestinoBigQuery(projeto=PROJETO, local="US", client=client)
    print("== 1. gravação das fatias")
    for arq, (nome, data_ref) in ARQUIVOS.items():
        corpo = gzip.decompress((AMOSTRAS / f"{arq}.csv.gz").read_bytes())
        regs = ler_csv(corpo)
        fonte = FONTES_B2C_POR_NOME[nome]
        destino.substituir_fatia(nome, PARTICAO[fonte.tipo], data_ref, regs, "teste")
        # segunda gravação da mesma fatia: não pode duplicar
        destino.substituir_fatia(nome, PARTICAO[fonte.tipo], data_ref, regs, "teste2")
        n = list(client.query(f"select count(*) n from `{PROJETO}.raw_b2click.{nome}`").result())[0].n
        print(f"  {nome:<20} csv={len(regs):>7} tabela={n:>7} {'OK' if n == len(regs) else 'DIVERGENTE'}")

    print("== 2. SQL do dbt (staging -> gold)")
    ordem = sorted((COMPILADO / "staging" / "b2click").glob("*.sql")) + [
        COMPILADO / "gold" / f"{m}.sql" for m in
        ("dim_empresa", "dim_tanque", "fct_vendas_diario", "fct_pagamentos_diario", "fct_afericao_bico_turno",
         "fct_vendas_tanque_diario", "fct_conciliacao_tanque_diario")]
    falhas = 0
    for f in ordem:
        camada = "staging" if "staging" in f.parts else "gold"
        sql = f.read_text(encoding="utf-8")
        tipo = "VIEW" if camada == "staging" else "TABLE"
        # o emulador não implementa views; materializa tudo como tabela
        ddl = f"CREATE OR REPLACE TABLE `{PROJETO}.{camada}.{f.stem}` AS\n{sql}"
        try:
            client.query(ddl).result()
            n = list(client.query(f"select count(*) n from `{PROJETO}.{camada}.{f.stem}`").result())[0].n
            print(f"  OK   {camada}.{f.stem:<32} {n:>7} linhas ({tipo} em produção)")
        except Exception as e:
            falhas += 1
            msg = re.sub(r"\s+", " ", str(e))[:300]
            print(f"  ERRO {camada}.{f.stem}: {msg}")

    if not falhas:
        print("== 3. totais")
        for q in [
            "select count(distinct cod_empresa) postos, round(sum(quantidade)) litros, round(sum(valor_total)) faturamento "
            f"from `{PROJETO}.gold.fct_vendas_diario` where especie = 'COMBUSTIVEL'",
            "select status, count(*) n from "
            f"`{PROJETO}.gold.fct_conciliacao_tanque_diario` group by status order by n desc",
            "select round(sum(saida_encerrante)) saida, round(sum(afericao_litros)) afericao, "
            "round(sum(litros_vendidos)) vendido, round(sum(diferenca_litros)) diferenca "
            f"from `{PROJETO}.gold.fct_afericao_bico_turno`",
        ]:
            for linha in client.query(q).result():
                print("  ", json.dumps(dict(linha.items()), default=str, ensure_ascii=False))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
