# Imagem da tarefa diária no Cloud Run (ambiente 3). Montar a partir da raiz do projeto:
#   docker build -f cloudrun/Dockerfile -t <imagem> .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    DESTINO=bigquery DBT_TARGET=bigquery \
    DBT_LOG_PATH=/tmp/dbt_logs DBT_SEND_ANONYMOUS_USAGE_STATS=false

RUN pip install "dbt-bigquery==1.9.1" google-cloud-bigquery google-cloud-storage

WORKDIR /app
COPY plugins/redesoft /app/plugins/redesoft
COPY dbt /app/dbt
COPY cloudrun/executar.py /app/executar.py
RUN rm -rf /app/dbt/target /app/dbt/logs /app/dbt/.user.yml

USER nobody
ENTRYPOINT ["python", "/app/executar.py"]
