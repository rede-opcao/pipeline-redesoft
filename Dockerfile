FROM apache/airflow:3.3.2

# Bibliotecas do Google para gravar no BigQuery e no Cloud Storage (DESTINO=bigquery)
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" google-cloud-bigquery google-cloud-storage

# dbt em ambiente virtual separado para não conflitar com as dependências do Airflow
RUN python -m venv /home/airflow/dbt_venv \
 && /home/airflow/dbt_venv/bin/pip install --no-cache-dir "dbt-postgres==1.9.0" "dbt-bigquery==1.9.1"
