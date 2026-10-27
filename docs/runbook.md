# Runbook

Run commands from the repository root. Python 3.11 or newer is required. The default path does not need PostgreSQL, Docker, or network access after the wheels are installed.

## Install and run

```bash
python -m pip install -e ".[dev]"
bi-analytics run
pytest
```

`bi-analytics run` is the same program as `python -m bi_analytics run`.

Useful variants:

```bash
bi-analytics run --input data/raw --output /tmp/lumen-warehouse
bi-analytics run --skip-sql
bi-analytics run --log-level DEBUG
```

`--skip-sql` writes the Pandas KPI frames and does not open DuckDB. The default path executes `sql/kpis/*.sql` and stops if those results differ from Pandas.

## What a healthy run looks like

- Exit code 0
- `warehouse/fact_sales.csv` and `warehouse/dim_*.csv` exist
- `warehouse/kpis/executive_summary.csv` has one data row
- `warehouse/quality_report.json` has every `fk_checks` value set to `true`
- `warehouse/rejects.csv` lists quarantined source rows

On the committed sample the executive row is as-of 2025-06-30, net revenue 71708.97 EUR, margin 30390.97 EUR, 355 completed orders, return rate 0.0707. A change to `data/raw` or to the money rules will change those figures. The parity test, not the printed total, is the contract.

## Regenerate the sample

```bash
python scripts/generate_sample_data.py
bi-analytics run
```

The script uses a fixed seed. Dirty rows (duplicate customer, unknown keys, cancelled order, bad measures) are part of the file on purpose.

## Optional PostgreSQL

```bash
python -m pip install -e ".[postgres]"
cp .env.example .env
bi-analytics run --postgres
```

`DATABASE_URL` must start with `postgresql`. The loader drops the known views and tables, applies `sql/ddl/01_star_schema.sql`, appends the frames, and creates the KPI views. Table names come from a fixed list in the code. The SQL text comes from the files in this repository, not from the CSV contents.

Docker Compose does the same thing inside a container:

```bash
docker compose up --build
```

The `analytics` container exits after a successful load. PostgreSQL keeps running on port 5432. Demo login: database `bi_analytics`, user `bi`, password `bi`. Stop it with `docker compose down`. Add `-v` if you also want the volume removed.

Connect a SQL client:

```bash
psql "postgresql://bi:bi@localhost:5432/bi_analytics" -c "SELECT * FROM vw_kpi_executive_summary;"
```

## Failures

| Symptom | What to check |
| :--- | :--- |
| Exit code 2, `Missing source file` or `missing columns` | `INPUT_DIR` must contain the six CSV files named in `bi_analytics.schema.RAW_FILES`, with the expected headers |
| Exit code 2, `DATABASE_URL is required` | `--postgres` was set and the URL is empty. Export it or drop the flag |
| Exit code 2, `Star schema failed foreign-key checks` | A fact key was not found on its dimension. This is a pipeline bug, not a dirty source row. Dirty rows are quarantined earlier |
| Exit code 2, `SQL KPI views do not match` | A view in `sql/kpis/` drifted from `bi_analytics.kpis`. The error names the view. Fix the SQL or the Pandas function, then re-run `pytest` |
| Exit code 2, postgres extra missing | `pip install -e ".[postgres]"` |
| `bi-analytics: command not found` | The package is not installed in this interpreter. Use `python -m bi_analytics run` or reinstall the editable package |
| Power BI or Tableau shows no rows on a "last N days" filter | The sample ends on 2025-06-30. Filter the model calendar instead of the wall clock |
| DuckDB or PostgreSQL rejects a new view | Keep the SQL inside the shared subset: `CAST`, `ROUND(numeric, scale)`, `CASE`, `COUNT(DISTINCT ...)`, and integer `day_index`. Avoid `::` casts and date subtraction |

## Logs

Logging goes to stderr in the form `timestamp LEVEL logger message`. `--log-level` overrides `LOG_LEVEL`. SQLAlchemy engine logs are held at warning so a PostgreSQL load does not dump every insert.

## Tests before a change

```bash
pytest
```

Add a row to the hand scenario in `tests/conftest.py` when you change a business rule, and keep `tests/test_kpis.py` asserting both the hand total and SQL parity. `tests/test_sql_contract.py` checks that the DDL names every model column and that each KPI file parses as PostgreSQL.
