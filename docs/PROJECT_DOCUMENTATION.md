# Migration Utility — Technical Documentation

**Version:** 0.8.0  
**Last updated:** June 2026  
**Repository:** https://github.com/dashsanat2024-sys/migration-utility  
**Live UI:** https://migration-utility.vercel.app

---

## 1. Executive summary

Migration Utility is a **generic, industry-aware data migration platform** for moving structured records from legacy source systems to modern destination platforms. It provides a full lifecycle: extract → validate → transform → load → reconcile, with configuration entirely driven from the UI.

The product is designed to be **vendor-neutral in the UI** (source / destination terminology instead of specific system names) while supporting pluggable connectors and adapters under the hood.

**Primary use case (v0.8):** Utilities industry data migration with **destination-as-plugin** architecture — the destination plugin publishes its schema contract; source fields map onto that fixed contract (Kraken-style migrations).

**Previous (v0.7):** Generic source/destination field catalog uploads for both sides.

See [PLUGIN_SCHEMA_DESIGN.md](./PLUGIN_SCHEMA_DESIGN.md) for the plugin architecture deep dive.

**Future industries:** Banking, healthcare, and generic migrations are scaffolded in the profile model but marked “Coming soon.”

---

## 2. Problem statement

Enterprise data migrations typically involve:

- Multiple spreadsheet-driven mapping specifications (field maps, tariff maps, validation rules)
- Ad-hoc scripts per migration wave
- Weak audit trails and approval workflows
- No single place to upload extracts, preview transformed JSON, and track load results

Migration Utility consolidates these into one configurable engine with a guided wizard, rule engine, and reconciliation dashboards.

---

## 3. High-level architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         React UI (Vite + React 19)                      │
│  Dashboard │ Migration Wizard │ Mapping │ Rules │ Runs │ Reconciliation │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ REST /api/*
┌───────────────────────────────▼─────────────────────────────────────────┐
│                    FastAPI Application (Python 3.11+)                   │
│  Routes │ ValidationEngine │ TransformEngine │ WorkflowEngine │ Pipeline│
└───────┬─────────────────────────────┬───────────────────┬─────────────┘
        │                             │                   │
        ▼                             ▼                   ▼
┌───────────────┐           ┌─────────────────┐   ┌──────────────────┐
│  PostgreSQL   │           │  Landing zone   │   │ Target adapters  │
│  (metadata,   │           │  (file uploads) │   │ mock, file_export│
│   rules, runs)│           │  CSV/JSON/XML   │   │ api_import, sap  │
└───────────────┘           └─────────────────┘   └──────────────────┘
```

### Pipeline stages

Every migration run executes four stages in order:

| Stage | Purpose |
|-------|---------|
| **Ingest** | Read staged rows from source connector (typically file-based staging tables) |
| **Validate** | Apply validation rules from approved rule sets |
| **Transform** | Apply field mappings and transform logic → destination JSON shape |
| **Load** | Send payloads to destination adapter (REST API, file export, mock) |

Implementation: `migration_utility/core/pipeline.py` orchestrates stages via `migration_utility/rules/pipeline_hooks.py`.

---

## 4. Technology stack

### Backend

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| API framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic (7 revisions, phases 0–6) |
| Database | PostgreSQL 16 |
| Settings | pydantic-settings |
| Serverless adapter | Mangum (Vercel) |
| Testing | pytest, httpx TestClient |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | React 19 |
| Build tool | Vite 6 |
| Routing | React Router 7 |
| Styling | Custom CSS (CSS variables, dark theme) |
| Fonts | DM Sans, JetBrains Mono |
| API client | Fetch-based `frontend/src/api/client.js` |

### Infrastructure & deployment

| Environment | Stack |
|-------------|-------|
| **Local / Docker** | Docker Compose: PostgreSQL + API + Nginx frontend |
| **Production UI + API** | Vercel (React static + Python serverless `/api`) |
| **Production DB** | Neon PostgreSQL (pooled connection, SSL) |
| **CI** | GitHub → Vercel auto-deploy on `main` |

---

## 5. Project profile model (industry-aware configuration)

Each migration **project** stores a JSON profile in `project.config.profile`:

```json
{
  "migration_type": "data_migration",
  "industry": "utility",
  "integration_approach": "api",
  "features": {
    "tariff_mapping": true,
    "validation_rules": true,
    "transform_rules": true
  }
}
```

### Migration types

| ID | Status | Description |
|----|--------|-------------|
| `data_migration` | Active | Structured record migration |
| `document_migration` | Coming soon | Document/metadata migration |
| `db_migration` | Coming soon | Schema-aware DB replication |

### Industries

| ID | Status | Features |
|----|--------|----------|
| `utility` | Active | Field mapping, tariff mapping, transforms |
| `generic` | Active | Field mapping, transforms (no tariffs) |
| `banking` | Coming soon | — |
| `healthcare` | Coming soon | — |

### Integration approaches

| ID | Status | Source | Destination |
|----|--------|--------|-------------|
| `api` | Active | File upload / mock | REST API import / file export |
| `file` | Active | File upload | JSON file export |
| `database` | Coming soon | Staging | File export |
| `hybrid` | Coming soon | Mixed | Mixed |

Profile drives:

- **Migration Wizard steps** (`buildWizardSteps` in `frontend/src/constants/migrationProfile.js`)
- **Visible project tabs** (`buildProjectTabs`)
- **Pipeline labels** shown in the wizard header

---

## 6. UI design

### Design principles

1. **Wizard-first** — New users follow a step checklist rather than hunting tabs
2. **Profile-driven** — UI adapts to industry (e.g. tariff step only for utilities)
3. **Generic language** — “Source / Destination” instead of vendor names in labels
4. **Dark, data-dense** — Tables, stats cards, workflow steppers for operational users

### Visual system

Defined in `frontend/src/styles/app.css`:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#0f1419` | Page background |
| `--bg-card` | `#1e2a3a` | Cards, panels |
| `--primary` | `#3b82f6` | Actions, active states |
| `--success` | `#22c55e` | Completed steps, OK status |
| `--error` | `#ef4444` | Errors, failed loads |
| `--font` | DM Sans | UI text |
| `--mono` | JetBrains Mono | Field names, JSON, code |

### Application structure

```
/                          → Dashboard (project list, create project)
/projects/:projectId       → Project workspace (tabbed + wizard)
```

### Project creation flow (4-step setup)

Implemented in `frontend/src/components/ProjectForm.jsx`:

1. **Migration type** — card selection grid
2. **Industry** — card selection grid
3. **Integration approach** — card selection grid
4. **Project details** — name, slug, connectors, optional tariff toggle

Uses `StepChecklist` component for progress indication.

### Migration Wizard (primary workflow)

Implemented in `frontend/src/components/MigrationWizard.jsx`:

| Step | Component | Purpose |
|------|-----------|---------|
| Overview | Built-in | Profile summary + checklist |
| Extract | Upload form | Stage CSV/JSON/XML extracts |
| Field mapping | `FieldCatalogPanel` | Upload catalogs, suggest & apply mappings |
| Transform rules | `TransformRulesStep` | Validation rules + custom transform types |
| Tariff mapping | `TariffWizardStep` | Optional product/rate band mapping (utilities) |
| Execute | Built-in | Approve rules, preview JSON, run migration |

Layout: **left sidebar step checklist** + **main content panel** (`wizard-layout` CSS grid).

### Additional project tabs

| Tab | Panel | Purpose |
|-----|-------|---------|
| Upload & Stage | `IngestPanel` | File upload, staging stats |
| Rules & Transforms | `RulesPanel` | Full rule set CRUD |
| Data Mapping | `MappingPanel` | Matrix, catalog upload, tariffs sub-tabs |
| Tariff Mapping | `TariffWizardStep` | Utilities tariff grid |
| Candidate Selection | `CandidatesPanel` | Selection profiles & preview |
| Migration Runs | `RunsPanel` | Start runs, view load results |
| Reconciliation | `ReconciliationPanel` | Funnel, variance, BI export |
| Ingest Errors | `ErrorsPanel` | Failed row review |

### Key UI components

| Component | Role |
|-----------|------|
| `StepChecklist` | Vertical numbered step navigator with done/current states |
| `FieldCatalogPanel` | Source/destination catalog upload, suggest mappings, per-row transform config |
| `TransformConfigEditor` | Dynamic config UI per transform type (lookup table, pad_left, etc.) |
| `TariffWizardStep` | Source→destination tariff row editor + CSV import |
| `WorkflowStepper` | Draft → in_review → approved → signed_off visual stepper |
| `StatusBadge` | Colored pill for run/load/workflow states |

---

## 7. Backend implementation

### Directory layout

```
migration_utility/
├── main.py                 # FastAPI app factory, CORS, router registration
├── config.py               # Environment settings (DATABASE_URL, CORS, adapters)
├── api/
│   ├── routes/             # REST endpoints by domain
│   ├── schemas.py          # Pydantic request/response models
│   └── deps.py             # DI: DB session, registries
├── core/
│   ├── pipeline.py         # MigrationPipeline orchestrator
│   ├── events.py           # EventBus for stage lifecycle
│   └── enums.py            # PipelineStage, AuditAction, etc.
├── connectors/
│   ├── staging.py          # Source: read from per-project staging tables
│   ├── builtin.py          # Mock source/target, file export
│   ├── kraken.py           # REST API import adapter (internal key)
│   └── sap.py              # SAP IDoc adapter (internal key)
├── rules/
│   ├── engine.py           # ValidationEngine + TransformEngine
│   ├── loader.py           # RuleLoader from DB
│   ├── service.py          # RuleSet CRUD + workflow
│   └── pipeline_hooks.py   # Stage implementations
├── ingest/                 # File parsing, landing zone, staging tables
├── mapping/                # Mapping matrix service
├── fields/                 # Field catalog upload + suggest + apply
├── selection/              # Candidate selection engine
├── tariff/                 # Tariff mapping sets
├── reconciliation/         # Dashboard + BI export
├── workflow/               # Role-based approval state machine
└── datastore/
    ├── models/             # SQLAlchemy ORM models
    └── session.py          # Engine (NullPool on Vercel, SSL for Neon)
```

### Database schema (Alembic migrations)

| Migration | Phase | Tables / changes |
|-----------|-------|------------------|
| 001 | 0 | `projects`, `migration_runs`, `batches`, `audit_logs` |
| 002 | 1 | `ingest_files`, `ingest_errors`, dynamic staging tables |
| 003 | 2 | `rule_sets`, `validation_rules`, `field_mappings` |
| 004 | 3 | `selection_profiles`, `selection_criteria`, `candidates` |
| 005 | 4 | `mapping_approvals`, `tariff_mapping_sets`, `tariff_mappings` |
| 006 | 5 | `load_records` |
| 007 | 6 | `field_catalogs` |

### Rule engine

**Validation types** (`ValidationEngine`):

- `required`, `format` (regex), `in_list`, `range`, `cross_field`, `unique`

**Transform types** (`TransformEngine`):

| Type | Config | Example use |
|------|--------|-------------|
| `copy` | — | Direct field copy |
| `constant` | `{ value }` | Hardcoded supplier ID |
| `default` | `{ value }` | Fallback when empty |
| `lookup` | `{ map, default }` | Enumeration mapping |
| `concat` | `{ fields, separator }` | Join name parts |
| `conditional` | `{ when, then, else }` | Complaint flag logic |
| `uppercase` / `lowercase` | — | Title normalization |
| `date_format` | `{ input_format, output_format }` | Date reformatting |
| `pad_left` | `{ width, char }` | 9-digit account numbers |
| `regex_replace` | `{ pattern, replacement }` | Strip “AdVAT” from rate bands |

Custom transform types can be registered per project in `project.config.custom_transforms` and appear in the UI dropdown.

### Workflow engine

Rule sets and tariff sets follow the same state machine:

```
draft → in_review → approved → signed_off
```

Roles: `mapping_lead`, `business_analyst`, `product_owner`

Only `draft` and `in_review` states allow mapping edits. Runs can require approved/signed-off rule sets via run config flags.

### Destination plugins (v0.8)

Each destination is a **plugin** that publishes its schema contract via `get_schema()`. The UI fetches this contract — users no longer upload destination field catalogs in the normal flow.

| Plugin ID | Adapter key | Entity | Description |
|-----------|-------------|--------|-------------|
| `kraken-billing-v3` | `kraken` | account, tariff | Kraken billing CRM import (18+ fields) |
| `sap-crm-v1` | `sap` | account | SAP DEBMAS customer master |
| `file-export-v1` | `file_export` | account | JSON file export |
| `mock-v1` | `mock` | account | Test destination |

API:
- `GET /api/destination/plugins` — list plugins
- `GET /api/projects/{id}/destination/schema?entity=account` — published contract
- `POST /api/projects/{id}/destination/swap` — swap plugin (with orphan confirmation)

Implementation: `migration_utility/plugins/`

### Connectors & adapters

| Key | Type | Description |
|-----|------|-------------|
| `staging` | Source | Reads from PostgreSQL staging tables populated by file upload |
| `mock` | Source/Target | Test data generator / echo loader |
| `file_export` | Target | Writes transformed JSON to `EXPORT_PATH` |
| `kraken` | Target | REST API import (UI label: “REST API import”) |
| `sap` | Target | SAP customer master (UI label: “ERP API import”) |

Registry: `migration_utility/connectors/registry.py`

### Field catalog & schema mapping flow

1. **Destination schema** fetched from active plugin (`GET .../destination/schema`)
2. Upload **source** field list (CSV/JSON) → `field_catalogs.source_fields`
3. `POST suggest-mappings?destination_first=true` — destination-first fuzzy matching
4. User maps source fields into destination sockets in **Schema & Mapping** UI
5. `POST apply-mappings/{rule_set_id}` — writes `field_mappings` rows

Legacy: manual destination catalog upload still supported via `POST .../fields/{entity}/target`.

Parser: `migration_utility/fields/catalog_parser.py`

### Tariff mapping

Each tariff row stores:

- `source_code` — composite key (product|rateband|dates)
- `target_code` — destination rate band code
- `config` (JSONB) — full row metadata (zones, charge type, dates, etc.)

Utilities can import `samples/utility/tariff_mapping.csv`.

---

## 8. API surface

Base path: `/api`

Interactive docs: `/docs` (Swagger UI)

### Core endpoints

| Domain | Prefix | Key operations |
|--------|--------|----------------|
| Health | `/health` | DB + connector status |
| Projects | `/projects` | CRUD, PATCH config |
| Ingest | `/projects/{id}/ingest` | Upload, list files, staging stats |
| Rules | `/projects/{id}/rules` | Rule sets, validation, mappings, workflow, preview-transform |
| Fields | `/projects/{id}/fields` | Catalog upload, suggest, apply |
| Mapping | `/projects/{id}/mapping` | Matrix, approvals, workflow options |
| Tariffs | `/projects/{id}/tariffs` | Tariff sets, mappings, load to target |
| Selection | `/projects/{id}/selection` | Profiles, criteria, preview |
| Runs | `/runs`, `/projects/{id}/runs` | Create run, audit log, loads |
| Reconciliation | `/projects/{id}/reconciliation` | Summary, export, run funnel |

---

## 9. Deployment architecture

### Local development

```bash
# Backend
docker compose up postgres -d
pip install -e ".[dev]"
alembic upgrade head
uvicorn migration_utility.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5174 (proxies /api → :8000)
```

### Docker Compose (full stack)

```bash
docker compose up --build -d
# UI: http://localhost:3000  API: http://localhost:8000  DB: localhost:5433
```

### Vercel production

| Component | Configuration |
|-----------|---------------|
| Frontend | Vite build → `frontend/dist` |
| API | Python serverless function `api/index.py` (Mangum + FastAPI) |
| Routing | `/api/*` → serverless; everything else → SPA `index.html` |
| Database | Neon PostgreSQL via `DATABASE_URL` env var |
| SSL | `sslmode=require` for Neon; `NullPool` on serverless |

Setup script: `scripts/setup_production_db.sh`

Environment variables (production):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Neon pooled connection string |
| `CORS_ORIGINS` | `https://migration-utility.vercel.app,...` |
| `LANDING_ZONE_PATH` | Writable temp path for uploads (serverless: `/tmp`) |
| `KRAKEN_MOCK_MODE` | `true` for mock API load (default) |

---

## 10. Sample data & templates

```
samples/
├── accounts.csv                    # Generic account extract
├── source_fields.csv               # Generic source field catalog
├── target_fields_kraken.csv        # Generic destination catalog
└── utility/                        # Utilities industry templates
    ├── source_fields.csv
    ├── destination_fields.csv
    ├── target_extract.csv
    └── tariff_mapping.csv
```

---

## 11. Testing

```bash
pytest                    # 50 backend tests
cd frontend && npm run build   # Production build verification
```

Test coverage areas:

- Rules engine (validation + transforms including pad_left, regex_replace)
- Ingest parsers (CSV, JSON, XML)
- API routes (projects, rules, mapping, fields, reconciliation)
- Kraken/SAP adapter mocks
- Selection engine
- Workflow transitions

---

## 12. Security & operational notes

- **Auth:** Not implemented in v0.7 — suitable for internal/dev use; add auth middleware before public multi-tenant use
- **Secrets:** `DATABASE_URL` stored as Vercel sensitive env var; never committed to git
- **CORS:** Explicit origin list in `CORS_ORIGINS`
- **File uploads:** Land in configurable landing zone; validated against schema before staging
- **Workflow locking:** Mappings locked after approval to prevent accidental production changes

---

## 13. Roadmap (from profile model)

| Feature | Status |
|---------|--------|
| Data migration (utilities) | ✅ Shipped |
| Data migration (generic) | ✅ Shipped |
| Document migration | 🔜 Scaffolded |
| Database migration | 🔜 Scaffolded |
| Banking industry templates | 🔜 Scaffolded |
| Healthcare industry templates | 🔜 Scaffolded |
| Live destination API (non-mock) | ⚙️ Configurable via env |
| User authentication / RBAC | 📋 Planned |

---

## 14. Key file reference

| Path | Description |
|------|-------------|
| `frontend/src/components/MigrationWizard.jsx` | Guided migration workflow |
| `frontend/src/constants/migrationProfile.js` | Industry/type/approach catalogue |
| `frontend/src/components/ProjectForm.jsx` | 4-step project creation |
| `frontend/src/api/client.js` | REST client with HTML-safe JSON parsing |
| `migration_utility/rules/engine.py` | Validation + transform engines |
| `migration_utility/core/pipeline.py` | Pipeline orchestrator |
| `migration_utility/fields/service.py` | Field catalog + mapping apply |
| `api/index.py` | Vercel serverless entrypoint |
| `vercel.json` | Vercel build + routing config |
| `scripts/setup_production_db.sh` | Neon + Vercel DB setup automation |
| `alembic/versions/` | Database migration history |

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **Source** | Legacy/origin system providing extract data |
| **Destination** | Target platform receiving transformed payloads |
| **Rule set** | Versioned collection of validation rules + field mappings |
| **Staging table** | Per-project PostgreSQL table holding validated extract rows |
| **Field catalog** | Uploaded list of source/destination field definitions |
| **Tariff mapping** | Product/rate-band translation (utilities-specific) |
| **Load record** | Persisted request/response from a destination adapter call |
| **Reconciliation** | Post-migration counts, funnel, and variance analysis |

---

*For quick start instructions see [README.md](../README.md). For API details see Swagger at `/docs` when running the API locally.*
