# StockPilot backend

Copy `.env.example` to `.env`. Generate a secret with:
`python -c "import secrets; print(secrets.token_urlsafe(48))"`
Set the result as `JWT_SECRET_KEY`.

Install and run:
`pip install -e ".[dev]"`
`uvicorn app.main:app --reload`

Authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login (requires organization_id)
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/auth/me

Registration creates an organization, owner role, membership and default permissions.
Generate and review the auth_sessions migration:
`alembic revision --autogenerate -m "add auth sessions"`
`alembic upgrade head`
