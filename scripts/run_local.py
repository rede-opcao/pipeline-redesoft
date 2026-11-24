"""Roda a extração fora do Airflow (útil para testar a API sem Docker).

Exemplos (PowerShell, na pasta do projeto):
    python scripts/run_local.py                         # mock, ontem e 2 dias antes
    python scripts/run_local.py --inicio 2026-11-01 --fim 2026-11-20
    python scripts/run_local.py --fontes empresas tanques bicos

Lê as mesmas variáveis de ambiente do .env (CADASTROS_API_MODE, CADASTROS_API_KEY, ...).
Sem WAREHOUSE_DSN, grava só no bronze (pasta data/bronze).
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "plugins"))

from redesoft.config import FONTES, Settings  # noqa: E402
from redesoft.pipeline import executar_fonte  # noqa: E402


def main() -> None:
    ontem = date.today() - timedelta(days=1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", type=date.fromisoformat, default=ontem - timedelta(days=2))
    ap.add_argument("--fim", type=date.fromisoformat, default=ontem)
    ap.add_argument("--fontes", nargs="*", default=[f.nome for f in FONTES])
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    s = Settings.from_env()
    if not Path(s.bronze_uri).is_absolute() and not s.bronze_uri.startswith("s3://"):
        s = Settings(**{**s.__dict__, "bronze_uri": str(RAIZ / s.bronze_uri)})
    run_id = "local__" + datetime.now().strftime("%Y%m%dT%H%M%S")
    print(f"modo={s.modo_api} janela={args.inicio}..{args.fim} bronze={s.bronze_uri}")
    for nome in args.fontes:
        r = executar_fonte(nome, run_id, args.inicio, args.fim, settings=s)
        print(f"  {nome:<20} {r['registros']:>8} registros -> {r['bronze']}")


if __name__ == "__main__":
    main()
