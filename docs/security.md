# Security notes

This is a local batch tool. It is not an application with users, sessions, or a network API.

## What is in the repository

- Sample customers, emails, and orders are synthetic. Domains are `example.com`. Do not replace them with real personal data and commit the result.
- `.env` is gitignored. `.env.example` has no secret beyond the local demo database password.
- KPI SQL is static files under `sql/`. The runners do not concatenate CSV cell values into SQL text.
- PostgreSQL table and view names are taken from a fixed allow-list (`LOAD_ORDER` and `KPI_VIEWS`), not from file headers.

## What the demo database is

`docker-compose.yml` publishes PostgreSQL on port 5432 with user `bi` and password `bi`. That is a laptop credential so Power BI and Tableau can connect without extra setup.

- Do not reuse that password anywhere else.
- Do not expose port 5432 on a shared network.
- Do not point `--postgres` at a production instance with this compose file.
- Change the user, password, and network exposure before any shared environment. The loader will follow whatever `DATABASE_URL` you give it, including a remote host.

## What this tool does not do

- There is no authentication on the CLI. Anyone who can run it can read the input directory and write the output directory.
- There is no row-level security in the star schema. A store manager and a finance lead see the same fact.
- There is no encryption of `warehouse/` beyond whatever the disk already provides. The CSVs contain the full synthetic customer list.
- Promotion windows, product `is_active`, and country values are data-quality rules, not access-control rules.
- The Pandas and SQL paths are cross-checked against each other. That catches definition drift. It does not certify that the business rules are the ones a finance team signed off.

## Dependency surface

The default install is Pandas, Pydantic, pydantic-settings, and DuckDB. PostgreSQL support is an extra (`sqlalchemy`, `psycopg`) and is unused unless you pass `--postgres`. Tests add pytest and sqlglot. None of these are called with a service token.
