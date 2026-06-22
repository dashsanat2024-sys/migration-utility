# Migration Utility

Generic data migration engine with **FastAPI backend** and **React frontend** (v0.7.0).

## Stack

| Layer | Tech |
|-------|------|
| API | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| UI | React 19, Vite, React Router |
| Database | PostgreSQL 16 |
| Containers | Docker Compose |

### Field catalog API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/fields/{entity}` | Uploaded source/target field lists |
| POST | `/api/projects/{id}/fields/{entity}/source` | Upload source fields (CSV/JSON) |
| POST | `/api/projects/{id}/fields/{entity}/target` | Upload destination fields (CSV/JSON) |
| POST | `/api/projects/{id}/fields/{entity}/suggest-mappings` | Auto-suggest source→target pairs |
| POST | `/api/projects/{id}/fields/{entity}/apply-mappings/{rule_set_id}` | Apply mappings to a rule set |

Sample files: `samples/source_fields.csv`, `samples/target_fields_kraken.csv`

## Phase 6 — Reporting & Reconciliation (v0.7)

- **Project reconciliation dashboard** — staged rows, run counts, load totals, open ingest errors
- **Run-level funnel** — staged → selected → target loaded/failed with variance analysis
- **Match rate & status** — balanced / partial / variance reconciliation states
- **Sample record diff** — compare candidate source payload vs target load response
- **BI export** — JSON dataset for Metabase / Power BI (`export.json` download)
- **Reconciliation UI tab** — one-click run reconciliation view

### Reconciliation API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/reconciliation` | Project-level summary counts |
| GET | `/api/projects/{id}/reconciliation/export` | Full JSON dataset for BI |
| GET | `/api/projects/{id}/reconciliation/export.json` | Downloadable JSON file |
| GET | `/api/runs/{id}/reconciliation` | Run funnel, variance, samples |
| GET | `/api/runs/{id}/reconciliation/samples` | Sample payload diffs only |

## Phase 5 — Kraken & SAP Target Adapters (v0.6)

- **Kraken target adapter** — validates account payloads against Kraken schema, mock import API
- **SAP target adapter** — maps account fields to DEBMAS customer master, mock IDoc posting
- **Target validation** — pre-load checks against the target schema registry
- **Load record tracking** — persisted per run/batch with request/response payloads
- **File export adapter** — writes transformed JSON to `./data/exports/{project_id}/`
- **Runs UI** — target load summary table per migration run

### Load API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/runs/{id}/loads` | Load records for a run |
| GET | `/api/runs/{id}/loads/summary` | Loaded/failed counts |
| GET | `/api/projects/{id}/loads` | Recent load records for project |

Target adapters: `mock`, `file_export`, `kraken`, `sap`

Env vars: `KRAKEN_MOCK_MODE`, `KRAKEN_API_URL`, `SAP_MOCK_MODE`, `SAP_API_URL`, `EXPORT_PATH`

### Test with Kraken adapter

1. Create project with **Target Adapter** = `kraken` and **Target System** = `kraken`
2. Seed account rules (maps `id` → `accountId`, etc.)
3. Upload `samples/accounts.csv` → **Run Migration**
4. Open run details → **Target Load** table shows Kraken import responses

## Phase 4 — Data Mapping & Approval Workflow (v0.5)

- **Mapping matrix UI** — source ↔ target field grid with coverage stats
- **Role-based workflow** — Mapping Lead → Business Analyst → Product Owner sign-off
- **Approval history** — auditable transitions with actor, role, and comments
- **Tariff mapping** — separate source → target tariff codes with own workflow
- **Kraken product import** — load signed-off tariffs to target (mock adapter)
- **Target schema catalog** — Kraken/generic target fields for matrix alignment

### Mapping API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/mapping/rules/{id}/matrix` | Field mapping matrix |
| PUT | `/api/projects/{id}/mapping/rules/{id}/matrix` | Update mappings (draft/in_review) |
| GET | `/api/projects/{id}/mapping/rules/{id}/approvals` | Approval history |
| GET | `/api/projects/{id}/mapping/rules/{id}/workflow/options` | Allowed transitions by role |
| GET | `/api/projects/{id}/tariffs` | List tariff mapping sets |
| POST | `/api/projects/{id}/tariffs/seed` | Seed starter tariffs |
| POST | `/api/projects/{id}/tariffs/{id}/workflow` | Transition tariff workflow |
| POST | `/api/projects/{id}/tariffs/{id}/load` | Load signed-off tariffs to target |

Workflow roles: `mapping_lead`, `business_analyst`, `product_owner`

## Phase 3 — Candidate Selection & Batch Management (v0.4)

- **Switchable selection profiles** — configure criteria without code changes
- **Selection engine** — eq, in, contains, range, null checks with AND/OR logic
- **Volume limits** — `max_candidates` on profile or `candidate_limit` per run
- **Candidate records** — linked to batches with status tracking (selected → loaded)
- **Staging tagging** — selected rows tagged with `_batch_id` before pipeline runs
- **Preview API** — dry-run selection against staged data before migration

### Selection API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/selection/profiles` | List selection profiles |
| POST | `/api/projects/{id}/selection/profiles` | Create profile |
| POST | `/api/projects/{id}/selection/profiles/seed-account` | Seed default active-accounts profile |
| POST | `/api/projects/{id}/selection/profiles/{id}/criteria` | Add criterion |
| PATCH | `/api/projects/{id}/selection/profiles/{id}/criteria/{cid}` | Toggle criterion on/off |
| POST | `/api/projects/{id}/selection/preview` | Preview selection counts |
| GET | `/api/runs/{id}/candidates` | List candidates for a run |
| GET | `/api/batches/{id}/candidates` | List candidates for a batch |

Run config: `use_selection`, `selection_profile_id`, `candidate_limit`, `require_candidates`

## Phase 2 — Rules & Mapping (v0.3)

- **Validation engine** — required, format, in_list, range, cross_field, unique
- **Transform engine** — copy, lookup, concat, conditional, default, date_format, case
- **Rule sets** with versioning and workflow (draft → in_review → approved → signed_off)
- **Field mapping matrix** stored in PostgreSQL
- Rules applied automatically during migration validate & transform stages
- **Seed Account Rules** button in UI creates a starter approved rule set

### Rules API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/rules` | List rule sets |
| POST | `/api/projects/{id}/rules` | Create rule set |
| POST | `/api/projects/{id}/rules/seed-account` | Seed default account rules |
| POST | `/api/projects/{id}/rules/{id}/validation-rules` | Add validation rule |
| POST | `/api/projects/{id}/rules/{id}/field-mappings` | Add field mapping |
| POST | `/api/projects/{id}/rules/{id}/workflow` | Transition workflow state |

### Test with rules

1. Open project → **Rules & Mapping** → **Seed Account Rules**
2. Upload `samples/accounts.csv`
3. **Migration Runs** → Run Migration (uses approved rules automatically)

Run config options: `use_rules`, `rule_set_id`, `require_approved_rules`, `block_unapproved_rules`

## Quick start — Docker (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cd /Users/sanat/Migration_Utility

# Build and start all services (postgres + api + ui)
docker compose up --build -d

# Open the UI
open http://localhost:3000
```

| Service | URL |
|---------|-----|
| **React UI** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **Swagger** | http://localhost:8000/docs |
| **PostgreSQL** | localhost:5433 (user: `migration`, pass: `migration`) |

Stop: `docker compose down`

### Docker dev mode (hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---------|-----|
| Vite dev UI | http://localhost:5173 |
| API | http://localhost:8000 |

## Local development (without Docker UI)

### Backend

```bash
docker compose up postgres -d   # or use local PostgreSQL
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn migration_utility.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174** — Vite proxies `/api` to the backend.

## Using the UI

1. **Projects** — create a migration project (target system, connectors)
2. **Rules & Transforms** — create rule sets, add validation rules and transform mappings (lookup, concat, conditional, etc.)
3. **Candidate Selection** — configure criteria and preview migration candidates
4. **Data Mapping** — upload source/destination field catalogs, suggest mappings, edit field matrix
5. **Upload & Stage** — upload CSV/JSON/XML extract; valid rows go to staging tables
6. **Migration Runs** — click **Run Migration** (optionally apply selection profile)
7. **Reconciliation** — funnel view, variance analysis, sample diffs, BI export
8. **Ingest Errors** — review failed rows and reprocess after correction

## API endpoints

See Swagger at `/docs` or the Phase 1 table in this repo's history.

## Project layout

```
migration_utility/     # Python API
frontend/              # React UI
docker/                # Entrypoint scripts
docker-compose.yml     # Production-like stack
Dockerfile             # API image
```

## Tests

```bash
pytest
cd frontend && npm run build
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgres://migration:… | PostgreSQL connection |
| `LANDING_ZONE_PATH` | ./data/landing | Uploaded file storage |
| `EXPORT_PATH` | ./data/exports | File export adapter output |
| `KRAKEN_MOCK_MODE` | true | Use mock Kraken import (no live API) |
| `KRAKEN_API_URL` | https://api.kraken.tech/migration/v1 | Kraken API base URL |
| `SAP_MOCK_MODE` | true | Use mock SAP IDoc posting |
| `SAP_API_URL` | https://sap.example.local/idoc | SAP integration URL |
| `CORS_ORIGINS` | localhost:5173,3000 | Allowed frontend origins |
