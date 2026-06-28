# Migration Utility — Technical Documentation

**Version:** 0.8.0  
**Last updated:** June 2026  
**Repository:** https://github.com/dashsanat2024-sys/migration-utility  
**Live UI:** https://migration-utility.vercel.app

---

## 1. Executive summary

Migration Utility is a **generic, industry-aware data migration platform** for moving structured records from legacy source systems to modern destination platforms. It provides a full lifecycle: **extract → validate → transform → load → reconcile**, with configuration driven from the UI and stored in PostgreSQL.

The product uses **vendor-neutral language** in the UI (source / destination) while supporting pluggable **destination plugins** and **target adapters** under the hood.

**Primary use case (v0.8):** Utilities industry migration where the **destination publishes its schema contract** (Kraken AccountType via Severn Trent Water GraphQL reference) and the source extract maps *into* that contract — no manual destination field catalog upload in the normal flow.

**Branding:** Arthavi-aligned UI — dark sidebar, light main panel, Poppins typography (aligned with VidyAI / Parvidya design system).

See also:

- [PLUGIN_SCHEMA_DESIGN.md](./PLUGIN_SCHEMA_DESIGN.md) — plugin architecture rationale
- [kraken-schema-reference.md](../kraken-schema-reference.md) — real Kraken ST Water field reference
- [target_cmp_data_dictionary.md](../target_cmp_data_dictionary.md) — fictional Target/CMP legacy extract for QA

---

## 2. Technology stack

### Backend

| Layer | Technology | Version / notes |
|-------|------------|-----------------|
| Language | Python | 3.11+ |
| API framework | FastAPI | ≥ 0.115 |
| ASGI server (local) | Uvicorn | ≥ 0.32 |
| Serverless (production) | Mangum | Wraps FastAPI on Vercel |
| ORM | SQLAlchemy | 2.x |
| DB driver | psycopg2-binary | PostgreSQL |
| Migrations | Alembic | 7 revisions (phases 0–6) |
| Validation / settings | Pydantic + pydantic-settings | v2 |
| File uploads | python-multipart | Multipart form parsing |
| Env loading | python-dotenv | `.env` at repo root |
| Testing | pytest + httpx (TestClient) | 58 tests |

### Frontend

| Layer | Technology | Version / notes |
|-------|------------|-----------------|
| UI library | React | 19.x |
| Build tool | Vite | 6.x |
| Routing | React Router | 7.x |
| Styling | Custom CSS | CSS variables (Arthavi / VidyAI tokens) |
| Fonts | Poppins, Inter, JetBrains Mono | Google Fonts |
| HTTP client | Native `fetch` | `frontend/src/api/client.js` |
| Dev server | Vite | Port **5174**; proxies `/api` → `:8000` |

### Data & infrastructure

| Component | Technology |
|-----------|------------|
| Primary database | PostgreSQL 16 (local Docker) |
| Production database | Neon PostgreSQL (pooled, SSL) |
| File landing zone | Local filesystem or `/tmp` on Vercel |
| Local full stack | Docker Compose (Postgres + API + Nginx UI) |
| Production hosting | Vercel (static frontend + Python serverless `/api`) |
| CI / deploy | GitHub → Vercel auto-deploy on `main` |

### Key Python packages (runtime)

```
fastapi, uvicorn, sqlalchemy, psycopg2-binary, alembic,
pydantic, pydantic-settings, python-dotenv, python-multipart, mangum
```

### Key npm packages

```
react, react-dom, react-router-dom, vite, @vitejs/plugin-react
```

---

## 3. High-level architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    React UI (Vite + React 19)                          │
│  Dashboard │ ProjectShell (dark sidebar) │ Schema & Mapping │ Runs │ …   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ REST /api/*
┌───────────────────────────────▼──────────────────────────────────────────┐
│                 FastAPI Application (Python 3.11+)                       │
│  Routes │ ValidationEngine │ TransformEngine │ WorkflowEngine │ Pipeline   │
│  Destination plugins (get_schema) │ Field catalog │ Mapping matrix       │
└───────┬─────────────────────────────┬────────────────────┬───────────────┘
        │                             │                    │
        ▼                             ▼                    ▼
┌───────────────┐           ┌─────────────────┐   ┌──────────────────────┐
│  PostgreSQL   │           │  Landing zone   │   │ Target adapters      │
│  metadata,    │           │  CSV/JSON/XML   │   │ mock, file_export,   │
│  rules, runs, │           │  uploads        │   │ kraken (api_import), │
│  field_catalogs│          └─────────────────┘   │ sap                  │
└───────────────┘                                  └──────────────────────┘
```

### Pipeline stages (every migration run)

| Stage | Purpose |
|-------|---------|
| **Ingest** | Read staged rows from source connector (typically PostgreSQL staging tables populated by file upload) |
| **Validate** | Apply validation rules from approved rule sets |
| **Transform** | Apply field mappings + transform logic → destination JSON shape |
| **Load** | Send payloads to destination adapter (REST API mock/live, file export, SAP mock) |

Orchestrator: `migration_utility/core/pipeline.py` via `migration_utility/rules/pipeline_hooks.py`.

---

## 4. End-to-end migration guide (step by step)

This walkthrough uses the **utilities + API integration** profile and the **Kraken Account** destination plugin. It matches the recommended QA path with the Target/CMP sample extract.

### Phase A — Environment setup

#### Local development

**Terminal 1 — API**

```bash
cd /path/to/migration-utility
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up postgres -d          # or use existing PostgreSQL
alembic upgrade head
uvicorn migration_utility.main:app --reload --port 8000
```

**Terminal 2 — UI**

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5174  (proxies /api → http://localhost:8000)
```

**Environment (`.env` at repo root)**

| Variable | Example | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/migration` | PostgreSQL connection |
| `CORS_ORIGINS` | `http://localhost:5174` | Allowed browser origins |
| `LANDING_ZONE_PATH` | `./uploads` | Uploaded extract files |
| `KRAKEN_MOCK_MODE` | `true` | Mock Kraken API loads (default) |

#### Production

- UI: https://migration-utility.vercel.app  
- API: same origin `/api/*` (Vercel serverless)  
- Set `DATABASE_URL` (Neon), `CORS_ORIGINS`, `LANDING_ZONE_PATH=/tmp` in Vercel env vars  
- Setup helper: `scripts/setup_production_db.sh`

---

### Phase B — Create a migration project

1. Open the **Dashboard** (`/`).
2. Click **+ New Project**.
3. Complete the **4-step setup wizard**:
   - **Migration type:** Data Migration
   - **Industry:** Utilities (enables tariff mapping)
   - **Integration approach:** API Integration
   - **Project details:** name, slug, environment, connectors
4. Click **Create project**.
5. You land at `/projects/{your-slug}` (slug-based URL, not UUID).

The project stores a **profile** in `project.config.profile` (industry, features, approach) which drives visible tabs and wizard steps.

---

### Phase C — Select destination plugin

1. Open the project — default workspace tab is **Schema & Mapping**.
2. On the left **Destination schema** card, review the active plugin (default for Kraken/API: `kraken-billing-v3`).
3. Optional: click **⇄ Swap destination plugin** to choose SAP CRM, file export, or mock.
4. Optional: click **↑ Upload destination schema** to use a custom CSV/JSON contract instead of the plugin (ad-hoc destinations).

**Kraken plugin (v4.0.0):** `Kraken Account — Severn Trent Water`  
~40 migration-relevant fields sourced from [developer.st.kraken.tech](https://developer.st.kraken.tech/graphql/reference/) including `number`, `accountType`, `status`, `isOnSteppedTariff`, `migrationSource`, `urn`, legacy `billingAddressLine1–5`, and structured `address.line1` etc.

---

### Phase D — Upload source extract & map fields

1. Stay on **Schema & Mapping**.
2. Upload **source extract** (CSV or JSON):
   - **QA sample:** `target_cmp_sample_extract.csv` (20 rows, 15 Target/CMP columns)
   - **Field catalog format:** `samples/source_fields.csv` (`name,data_type,required,...`)
3. The parser auto-detects **data extracts** (column headers → source fields) vs **field catalog** rows.
4. Click **Auto-suggest mappings** (destination-first):
   - Proposes `CUST_ACCOUNT_NO → number`, `LEGACY_SYS_REF → urn`, `STEPPED_RATE_FLAG → isOnSteppedTariff`, etc.
5. Manually complete mappings that need transforms:
   - **Lookup:** `CUST_TYPE_FLAG → accountType` (D→DOMESTIC, B→BUSINESS, …)
   - **Lookup:** `ACCT_STATUS_CODE → status` (A→ACTIVE, P→PENDING, …)
   - **Conditional:** `STEPPED_RATE_FLAG` Y/N → `isOnSteppedTariff` boolean
   - **Constant:** `migrationSource` = `"TARGET_CMP"` (provenance)
6. Leave intentionally unmapped source fields (`COMPLAINT_FLAG`, `DATE_ACCOUNT_OPENED`) to verify UI shows **source-only** rows.
7. Create or select a **rule set**, then **Apply mappings to rule set**.

**Filter chips:** All · Unmapped · Required only · Migration provenance · Needs transform

---

### Phase E — Upload & stage raw data (optional parallel path)

1. Open **Upload & Stage** tab.
2. Upload account extract CSV/JSON/XML (`samples/accounts.csv` or Target/CMP extract).
3. Files land in the **landing zone**, parse into **per-project staging tables**.
4. Review **staging stats** and fix **Ingest Errors** if any rows fail validation.

---

### Phase F — Transform rules & validation

1. Open **Transform Rules** tab (or continue in Migration Wizard).
2. **Seed account rules** if starting fresh: creates a draft rule set with sample validation rules.
3. Add **validation rules** (`required`, `format`, `in_list`, `range`, `cross_field`, `unique`).
4. Configure **custom transform types** in project config if needed.
5. Move rule set through workflow: **draft → in review → approved → signed off**.

Only `draft` and `in_review` rule sets accept mapping edits.

---

### Phase G — Tariff mapping (utilities only)

1. Open **Tariff Mapping** tab.
2. **Seed** or import tariff rows (`samples/utility/tariff_mapping.csv`).
3. Map source product / rate band → destination product codes.
4. Approve tariff set through the same workflow engine.
5. **Load tariffs** to destination when ready.

---

### Phase H — Candidate selection

1. Open **Candidate Selection** tab.
2. **Seed account selection profile** or create criteria (filters on staged data).
3. **Preview selection** to see which records would be included in a run.
4. Toggle criteria on/off per migration wave.

---

### Phase I — Execute migration run

1. Open **Migration Runs** tab (or Migration Wizard → Execute step).
2. Ensure rule set is **approved** (if run config requires it).
3. Click **Start run** with options:
   - `use_rules: true` — apply approved mappings + validation
   - `use_selection: true/false` — filter by selection profile
4. Pipeline executes: **Ingest → Validate → Transform → Load**.
5. Review **load records** (request/response per account), batch stats, audit log.

With `KRAKEN_MOCK_MODE=true`, loads succeed against the mock Kraken adapter without live API credentials.

---

### Phase J — Reconciliation & sign-off

1. Open **Reconciliation** tab.
2. Review **funnel** (staged → validated → transformed → loaded).
3. Check **variance** vs expected counts.
4. **Export** reconciliation JSON for BI / audit.
5. Review **Ingest Errors** tab for any rows to reprocess.

---

### Quick reference — recommended tab order

| Step | Tab | Outcome |
|------|-----|---------|
| 1 | Schema & Mapping | Destination contract + source → field mappings in rule set |
| 2 | Upload & Stage | Raw extracts in staging tables |
| 3 | Transform Rules | Validation rules + workflow approval |
| 4 | Tariff Mapping | Product/rate translations (utilities) |
| 5 | Candidate Selection | Record filter for run |
| 6 | Migration Runs | Execute pipeline |
| 7 | Reconciliation | Post-run counts and export |

**Migration Wizard** tab consolidates steps 1–6 in a guided checklist for first-time setup.

---

## 5. UI design & navigation

### Layout pattern (Arthavi / VidyAI)

| Area | Style |
|------|-------|
| **Sidebar** | Dark gradient (`#121230 → #2A2858`), white nav text, purple active state |
| **Main panel** | Light background `#F5F7FB`, white cards |
| **Primary actions** | Purple gradient `#6B52B0`, blue accent `#04A0E8` |
| **Logo** | `frontend/public/arthavi-logo.png` via `BrandLogo` component |

### Routes

| URL | Screen |
|-----|--------|
| `/` | Dashboard — project list, create project |
| `/projects/{slug}` | Project workspace (tabs in app state, slug in URL) |

Legacy UUID URLs redirect to slug. Old `/projects/{id}/mapping` paths strip the tab segment.

### Project workspace tabs

Implemented in `ProjectShell.jsx` + `ProjectPage.jsx`:

| Tab | Component | Purpose |
|-----|-----------|---------|
| **Schema & Mapping** (default) | `SchemaMappingScreen` | Plugin schema + mapping canvas |
| Migration Wizard | `MigrationWizard` | Guided checklist workflow |
| Upload & Stage | `IngestPanel` | File upload, staging stats |
| Transform Rules | `RulesPanel` | Rule set CRUD, validation rules |
| Tariff Mapping | `TariffWizardStep` | Utilities tariff grid |
| Candidate Selection | `CandidatesPanel` | Selection profiles & preview |
| Migration Runs | `RunsPanel` | Start runs, view loads |
| Reconciliation | `ReconciliationPanel` | Funnel, variance, BI export |
| Ingest Errors | `ErrorsPanel` | Failed row review & reprocess |

Hidden legacy tab: `matrix` → `MappingPanel` (full matrix view).

### Schema & Mapping screen (v0.8 flagship)

| Element | Component | Description |
|---------|-----------|-------------|
| Stepper | `MigrationStepper` | 6-step progress (plugin → extract → map → rules → tariff → run) |
| Plugin card | `DestinationPluginCard` | Active plugin, stats, swap/upload/clear schema |
| Mapping canvas | `SchemaMappingPanel` | Destination-first rows, transforms, filters |
| Footer bar | `SchemaMappingScreen` | Pending required count, submit for review |

---

## 6. Destination plugin system

Each destination is a **plugin** implementing `get_schema(entity)` and publishing a typed field contract.

| Plugin ID | Label | Adapter | Transport |
|-----------|-------|---------|-----------|
| `kraken-billing-v3` | Kraken Account — Severn Trent Water | `kraken` | GraphQL · REST |
| `sap-crm-v1` | SAP Customer Master | `sap` | IDoc / BAPI |
| `file-export-v1` | JSON File Export | `file_export` | File system |
| `mock-v1` | Mock Destination | `mock` | In-memory |

### API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/destination/plugins` | List available plugins |
| GET | `/api/projects/{id}/destination/plugin` | Active plugin for project |
| GET | `/api/projects/{id}/destination/schema?entity=account` | Published schema contract |
| POST | `/api/projects/{id}/destination/swap` | Swap plugin (`confirm_orphan` if mappings exist) |

Implementation: `migration_utility/plugins/`  
Registry: `migration_utility/plugins/registry.py`

### Custom destination schema (without code)

On **Schema & Mapping**, click **↑ Upload destination schema** (CSV/JSON).  
This overrides the plugin contract for mapping only. Click **↩ Use plugin schema instead** to revert.

Clear uploaded schema: `DELETE /api/projects/{id}/fields/{entity}/target`

---

## 7. Field catalog & mapping engine

### Source upload formats

1. **Field catalog CSV/JSON** — rows with `name`, `data_type`, `required`, `description`
2. **Data extract CSV/JSON** — header row = column names; parser infers source fields automatically (`catalog_parser._looks_like_data_extract`)

### Mapping suggest

`POST /api/projects/{id}/fields/{entity}/suggest-mappings?destination_first=true`

- **Destination-first:** each Kraken socket gets a row; fuzzy + alias matching (`CUST_ACCOUNT_NO → number`)
- Unmapped source columns appear as **source-only** rows

### Apply to rule set

`POST /api/projects/{id}/fields/{entity}/apply-mappings/{rule_set_id}`

Writes `field_mappings` rows (source_field, target_field, transform_type, config).

### Transform types

| Type | Use case |
|------|----------|
| `copy` | Direct field copy |
| `constant` | Hardcoded value (e.g. `migrationSource`) |
| `default` | Fallback when empty |
| `lookup` | Enum translation (status codes, account types) |
| `concat` | Join name parts |
| `conditional` | Y/N flags → boolean |
| `uppercase` / `lowercase` | Normalization |
| `date_format` | Date reformatting |
| `pad_left` | Padded account numbers |
| `regex_replace` | Strip prefixes from rate bands |

Custom types: register in `project.config.custom_transforms`.

---

## 8. Backend module reference

```
migration_utility/
├── main.py                      # FastAPI app, CORS, routers
├── config.py                    # Settings from .env
├── plugins/                     # Destination plugin system (v0.8)
│   ├── kraken_billing.py        # Real ST Water AccountType schema
│   ├── sap_crm.py
│   ├── builtin.py               # mock, file_export
│   └── registry.py
├── api/routes/
│   ├── projects.py              # CRUD; GET by UUID or slug
│   ├── destination.py           # Plugin list, schema, swap
│   ├── fields.py                # Catalog upload, suggest, apply, clear target
│   ├── ingest.py, rules.py, mapping.py, tariffs.py
│   ├── selection.py, migration_runs.py, reconciliation.py
│   └── project_lookup.py        # resolve_project(uuid|slug)
├── connectors/                  # Source/target adapters at load time
├── rules/engine.py              # ValidationEngine + TransformEngine
├── core/pipeline.py             # MigrationPipeline
├── fields/                      # Catalog parser + service
├── ingest/                      # Parsers, landing zone, staging
├── mapping/, tariff/, selection/, reconciliation/, workflow/
└── datastore/models/            # SQLAlchemy ORM
```

### Database (Alembic)

| Phase | Key tables |
|-------|------------|
| 0 | `projects`, `migration_runs`, `batches`, `audit_logs` |
| 1 | `ingest_files`, `ingest_errors`, dynamic staging tables |
| 2 | `rule_sets`, `validation_rules`, `field_mappings` |
| 3 | `selection_profiles`, `selection_criteria`, `candidates` |
| 4 | `mapping_approvals`, `tariff_mapping_sets`, `tariff_mappings` |
| 5 | `load_records` |
| 6 | `field_catalogs` |

---

## 9. API surface (summary)

Base: `/api` — Swagger UI at `/docs` when running locally.

| Domain | Prefix | Key operations |
|--------|--------|----------------|
| Health | `/health` | DB + connector status |
| Projects | `/projects` | CRUD; GET by slug or UUID |
| Destination | `/destination/plugins`, `/projects/{id}/destination/*` | Plugin schema & swap |
| Fields | `/projects/{id}/fields/{entity}/*` | Source/target upload, suggest, apply, clear |
| Ingest | `/projects/{id}/ingest/*` | Upload, staging stats, errors |
| Rules | `/projects/{id}/rules/*` | Rule sets, validation, workflow, preview-transform |
| Mapping | `/projects/{id}/mapping/*` | Matrix, approvals |
| Tariffs | `/projects/{id}/tariffs/*` | Tariff sets, load |
| Selection | `/projects/{id}/selection/*` | Profiles, preview |
| Runs | `/projects/{id}/runs`, `/runs/{id}/*` | Execute, audit, loads |
| Reconciliation | `/projects/{id}/reconciliation/*` | Summary, export |

---

## 10. Sample data & test files

```
target_cmp_sample_extract.csv            # Target/CMP legacy extract (20 rows) — QA default
samples/
├── accounts.csv                         # Generic account extract
├── source_fields.csv                    # Field catalog format
├── destination_schema_example.json      # Custom schema upload example
└── severn_trent/
    ├── source_fields_cast.csv           # CAST-style column names
    ├── target_fields_kraken.csv         # Subset of Kraken field names
    └── target_cmp_sample_extract.csv    # Copy of root QA extract

target_cmp_data_dictionary.md            # Column definitions + edge cases
kraken-schema-reference.md               # Real Kraken GraphQL field notes
```

### Target/CMP QA checklist

After uploading `target_cmp_sample_extract.csv`:

1. ✅ 15 source fields appear (not account numbers as field names)
2. ✅ Auto-suggest maps `CUST_ACCOUNT_NO → number`, `LEGACY_SYS_REF → urn`
3. ⚙️ Manual lookup for `ACCT_STATUS_CODE → status`
4. ✅ `COMPLAINT_FLAG` and `DATE_ACCOUNT_OPENED` remain unmapped source-only

---

## 11. Deployment

### Vercel production

| Piece | Config |
|-------|--------|
| Frontend | `frontend/dist` static build |
| API | `api/index.py` — Mangum + FastAPI |
| Routing | `/api/*` → serverless; else SPA `index.html` |
| DB | Neon via `DATABASE_URL` |
| Pooling | `NullPool` on serverless; SSL for Neon |

### Docker Compose (local full stack)

```bash
docker compose up --build -d
# UI: http://localhost:3000  API: http://localhost:8000  DB: localhost:5433
```

---

## 12. Testing

```bash
pytest                         # 58 backend tests
cd frontend && npm run build     # Production build check
```

Coverage: rules engine, ingest parsers, field catalog (incl. data extract detection), destination plugins, API routes, Kraken/SAP mocks, selection, workflow, reconciliation.

---

## 13. Security & operations

| Topic | Status |
|-------|--------|
| Authentication | Not implemented — internal/dev use; add before multi-tenant |
| Secrets | `DATABASE_URL` in Vercel env only |
| CORS | Explicit `CORS_ORIGINS` list |
| Workflow locking | Mappings locked after approval |
| File uploads | Landing zone + schema validation before staging |
| Mock loads | `KRAKEN_MOCK_MODE=true` default — set `false` + credentials for live Kraken |

---

## 14. Roadmap

| Feature | Status |
|---------|--------|
| Destination-as-plugin + Schema & Mapping UI | ✅ v0.8 |
| Real Kraken ST Water AccountType schema | ✅ v0.8 |
| Target/CMP sample extract + data extract parsing | ✅ v0.8 |
| Custom destination schema upload | ✅ v0.8 |
| Arthavi branding + slug URLs | ✅ v0.8 |
| Live Kraken GraphQL schema introspection | 📋 Planned |
| User authentication / RBAC | 📋 Planned |
| Document / DB migration types | 🔜 Scaffolded |
| Banking / healthcare templates | 🔜 Scaffolded |

---

## 15. Key file reference

| Path | Role |
|------|------|
| `frontend/src/components/SchemaMappingScreen.jsx` | Schema & Mapping page chrome |
| `frontend/src/components/SchemaMappingPanel.jsx` | Mapping canvas + plugin integration |
| `frontend/src/components/DestinationPluginCard.jsx` | Plugin card, swap, upload schema |
| `frontend/src/components/ProjectShell.jsx` | Dark sidebar + tab navigation |
| `frontend/src/constants/migrationProfile.js` | Industry/type/approach catalogue |
| `frontend/src/constants/projectRoutes.js` | Slug-based URL helpers |
| `migration_utility/plugins/kraken_billing.py` | Kraken AccountType schema |
| `migration_utility/fields/catalog_parser.py` | Catalog + data extract parsing |
| `migration_utility/api/routes/destination.py` | Plugin API |
| `api/index.py` | Vercel serverless entry |
| `vercel.json` | Deploy routing |

---

## 16. Glossary

| Term | Meaning |
|------|---------|
| **Source** | Legacy system providing extract data or field columns |
| **Destination** | Target platform; publishes schema via plugin |
| **Destination plugin** | Adapter that owns `get_schema()` contract |
| **Schema socket** | One destination field row on the mapping canvas |
| **Rule set** | Versioned validation rules + field mappings |
| **Staging table** | Per-project PostgreSQL table for extract rows |
| **Field catalog** | Uploaded source (or optional custom destination) field list |
| **Data extract** | Tabular CSV whose headers become source fields |
| **Migration provenance** | Kraken fields like `migrationSource`, `isMigrated`, `urn` |
| **Load record** | Persisted destination adapter request/response |
| **Reconciliation** | Post-run funnel, variance, and export |

---

*Quick start: [README.md](../README.md). API explorer: `/docs` when running the API locally.*
