"""Tarefa diária do pipeline Redesoft no Cloud Run (ambiente 3, sem Airflow).

Roda as extrações do B2Click (gravando no BigQuery e no Cloud Storage) e depois o dbt build.
Sai com código 1 se qualquer etapa falhar, para o Cloud Run marcar a execução como falha
(e o alerta do Monitoring avisar por e-mail).

Variáveis:
  DATA_INICIO / DATA_FIM   carga histórica (AAAA-MM-DD); sem elas, últimos DIAS_REPROCESSAMENTO dias até ontem
  DIAS_REPROCESSAMENTO     padrão 3
  FONTES                   lista separada por vírgula para rodar só algumas (padrão: todas)
  PULAR_DBT=1              só extrai
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app/plugins")
from redesoft.b2click import FONTES_B2C, executar_fonte_b2c  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("executar")


def janela() -> tuple[date, date]:
    if os.environ.get("DATA_INICIO") and os.environ.get("DATA_FIM"):
        return date.fromisoformat(os.environ["DATA_INICIO"]), date.fromisoformat(os.environ["DATA_FIM"])
    ontem = datetime.now(ZoneInfo("America/Sao_Paulo")).date() - timedelta(days=1)
    dias = int(os.environ.get("DIAS_REPROCESSAMENTO", "3"))
    return ontem - timedelta(days=dias - 1), ontem


def main() -> int:
    os.environ.setdefault("DESTINO", "bigquery")
    inicio, fim = janela()
    escolhidas = {x.strip() for x in os.environ.get("FONTES", "").split(",") if x.strip()}
    fontes = [f for f in FONTES_B2C if not escolhidas or f.nome in escolhidas]
    run_id = "cloudrun__" + os.environ.get("CLOUD_RUN_EXECUTION", datetime.now().strftime("%Y%m%dT%H%M%S"))
    log.info("janela %s..%s, %s fontes, destino=%s", inicio, fim, len(fontes), os.environ["DESTINO"])

    falhas = []
    for f in fontes:
        t0 = time.time()
        try:
            r = executar_fonte_b2c(f.nome, run_id=run_id, inicio=inicio, fim=fim)
            log.info("OK %s: %s registros, %s requisições, %.0fs", f.nome, r["registros"], r["requisicoes"], time.time() - t0)
        except Exception as e:  # segue para as outras fontes e falha no fim
            log.exception("FALHA %s: %s", f.nome, e)
            falhas.append(f.nome)

    if falhas:
        log.error("extrações com falha: %s (dbt não será executado)", ", ".join(falhas))
        return 1
    if os.environ.get("PULAR_DBT") == "1":
        return 0

    cmd = ["dbt", "build", "--select", "tag:b2click", "--target", os.environ.get("DBT_TARGET", "bigquery"),
           "--profiles-dir", "/app/dbt", "--project-dir", "/app/dbt", "--target-path", "/tmp/dbt_target"]
    log.info("executando: %s", " ".join(cmd))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
