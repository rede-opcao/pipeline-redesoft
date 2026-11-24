"""Carga diária da API do B2Click/Redesoft (retaguarda) para o data lake.

Todo dia às 02:00 (America/Sao_Paulo):
  1. cadastros (completo), rotas diárias (D-3 .. D-1) e rotas mensais (mês inteiro
     de cada mês tocado pela janela), com no máximo 3 chamadas simultâneas à API;
  2. dbt build dos modelos do B2Click (staging -> gold + testes).

Carga histórica: "Trigger DAG w/ config" com {"data_inicio": "2026-01-01", "data_fim": "2026-10-31"}.
"""
from __future__ import annotations

from datetime import date, timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Param, dag, get_current_context, task

from redesoft.b2click import FONTES_B2C, executar_fonte_b2c

TZ = "America/Sao_Paulo"


def _janela() -> tuple[date, date]:
    ctx = get_current_context()
    p = ctx["params"]
    if p.get("data_inicio") and p.get("data_fim"):
        return date.fromisoformat(p["data_inicio"]), date.fromisoformat(p["data_fim"])
    ref = ctx.get("logical_date") or ctx["dag_run"].run_after
    fim = pendulum.instance(ref).in_timezone(TZ).date() - timedelta(days=1)
    return fim - timedelta(days=int(p.get("dias_reprocessamento") or 3) - 1), fim


@dag(
    dag_id="b2click_diario",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz=TZ),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    params={
        "dias_reprocessamento": Param(3, type="integer", minimum=1),
        "data_inicio": Param(None, type=["null", "string"], format="date"),
        "data_fim": Param(None, type=["null", "string"], format="date"),
    },
    tags=["b2click", "redesoft"],
)
def b2click_diario():
    @task(max_active_tis_per_dagrun=3)
    def extrair(nome: str) -> dict:
        ctx = get_current_context()
        inicio, fim = _janela()
        return executar_fonte_b2c(nome, run_id=ctx["run_id"], inicio=inicio, fim=fim)

    extracoes = [extrair.override(task_id=f"extrair_{f.nome}")(f.nome) for f in FONTES_B2C]

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=("cd /opt/airflow/dbt && /home/airflow/dbt_venv/bin/dbt build --select tag:b2click "
                      "--profiles-dir . --target-path /tmp/dbt_target_b2click"),
    )

    extracoes >> dbt_build


b2click_diario()
