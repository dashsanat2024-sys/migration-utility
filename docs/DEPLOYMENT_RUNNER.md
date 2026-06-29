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
| `LOAD_BATCH_SIZE` | `200` | Records per destination API call (Kraken sub-batch) |
| `LOAD_CONCURRENCY` | `4` | Parallel destination load batches |
| `LOAD_MAX_RPS` | `0` | Max destination requests/sec (`0` = unlimited) |
| `LOAD_RETRY_MAX` | `5` | Retries on HTTP 429 / `KT-CT-1199` with exponential backoff |
| `LOAD_IDEMPOTENT` | `true` | Skip records already loaded for project+entity (URN dedup) |
| `WORKER_ID` | *(auto)* | Worker identity in logs and `claimed_by` (`hostname-pid` if empty) |
| `LOAD_AUDIT_MODE` | `full` | `full` = all load rows; `summary` = sample payloads + counts only |
| `LOAD_AUDIT_SAMPLE_SIZE` | `10` | Max loaded/failed samples persisted per batch in summary mode |
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

## Scaling workers

Multiple worker processes can run in parallel; each claims a distinct queued run via PostgreSQL `SKIP LOCKED`.

```bash
# Docker Compose — 4 parallel workers
docker compose up --scale worker=4

# Kubernetes — set replicas on the worker Deployment; set WORKER_ID from pod name
```

Do **not** set a fixed `container_name` on the worker service when scaling Compose replicas.

## Connection pooling (PgBouncer)

For 4+ worker replicas, point `DATABASE_URL` at **PgBouncer** (transaction or session pool) instead of PostgreSQL directly:

```bash
# Example — PgBouncer in front of Postgres
DATABASE_URL=postgresql://migration:migration@pgbouncer:6432/migration_utility
```

Use **session** pooling if you rely on `FOR UPDATE SKIP LOCKED` across long-running worker transactions; **transaction** pooling is fine when each claim+commit is a short unit of work (current worker design).

## Daily wave programme (Phase 5)

Schedule N parallel queued runs (e.g. 5 × 10,000 accounts = 50k/day):

```bash
curl -X POST "$API/api/projects/$PROJECT_ID/waves" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cutover day 1",
    "wave_count": 5,
    "accounts_per_wave": 10000,
    "require_health_gate": true,
    "max_failure_pct": 10,
    "run_config": { "use_rules": true, "use_selection": true, "async": true }
  }'
```

- **Health gate:** requires a recent `POST /account-health/assess` unless `require_health_gate: false`
- **Auto-pause:** if a wave run fails or load failure % exceeds `max_failure_pct`, the plan pauses and cancels remaining queued runs
- **Cron:** call the endpoint each morning or use `POST .../waves/{id}/resume` after operator review

| Variable | Default | Purpose |
|----------|---------|---------|
| `WAVE_REQUIRE_HEALTH_GATE` | `true` | Block scheduling without cohort readiness |
| `WAVE_DEFAULT_MIN_COHORT_SCORE` | `85` | Minimum cohort score |
| `WAVE_DEFAULT_MAX_BLOCKED_PCT` | `5` | Max % blocked accounts |
| `WAVE_DEFAULT_MAX_FAILURE_PCT` | `10` | Auto-pause threshold per wave run |

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
