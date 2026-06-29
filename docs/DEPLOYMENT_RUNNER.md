# Deployment Guide — API, Worker & On-Prem Runner

**Version 0.9.0**

This guide covers customer-deployable migration execution: Docker Compose, async worker, proxy/mTLS, and environment variables introduced for enterprise (P0) features.

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  React UI   │────►│  FastAPI    │────►│  PostgreSQL      │
│  (static)   │     │  :8000      │     │  metadata/stage  │
└─────────────┘     └──────┬──────┘     └──────────────────┘
                           │
                           │ queues runs (status=queued)
                           ▼
                    ┌─────────────┐
                    │   Worker    │────► Destination APIs
                    │  (poll DB)  │      (via proxy/mTLS)
                    └─────────────┘
```

- **Sync mode (default):** `RUNNER_MODE=api` — creating a run executes inline in the API process.  
- **Async mode:** `RUNNER_MODE=worker` + worker container/process — API enqueues; worker executes.

---

## Docker Compose (recommended pilot)

```bash
cd Migration_Utility
docker compose up -d
```

Services:

| Service | Port | Role |
|---------|------|------|
| `postgres` | 5433→5432 | Database |
| `api` | 8000 | REST API |
| `frontend` | 3000→80 | React UI |
| `worker` | — | Polls queued migration runs |

Apply migrations on first API start (Alembic) or run:

```bash
docker compose exec api alembic upgrade head
```

---

## Worker process (standalone)

```bash
export DATABASE_URL=postgresql://migration:migration@localhost:5433/migration_utility
export RUNNER_MODE=worker
export ASYNC_RUNS_ENABLED=true
python -m migration_utility.worker.runner_worker
```

Poll interval: `WORKER_POLL_SECONDS` (default 5).

---

## Key environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | — | PostgreSQL connection |
| `LANDING_ZONE_PATH` | `./data/landing` | Uploaded file storage |
| `RUNNER_MODE` | `api` | `api` (sync) or `worker` (queue) |
| `ASYNC_RUNS_ENABLED` | `true` | Queue runs when worker mode |
| `RUN_CHUNK_SIZE` | `500` | Staging rows per pipeline chunk (cursor pagination; checkpoint resume) |
| `WORKER_POLL_SECONDS` | `5` | Worker idle poll |
| `AUTH_ENABLED` | `false` | Enable JWT login + RBAC |
| `AUTH_SECRET` | change-me | JWT signing secret |
| `AUTH_SEED_EMAIL` | admin@arthavi.local | First admin if no users |
| `AUTH_SEED_PASSWORD` | admin123 | Seed password |
| `HTTP_PROXY` / `HTTPS_PROXY` | — | Corporate egress proxy |
| `CLIENT_CERT_PATH` | — | mTLS client certificate |
| `CLIENT_KEY_PATH` | — | mTLS private key |
| `CA_BUNDLE_PATH` | — | Custom CA for TLS verify |
| `KRAKEN_MOCK_MODE` | `true` | `false` for live REST load |
| `KRAKEN_API_URL` | Kraken migration URL | Live import base |

---

## Proxy and mTLS

Outbound calls (live Kraken product/account import) use `migration_utility.network.http_client.build_http_client()`:

```bash
export HTTPS_PROXY=http://proxy.customer.corp:8080
export CLIENT_CERT_PATH=/certs/client.pem
export CLIENT_KEY_PATH=/certs/client-key.pem
export CA_BUNDLE_PATH=/certs/customer-ca.pem
```

Ensure the worker and API both receive these variables if either initiates outbound loads.

---

## Authentication (production pilot)

```bash
export AUTH_ENABLED=true
export AUTH_SECRET=$(openssl rand -hex 32)
export AUTH_SEED_EMAIL=migration-admin@customer.com
export AUTH_SEED_PASSWORD=<strong-password>
```

First login creates seed admin if the users table is empty. UI requires sign-in; workflow transitions use authenticated identity.

---

## Run lifecycle (async)

1. `POST /api/projects/{id}/runs` with `run_config.async: true` (or global `ASYNC_RUNS_ENABLED`) while `RUNNER_MODE=worker`  
2. Run status → `queued`  
3. Worker sets `running`, updates `progress_pct` through pipeline stages  
4. On failure: `checkpoint` saved; `POST /api/runs/{id}/resume` re-queues  
5. `GET /api/runs/{id}/progress` for polling

---

## Vercel / serverless note

The hosted demo runs API serverless without a co-located worker. Use **sync runs** there, or point the UI at a customer-deployed API+worker with `VITE_API_BASE`.

---

## Health checks

- Liveness (no DB): `GET /api/health/live`  
- Full health: `GET /api/health`

Warm the UI with `/api/health/live` on first paint to reduce cold-start latency.
