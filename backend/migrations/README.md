# Alembic migrations

After starting PostgreSQL and setting `DATABASE_URL`:

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
```

Review the generated migration before applying it. Autogeneration is a draft, not a substitute for reviewing constraints, indexes, and dependency ordering.

```bash
alembic upgrade head
alembic current
```

For later model changes:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Do not use `Base.metadata.create_all()` as the production schema management strategy.
