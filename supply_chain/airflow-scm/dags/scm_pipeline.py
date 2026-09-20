"""Supply-chain pipeline DAG.

Runs the whole chain in order, once a day (and on manual trigger):
  dbt deps -> dbt snapshot -> dbt run -> dbt test -> validate_issues.py

dbt runs from an isolated virtualenv baked into the image (see Dockerfile), so
its pinned versions never clash with Airflow's. The AI bot runs in Airflow's
own Python (oracledb / anthropic come from requirements.txt).
"""
from datetime import datetime

from airflow import DAG

try:  # Airflow 3
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:  # Airflow 2
    from airflow.operators.bash import BashOperator

DBT = "/usr/local/airflow/dbt_venv/bin/dbt"
DBT_DIR = "/usr/local/airflow/include/dbt"
SCRIPTS_DIR = "/usr/local/airflow/include/scripts"

with DAG(
    dag_id="scm_pipeline",
    description="Supply-chain: snapshot -> transform -> test -> AI validation",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 1},
    tags=["supply_chain"],
) as dag:

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_DIR} && {DBT} deps --profiles-dir .",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && {DBT} snapshot --profiles-dir .",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {DBT} run --full-refresh --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && {DBT} test --profiles-dir .",
    )

    validate_issues = BashOperator(
        task_id="validate_issues",
        bash_command=f"cd {SCRIPTS_DIR} && python validate_issues.py",
    )

    dbt_deps >> dbt_snapshot >> dbt_run >> dbt_test >> validate_issues
