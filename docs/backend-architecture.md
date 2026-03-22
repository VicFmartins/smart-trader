# Backend Architecture

This refactor keeps the current MVP compatible while giving the codebase a cleaner local-first shape.
Working name: `Smart Trade`.

## Proposed Structure

```text
app/
  api/
    app.py                 # FastAPI app factory, lifespan, exception handlers
    dependencies.py        # shared FastAPI dependencies
    router.py              # central route registration
    routes/                # thin HTTP endpoints
  core/
    config.py              # environment settings and runtime defaults
    exceptions.py          # business and transport-safe exceptions
    logging.py             # logging bootstrap
    security.py            # JWT and password helpers
  db/
    base.py                # SQLAlchemy declarative base
    session.py             # engine and session factory
  models/                  # SQLAlchemy ORM models
  repositories/            # database access only
    accounts.py
    analytics.py
    assets.py
    clients.py
    ingestion_reports.py
    positions.py
    users.py
    pagination.py
  schemas/                 # Pydantic request/response contracts
  services/
    accounts.py            # account use cases
    analytics.py           # analytics queries and PDF generation
    assets.py              # asset use cases
    auth.py                # authentication flow
    clients.py             # client use cases
    import_pipeline.py     # upload + ETL orchestration
    ingestion_reports.py   # report lifecycle and review actions
    trades.py              # reserved trade-journal boundary
    taxes.py               # reserved tax-calculation boundary
    *_service.py           # compatibility shims for the current MVP
  etl/                     # pipeline internals kept behind ImportPipelineService
  lambda_handlers/         # AWS entrypoints
```

## Module Responsibilities

- `api`: transport layer only. Routes should parse input, call a service, and return a schema.
- `core`: app-wide policies such as config, logging, auth, and exceptions.
- `db`: vendor-aware database bootstrap. SQLite stays the default, but PostgreSQL remains a configuration change.
- `models`: persistence entities only.
- `repositories`: all SQLAlchemy query logic. This is the main seam that keeps PostgreSQL migration small later.
- `schemas`: stable request/response contracts for API and UI layers.
- `services`: business orchestration. This is where trades, analytics, taxes, and import workflows should live.
- `etl`: low-level parsing, normalization, enrichment, and loading utilities, now hidden behind the service layer.

## Why This Shape

- It preserves current routes and models.
- It introduces a real repository layer without adding a heavy abstraction framework.
- It creates clear service boundaries for future `trades`, `analytics`, `taxes`, and `import_pipeline` work.
- It keeps the app local-first by defaulting to SQLite while leaving PostgreSQL support in `db/session.py`.

## Next Domain Step

When the journal moves from portfolio positions to actual B3 trade events, add new ORM/Pydantic/repository/service modules in parallel:

- `models/trade.py`
- `schemas/trade.py`
- `repositories/trades.py`
- `services/trades.py`
- `services/taxes.py`

That will let the current MVP coexist with the trade journal transition instead of requiring a rewrite.
