# Alembic Migrations

Migrations are stored under `alembic/versions`. Use the following commands from the project root:

```bash
poetry run alembic revision --autogenerate -m "describe change"
poetry run alembic upgrade head
```

Set `DATABASE_URL` to point at the target database before running migrations. By default, Alembic falls back to the URL defined in `alembic.ini` (a local SQLite file for development/testing).
