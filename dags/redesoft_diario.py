"""Carga diária da Cadastros API (dados do Redesoft) para o data lake.

Roda todo dia às 02:00 (America/Sao_Paulo):
  1. cadastros (snapshot completo) e movimento (janela D-N .. D-1) em paralelo;
  2. dbt build (staging -> gold + testes de qualidade).

Carga histórica: "Trigger DAG w/ config" com {"data_inicio": "2026-01-01", "data_fim": "2026-10-31"}.
A janela é fatiada automaticamente nos limites de dias de cada rota.
"""
from __future__ import annotations

from datetime import date, timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Param, dag, get_current_context, task

from redesoft.config import FONTES, Settings
from redesoft.pipeline import executar_fonte

TZ = "America/Sao_Paulo"


def _janela() -> tuple[date, date]:
    ctx = get_current_context()
    params = ctx["params"]
    if params.get("data_inicio") and params.get("data_fim"):
        return date.fromisoformat(params["data_inicio"]), date.fromisoformat(params["data_fim"])
    ref = ctx.get("logical_date") or ctx["dag_run"].run_after
    fim = pendulum.instance(ref).in_timezone(TZ).date() - timedelta(days=1)
    dias = int(params.get("dias_reprocessamento") or Settings.from_env().dias_reprocessamento)
    return fim - timedelta(days=dias - 1), fim


@dag(
    dag_id="redesoft_diario",
    # Sem agendamento enquanto a chave da Cadastros API não chega (a fonte ativa é o b2click_diario).
    schedule=None,
    start_date=pendulum.datetime(2026, 11, 1, tz=TZ),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    params={
        "dias_reprocessamento": Param(3, type="integer", minimum=1),
        "data_inicio": Param(None, type=["null", "string"], format="date"),
        "data_fim": Param(None, type=["null", "string"], format="date"),
    },
    tags=["redesoft", "cadastros-api"],
)
def redesoft_diario():
    @task(max_active_tis_per_dagrun=4)
    def extrair_fonte(nome: str) -> dict:
        ctx = get_current_context()
        inicio, fim = _janela()
        return executar_fonte(nome, run_id=ctx["run_id"], inicio=inicio, fim=fim)

    extracoes = [extrair_fonte.override(task_id=f"extrair_{f.nome}")(f.nome) for f in FONTES]

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=("cd /opt/airflow/dbt && /home/airflow/dbt_venv/bin/dbt build --select tag:cadastros_api "
                      "--profiles-dir . --target-path /tmp/dbt_target"),
    )

    extracoes >> dbt_build


redesoft_diario()
