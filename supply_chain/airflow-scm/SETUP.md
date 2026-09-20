# Wiring the Airflow DAG -- setup steps

Do these in order, inside your `airflow-scm/` Astro project.

1. COPY YOUR DBT PROJECT into `include/dbt/`
   Copy the contents of your dbt project -- dbt_project.yml, packages.yml,
   models/, snapshots/ (and seeds/ if any) -- into `airflow-scm/include/dbt/`.
   Do NOT copy your local ~/.dbt/profiles.yml; this package provides a
   container profiles.yml at include/dbt/profiles.yml (wallet-free TLS).

2. UNZIP THIS PACKAGE into `airflow-scm/` (overwrite when asked).
   It adds:
     dags/scm_pipeline.py
     include/dbt/profiles.yml
     include/scripts/db.py
     include/scripts/validate_issues.py
     requirements.txt
     .env.example
     DOCKERFILE_APPEND.txt

3. EDIT THE DOCKERFILE
   Open airflow-scm/Dockerfile and paste the contents of DOCKERFILE_APPEND.txt
   at the bottom (below the existing FROM line).

4. CREATE .env
   Copy .env.example to .env, then fill in DB_PASSWORD and ANTHROPIC_API_KEY.
   (DB_HOST / DB_SERVICE are already your values.) Confirm .env is git-ignored.

5. REBUILD & START
   In the airflow-scm/ folder:
       astro dev restart
   (restart, not start -- it rebuilds the image with the Dockerfile +
   requirements changes). Wait for it to finish and open localhost:8080.

6. RUN THE DAG
   In the Airflow UI, find `scm_pipeline`, toggle it ON (unpause), then click
   the play/trigger button. Watch the five tasks turn green in order.
   Click any task -> Logs to see its output.

Troubleshooting
- A task fails on connection: check .env values and that your current IP is in
  the ADB access control list (the container uses your machine's public IP).
- dbt task can't find profiles: it uses `--profiles-dir .` with cwd=include/dbt,
  so profiles.yml must be in include/dbt/ (step 2 places it there).
