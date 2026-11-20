# StockPilot — Database foundation

Initial SQLAlchemy 2.x / Alembic foundation for the StockPilot inventory platform.

## Included
- Organization and membership model
- Organization-scoped roles and permissions
- Product catalogue and warehouses
- Inventory balances, movements, reservations
- Orders and order items
- Composite foreign keys for same-tenant relationships
- PostgreSQL and Redis development services
- Async SQLAlchemy engine and Alembic environment

## Start local dependencies

```bash
docker compose up -d
```

## Set up backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
export DATABASE_URL="postgresql+asyncpg://stockpilot:stockpilot@localhost:5432/stockpilot"
```

## Generate and review initial migration

```bash
alembic revision --autogenerate -m "initial schema"
```

Review the migration, then:

```bash
alembic upgrade head
```

## Important design notes

- Application authorization and database constraints are both required.
- Composite foreign keys prevent cross-organization references for key relationships.
- PostgreSQL RLS policies are intentionally a follow-up migration. They require a carefully designed transaction-scoped tenant context and connection-pool handling; enabling them before that would risk leaking or blocking legitimate requests.
- Inventory balance changes and inventory ledger inserts must be committed in the same transaction.
- `inventory_movements` is an append-only audit ledger by application convention. Enforce this with database permissions/triggers before production.
- AI-generated SQL must use a read-only database role and a separate, tenant-safe execution path.
