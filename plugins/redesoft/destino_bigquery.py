"""Gravação das fatias do B2Click no BigQuery (alternativa ao PostgreSQL).

Cada fonte vira uma tabela em <BQ_PROJETO>.<BQ_DATASET_RAW>.<nome>, com uma coluna STRING por
campo do CSV (os nomes originais, ex.: COD_EMPRESA) e mais data_ref, run_id e carregado_em.

  cadastros (data_ref nulo) -> conteúdo inteiro apagado e recarregado
  dia / mês                 -> tabela particionada por data_ref; a fatia é apagada e recarregada

Campos novos que a API passar a enviar são acrescentados à tabela automaticamente.
Configuração por ambiente: BQ_PROJETO, BQ_LOCAL (padrão southamerica-east1), BQ_DATASET_RAW
(padrão raw_b2click). Credenciais: as padrão do Google (GOOGLE_APPLICATION_CREDENTIALS no PC,
conta de serviço da tarefa no Cloud Run).
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)

COLUNAS_CONTROLE = ("data_ref", "run_id", "carregado_em")


def nome_coluna(campo: str) -> str:
    """Nome válido no BigQuery: letras, dígitos e _; não começa com dígito."""
    n = re.sub(r"[^0-9A-Za-z_]", "_", campo.strip())
    return f"_{n}" if n[:1].isdigit() else n


def montar_linhas(regs: list[dict], data_ref: date | None, run_id: str) -> tuple[list[str], list[dict]]:
    colunas: list[str] = []
    vistos: set[str] = set()
    linhas = []
    agora = datetime.now(timezone.utc).isoformat()
    for r in regs:
        linha = {}
        for k, v in r.items():
            if k is None or not str(k).strip():
                continue  # linha com mais campos que o cabeçalho
            c = nome_coluna(k)
            if c in COLUNAS_CONTROLE:
                c = f"api_{c}"
            if c not in vistos:
                vistos.add(c)
                colunas.append(c)
            linha[c] = v
        linha.update({"data_ref": data_ref.isoformat() if data_ref else None, "run_id": run_id, "carregado_em": agora})
        linhas.append(linha)
    return colunas, linhas


class DestinoBigQuery:
    def __init__(self, projeto: str | None = None, local: str | None = None, dataset: str | None = None, client=None):
        self.projeto = projeto or os.environ.get("BQ_PROJETO")
        if not self.projeto:
            raise ValueError("Defina BQ_PROJETO para gravar no BigQuery.")
        self.local = local or os.environ.get("BQ_LOCAL", "southamerica-east1")
        self.dataset = dataset or os.environ.get("BQ_DATASET_RAW", "raw_b2click")
        if client is None:
            from google.cloud import bigquery
            endpoint = os.environ.get("BQ_ENDPOINT")  # só para testes com o emulador local
            if endpoint:
                from google.api_core.client_options import ClientOptions
                from google.auth.credentials import AnonymousCredentials
                client = bigquery.Client(project=self.projeto, credentials=AnonymousCredentials(),
                                         client_options=ClientOptions(api_endpoint=endpoint))
            else:
                client = bigquery.Client(project=self.projeto, location=self.local)
        self.client = client

    def tabela(self, nome: str) -> str:
        return f"{self.projeto}.{self.dataset}.{nome}"

    def substituir_fatia(self, nome: str, particionada_por: str | None, data_ref: date | None,
                         regs: list[dict], run_id: str) -> None:
        """particionada_por: None (cadastro), "DAY" ou "MONTH"."""
        from google.cloud import bigquery

        tabela = self.tabela(nome)
        colunas, linhas = montar_linhas(regs, data_ref, run_id)
        schema = ([bigquery.SchemaField(c, "STRING") for c in colunas] +
                  [bigquery.SchemaField("data_ref", "DATE"), bigquery.SchemaField("run_id", "STRING"),
                   bigquery.SchemaField("carregado_em", "TIMESTAMP")])
        corpo = io.BytesIO("\n".join(json.dumps(x, ensure_ascii=False) for x in linhas).encode("utf-8"))

        if particionada_por is None and not linhas:
            log.warning("%s: cadastro vazio; tabela mantida como estava", nome)
            return

        t = bigquery.Table(tabela, schema=schema)
        if particionada_por:
            t.time_partitioning = bigquery.TimePartitioning(type_=particionada_por, field="data_ref")
        self.client.create_table(t, exists_ok=True)
        if particionada_por is None:  # cadastro: substitui tudo
            self.client.query(f"DELETE FROM `{tabela}` WHERE TRUE").result()
        else:
            cfg_q = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", data_ref)])
            self.client.query(f"DELETE FROM `{tabela}` WHERE data_ref = @d", job_config=cfg_q).result()
        if linhas:
            cfg = bigquery.LoadJobConfig(
                schema=schema, write_disposition="WRITE_APPEND",
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION])
            self.client.load_table_from_file(corpo, tabela, job_config=cfg).result()


def gravar_gcs(uri: str, chave: str, dados: bytes) -> str:
    """Grava no Cloud Storage. uri: gs://bucket/prefixo"""
    from google.cloud import storage

    bucket, _, prefixo = uri[5:].partition("/")
    nome = f"{prefixo.rstrip('/')}/{chave}" if prefixo else chave
    storage.Client().bucket(bucket).blob(nome).upload_from_string(dados, content_type="application/gzip")
    return f"gs://{bucket}/{nome}"
