# StockPilot backend

## Configure

Copy `.env.example` to `.env` and set `DATABASE_URL`.

## Run locally

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open:
- Swagger UI: http://localhost:8000/docs
- Liveness: http://localhost:8000/api/v1/health/live
- Readiness: http://localhost:8000/api/v1/health/ready

## Test

```bash
pytest -q
```

The liveness endpoint checks that the process is responding. The readiness endpoint checks database connectivity. Do not use the liveness endpoint as a dependency health check.
