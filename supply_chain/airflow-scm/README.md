# Airflow project (scm_pipeline)

Runs the daily supply chain pipeline with Astro CLI in Docker.

**DAG:** `scm_pipeline` (`@daily`, 1 retry)
`dbt deps` -> `dbt snapshot` -> `dbt run --full-refresh` -> `dbt test` -> `validate_issues.py`

If any dbt test fails, the DAG stops before the AI validation step.

**dbt models:** `include/dbt/` holds a copy of the models in `../models` so the Airflow image is self-contained. Edit models in `../models` and keep the two in sync.

**Run locally**
cp .env.example .env   # fill in your own values
astro dev start        # Airflow UI on http://localhost:8080

See `SETUP.md` for details.