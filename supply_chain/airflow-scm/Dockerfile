FROM astrocrpublic.azurecr.io/runtime:3.3-2-python-3.12
RUN python -m venv /usr/local/airflow/dbt_venv && \
    /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir \
        "dbt-core~=1.10.0" "dbt-oracle==1.10.0"