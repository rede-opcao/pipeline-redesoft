FROM apache/airflow:3.3.2

# dbt em ambiente virtual separado para não conflitar com as dependências do Airflow
RUN python -m venv /home/airflow/dbt_venv \
 && /home/airflow/dbt_venv/bin/pip install --no-cache-dir "dbt-postgres==1.9.0"
