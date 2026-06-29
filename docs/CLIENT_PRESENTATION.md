# Migration Utility — Client Presentation Guide

**Product:** Arthavi Migration Utility  
**Version:** 0.11.0  
**Live demo:** https://migration-utility.vercel.app  
**Repository:** https://github.com/dashsanat2024-sys/migration-utility  
**Audience:** Programme sponsors, migration leads, IT architecture, procurement  
**Last updated:** June 2026

---

## 1. Executive summary

Migration Utility is a **vendor-neutral data migration platform** for moving structured records from legacy source systems into modern destination platforms (billing, CRM, ERP).

Unlike point-to-point ETL scripts, it provides a **governed, auditable workflow** in one product:

```
Extract → Profile → Map → Validate → Transform → Approve → Load → Reconcile
```

Teams configure migrations through a web UI. Rules, mappings, and approvals are stored in PostgreSQL. A deterministic engine executes every load — **AI assists with suggestions but never writes to destination systems autonomously**.

**Primary reference use case:** Utilities industry migration (e.g. legacy billing/CRM extract → Kraken AccountType), with pluggable destination schemas for other industries.

---

## 2. Business benefits

| Benefit | What it means for the client |
|---------|------------------------------|
| **Faster time-to-first-migration** | Upload a source extract, map to a published destination schema, and run a pilot in days — not months of bespoke scripting |
| **Reduced migration risk** | Validation rules, transform previews, reconciliation funnel, and exception queue catch issues before production cutover |
| **Auditability & sign-off** | Mapping workflow (`draft` → `in_review` → `approved` → `signed_off`) with actor, role, and comment history |
| **Vendor neutrality** | Destination behaviour is plugin-based; UI uses source/destination language, not a single vendor lock-in |
| **AI-assisted productivity** | Semantic field matching, lookup table drafts, transform-rule inference, and error triage — all human-reviewed |
| **Deployable in customer network** | Docker Compose for VPC/on-prem; corporate proxy and mTLS supported for outbound API calls |
| **Pre-migration readiness** | Account health scoring and Kraken error catalog help exclude blocked accounts before a run |
| **Reconciliation & reporting** | Funnel metrics, variance analysis, and JSON export for BI tools (Metabase, Power BI) |

---

## 3. Capability overview

### 3.1 Project & workspace

- Create migration projects (industry profile, integration approach, target adapter)
- Single workspace API load (plugin schema, field catalog, rule sets)
- Destination plugin selection (Kraken Billing, SAP CRM, file export, mock)
- Custom destination schema upload (optional override of plugin contract)

### 3.2 Schema mapping & field catalog

- Upload **source extract** (CSV/JSON) — column names and sample values inferred automatically
- **Destination-first mapping** — each destination field is a “socket”; source fields plug in
- Auto-suggest mappings (deterministic name/alias matching)
- **AI suggest mappings** — semantic matching with confidence scores
- **AI lookup gaps** — draft enum lookup tables from sample values
- **AI transform rules** — infer conditional/lookup/date transforms from sample data
- **Needs review first** panel — surfaces uncovered values and low-confidence rules
- Apply approved mappings to versioned rule sets

### 3.3 Rules, validation & transforms

| Category | Types |
|----------|-------|
| **Validation** | Required, format (regex), in-list, numeric range, unique, cross-field |
| **Transforms** | Copy, constant, default, lookup, concat, conditional, uppercase/lowercase, date format, pad left, regex replace |
| **Utility (STW)** | Property type, area code, rate band lookup (Severn Trent → Kraken rules) |

- Rule sets with versioning and workflow states
- Transform preview against sample records
- Seed starter account rules for quick POC

### 3.4 AI-assisted migration layer (v0.11)

| Feature | Purpose |
|---------|---------|
| Semantic field mapping | Suggest source → destination pairs |
| Lookup gap analysis | Flag enum values with no destination match |
| Transform-rule inference | Propose lookup/conditional/date rules from samples |
| Error triage | Cluster migration errors by Kraken code / root cause |
| Mapping assistant chat | Q&A over schema, codes, and mapping context |

**Principle:** AI proposes; deterministic engine disposes. Every AI suggestion requires human approval.

### 3.5 Ingest, staging & profiling

- Upload CSV, JSON, or XML extracts
- Valid rows staged in PostgreSQL per project/entity
- Ingest error queue with reprocess
- **Data profiling** on upload: null %, distinct counts, inferred types, anomaly report

### 3.6 Candidate selection & batches

- Selection profiles with AND/OR criteria (eq, in, contains, range, null)
- Preview selection counts before run
- Volume limits (`max_candidates`, per-run `candidate_limit`)
- Multi-batch migration runs

### 3.7 Migration execution

Pipeline stages: **Ingest → Validate → Transform → Load**

| Mode | Description |
|------|-------------|
| **Sync** | Run executes inline in API (default; suitable for demos and small pilots) |
| **Async** | API queues run; dedicated worker process executes with progress and resume |

- Audit log per run
- Load records with request/response payloads
- Target adapters: mock, file export, Kraken REST, SAP IDoc (mock/live configurable)

### 3.8 Tariff & product mapping (utilities)

- Tariff mapping sets with own approval workflow
- Load signed-off tariff codes to destination (mock or live)
- STW transform rules UI for property type, area code, rate band

### 3.9 Account health & error intelligence

- Kraken error catalog (~920 codes, range-indexed)
- Account health assessment: readiness score (0–100), blocker detection
- Sync blockers to exception queue
- Migration testing plan (dress rehearsal phases)

### 3.10 Reconciliation & reporting

- Project-level summary: staged, runs, loads, open errors
- Run-level funnel: staged → selected → loaded/failed
- Variance analysis and match rate
- Sample record diff (source vs target payload)
- JSON export for BI dashboards

### 3.11 Exception queue (human-in-the-loop)

- Assign, override, resolve exceptions
- Audit history per exception
- Sync from ingest errors and account health fallout

### 3.12 Security (opt-in)

- JWT login and role-based access (`mapping_lead`, `business_analyst`, `product_owner`, etc.)
- Workflow transitions tied to authenticated user when enabled
- SSO/SAML: roadmap (v1.x)

---

## 4. How to use — step-by-step

### 4.1 Pilot workflow (recommended)

| Step | Action | Outcome |
|------|--------|---------|
| 1 | Create a project (utilities + API integration profile) | Workspace ready |
| 2 | Confirm destination plugin (e.g. Kraken Account) | Destination schema loaded |
| 3 | Upload source extract CSV | Field catalog + sample values |
| 4 | Click **AI suggest** → review mappings | Draft field links |
| 5 | Click **AI lookup gaps** / **AI transform rules** | Draft transforms; review flagged gaps |
| 6 | Create rule set → **Apply mappings** | Versioned mapping rules |
| 7 | Add validation rules; transition workflow to **approved** | Governed rule set |
| 8 | Upload full data file → **Upload & Stage** | Staged rows in database |
| 9 | (Optional) Configure selection profile | Filter migration cohort |
| 10 | **Run Migration** | Validate → transform → load |
| 11 | **Reconciliation** tab | Funnel, variance, sample diffs |
| 12 | **Errors & Exceptions** | Triage and remediate failures |

### 4.2 AI feature test path

Use the bundled QA sample for non-zero AI suggestions:

1. Keep **plugin schema** active (not a plain custom target without enums).
2. Upload: `samples/severn_trent/target_cmp_ai_gap_sample.csv`
3. Click **AI suggest** → **AI lookup gaps** → **AI transform rules**
4. Review the **Needs review first** panel for uncovered values (e.g. `STD`, `X`, `Z`)

### 4.3 Roles in the workflow

| Role | Typical responsibility |
|------|------------------------|
| Mapping Lead | Upload extracts, create mappings, submit for review |
| Business Analyst | Validate business rules, approve mappings |
| Product Owner | Final sign-off before production runs |
| Migration Engineer | Configure runs, monitor execution, resume failures |
| QA Analyst | Reconciliation, exception resolution, BI export |

---

## 5. Technology stack

### 5.1 Application

| Layer | Technology |
|-------|------------|
| **Backend API** | Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic |
| **Frontend** | React 19, Vite 6, React Router 7, custom CSS (Arthavi design system) |
| **Database** | PostgreSQL 16 |
| **AI (optional)** | LangChain, LangGraph, OpenAI (`gpt-4o-mini` default) |
| **Auth (optional)** | JWT (PyJWT) |
| **HTTP client** | httpx (proxy + mTLS support) |

### 5.2 Packaging & runtime

| Component | Technology |
|-----------|------------|
| API container | Python 3.12-slim Docker image |
| UI container | Nginx serving Vite production build |
| Worker | Same API image, `runner_worker` command |
| Serverless (demo) | Vercel + Mangum (FastAPI ASGI adapter) |

### 5.3 Data flow architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React UI  —  mapping, rules, runs, reconciliation, AI     │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST /api/*
┌───────────────────────────▼─────────────────────────────────┐
│  FastAPI  —  validation engine, transform engine, workflow    │
│  Destination plugins  ·  AI suggestion layer  ·  Pipeline   │
└───────┬─────────────────────┬────────────────────┬──────────┘
        │                     │                    │
        ▼                     ▼                    ▼
   PostgreSQL           Landing zone          Destination APIs
   (metadata,          (uploaded files)      (Kraken, SAP, file)
    staging)
```

---

## 6. Deployment options

### 6.1 Option A — Hosted demo (fastest trial)

| Item | Detail |
|------|--------|
| **URL** | https://migration-utility.vercel.app |
| **Best for** | Sales demo, light evaluation, mapping UX |
| **Database** | Neon PostgreSQL (managed) |
| **Limitations** | Sync runs only (no co-located worker on serverless); 30s API timeout; ephemeral file storage |

**Client action:** Use as-is for UI/POC. Point a custom deployment’s API via `VITE_API_BASE` when ready for VPC pilot.

### 6.2 Option B — Docker Compose (recommended pilot / VPC)

**Best for:** Customer VPC, on-prem, private cloud, UAT, dress rehearsal.

```bash
git clone https://github.com/dashsanat2024-sys/migration-utility.git
cd migration-utility
docker compose up --build -d
```

| Service | URL / port |
|---------|------------|
| UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 |

**Includes:** API + UI + PostgreSQL + **async worker** (queued runs, progress, resume).

Apply migrations:

```bash
docker compose exec api alembic upgrade head
```

### 6.3 Option C — Manual / Kubernetes / cloud PaaS

Deploy the same containers to any orchestrator:

1. **PostgreSQL** — managed service (RDS, Cloud SQL, Azure Database, Neon, etc.)
2. **API** — container from `Dockerfile`; expose port 8000
3. **Worker** — same image; command `python -m migration_utility.worker.runner_worker`
4. **UI** — static build from `frontend/` (`npm run build`); serve via Nginx, S3+CloudFront, Azure Static Web Apps, etc.
5. Set `DATABASE_URL`, `LANDING_ZONE_PATH`, `CORS_ORIGINS`, and optional auth/AI/proxy vars
6. Run `alembic upgrade head` on first deploy

---

## 7. Client onboarding checklist (when they agree to try)

### Phase 1 — Environment (Day 1–2)

- [ ] Choose deployment mode (hosted demo vs Docker vs customer cloud)
- [ ] Provision PostgreSQL 16+
- [ ] Deploy API + UI (+ worker for async runs)
- [ ] Run database migrations (`alembic upgrade head`)
- [ ] Configure `.env` (see section 8)
- [ ] Verify health: `GET /api/health` and `GET /api/health/live`

### Phase 2 — Connectivity (Day 2–3)

- [ ] Confirm outbound access to destination APIs (or use mock mode initially)
- [ ] Configure corporate proxy if required (`HTTP_PROXY`, `HTTPS_PROXY`)
- [ ] Configure mTLS client certs if required (`CLIENT_CERT_PATH`, `CLIENT_KEY_PATH`, `CA_BUNDLE_PATH`)
- [ ] Set `KRAKEN_MOCK_MODE=false` and `KRAKEN_API_URL` when ready for live REST (customer URL)

### Phase 3 — POC data (Day 3–5)

- [ ] Create migration project
- [ ] Upload sample source extract (or use `target_cmp_sample_extract.csv`)
- [ ] Complete schema mapping with AI assist
- [ ] Create and approve rule set
- [ ] Run pilot migration (sync or async)
- [ ] Review reconciliation and exception queue

### Phase 4 — Production readiness (Week 2+)

- [ ] Enable `AUTH_ENABLED=true` with strong `AUTH_SECRET`
- [ ] Size worker and database for expected volume (`RUN_CHUNK_SIZE`, batch strategy)
- [ ] Account health assessment on full cohort
- [ ] Dress rehearsal run with migration testing plan
- [ ] BI export wired to customer reporting

---

## 8. Key environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `LANDING_ZONE_PATH` | Uploaded file storage path |
| `EXPORT_PATH` | File export adapter output |
| `CORS_ORIGINS` | Allowed frontend origins |
| `RUNNER_MODE` | `api` (sync) or `worker` (async queue) |
| `ASYNC_RUNS_ENABLED` | Enable queued runs |
| `RUN_CHUNK_SIZE` | Records per pipeline chunk (default 500) |
| `AUTH_ENABLED` | Enable JWT login |
| `AUTH_SECRET` | JWT signing secret |
| `HTTP_PROXY` / `HTTPS_PROXY` | Corporate egress |
| `CLIENT_CERT_PATH` / `CLIENT_KEY_PATH` / `CA_BUNDLE_PATH` | mTLS |
| `KRAKEN_MOCK_MODE` / `KRAKEN_API_URL` | Destination load behaviour |
| `AI_ENABLED` / `OPENAI_API_KEY` / `AI_MODEL` | AI-assisted features |
| `VITE_API_BASE` | Frontend API URL (build-time for custom deploys) |

Full list: [DEPLOYMENT_RUNNER.md](./DEPLOYMENT_RUNNER.md)

---

## 9. Cloud platform compatibility

### 9.1 Does it work on any cloud?

**Yes — with the right deployment pattern.** The application is **cloud-agnostic** at the architecture level:

| Requirement | Portable? | Notes |
|-------------|-----------|-------|
| PostgreSQL | Yes | Any managed or self-hosted Postgres 14+ |
| Containerized API | Yes | Standard Docker image; runs on ECS, AKS, GKE, Cloud Run, App Service, etc. |
| Static UI | Yes | Any static hosting (S3, Blob, GCS, CDN, Nginx) |
| Background worker | Yes | Separate container/process; not tied to one vendor |
| File landing zone | Yes | Local disk, EFS, Azure Files, GCS FUSE, NFS — set `LANDING_ZONE_PATH` |

### 9.2 Platform-specific notes

| Platform | Supported? | Recommended pattern |
|----------|------------|---------------------|
| **AWS** | Yes | ECS/Fargate or EKS: API + worker + RDS Postgres; UI on S3+CloudFront |
| **Azure** | Yes | Container Apps or AKS; Azure Database for PostgreSQL; Static Web Apps for UI |
| **Google Cloud** | Yes | Cloud Run (API) + Cloud SQL; GCE/GKE for worker; Cloud Storage for landing |
| **Oracle OCI** | Yes | OKE + Autonomous PostgreSQL-compatible or self-managed Postgres |
| **Vercel / Netlify** | Partial | UI + serverless API only; **no long-running worker**; sync runs; use external DB |
| **On-prem / VPC** | Yes | Docker Compose or Kubernetes behind customer reverse proxy |
| **OpenShift** | Yes | Deploy API/worker/UI containers; customer Postgres operator |

### 9.3 What does *not* port trivially to serverless-only?

| Capability | Serverless limitation | Fix |
|------------|----------------------|-----|
| Async migration runs | No persistent worker on Vercel Lambda | Deploy worker container elsewhere; same `DATABASE_URL` |
| Large file processing | Function timeout (e.g. 30s on Vercel) | Use Docker/K8s API or increase timeout + chunking |
| Long-running reconciliation | Same timeout constraints | Customer-hosted API with no short ceiling |
| Durable file storage | `/tmp` is ephemeral on Lambda | Mount persistent volume or object storage adapter |

---

## 10. Making it compatible with any cloud — architecture principles

To deploy on **any** cloud platform, treat Migration Utility as three independently scalable tiers:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Tier 1: UI  │   │ Tier 2: API  │   │ Tier 3: DB   │
│  (static)    │──►│  (stateless) │──►│ (PostgreSQL) │
└──────────────┘   └──────┬───────┘   └──────────────┘
                          │
                   ┌──────▼───────┐
                   │ Tier 4:      │
                   │ Worker       │
                   │ (optional)   │
                   └──────────────┘
```

### 10.1 Portability checklist for cloud implementers

1. **Stateless API** — no local session state; all config in PostgreSQL  
2. **External database** — single `DATABASE_URL`; no SQLite in production  
3. **Configurable storage** — `LANDING_ZONE_PATH` points to cloud volume or future object-store adapter  
4. **Environment-driven config** — no hard-coded cloud SDKs; proxy/mTLS via env vars  
5. **Container-first** — same `Dockerfile` runs everywhere  
6. **Worker separation** — async runs use a poll-based worker, deployable on any compute with DB access  
7. **Frontend build decoupling** — `VITE_API_BASE` at build time points UI to any API URL  

### 10.2 Optional enhancements for multi-cloud SaaS

| Enhancement | Benefit |
|-------------|---------|
| Object storage adapter (S3/Blob/GCS) for landing zone | Replace local disk on serverless |
| Managed secrets (AWS SM, Azure Key Vault) | Rotate DB and API keys |
| Message queue (SQS, Pub/Sub) instead of DB polling | Scale workers horizontally |
| SSO/OIDC integration | Enterprise identity |
| Helm chart | One-command K8s deploy on any cloud |

These are **roadmap items** — the current codebase already supports VPC Docker and manual K8s deployment without code changes.

---

## 11. Competitive positioning (honest)

### Strengths vs traditional ETL / iPaaS / conversion tools

- End-to-end migration workflow in one product (not just mapping or just load)
- Destination plugin model with published schema contracts
- Governed approval workflow built in
- AI-assisted mapping and transform suggestions with human review
- Utilities-specific templates (tariffs, STW transforms, account health)
- Reconciliation and exception queue for operational migration programmes
- Deployable inside customer network with proxy/mTLS

### Current gaps (set expectations early)

- No native SSO/SAML (JWT opt-in today)
- Limited pre-built source connectors (file extract primary; DB replication roadmap)
- Bulk scale (100M+ rows) requires sizing and tuning — **Phase 1 chunked pipeline** (500 rows/chunk) is in place; 50k–100k/day needs Phases 2–5 (see [HIGH_VOLUME_MIGRATION.md](./HIGH_VOLUME_MIGRATION.md))
- AI does not autonomously repair or load data — suggestions only
- Live destination APIs require customer credentials and network path

---

## 12. Support documents (technical depth)

| Document | Contents |
|----------|----------|
| [PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md) | Technical setup, API index |
| [FUNCTIONAL_SPECIFICATION.md](./FUNCTIONAL_SPECIFICATION.md) | Full functional spec |
| [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md) | RFP one-pager (Yes/Partial/Roadmap) |
| [CUSTOMER_FAQ_RFP.md](./CUSTOMER_FAQ_RFP.md) | Procurement & security FAQ |
| [DEPLOYMENT_RUNNER.md](./DEPLOYMENT_RUNNER.md) | Docker, worker, proxy, auth |
| [AI_ASSISTED_MIGRATION.md](./AI_ASSISTED_MIGRATION.md) | AI layer design |
| [STW_TRANSFORM_RULES.md](./STW_TRANSFORM_RULES.md) | Utility transform rules |
| [ACCOUNT_HEALTH_STRATEGY.md](./ACCOUNT_HEALTH_STRATEGY.md) | Pre-migration readiness |
| [HIGH_VOLUME_MIGRATION.md](./HIGH_VOLUME_MIGRATION.md) | 50k–100k/day capacity & roadmap |

---

## 13. One-page summary for slides

**Migration Utility** — Governed, AI-assisted data migration from legacy extracts to modern platforms.

- **What:** Map, validate, transform, approve, load, reconcile — in one web app  
- **Who:** Utilities, CRM, ERP migration programmes  
- **How:** Upload extract → map to destination schema → approve rules → run → reconcile  
- **AI:** Suggests mappings, lookups, transforms, error triage — human approves everything  
- **Deploy:** Vercel demo · Docker VPC · Any cloud (Postgres + containers + static UI)  
- **Try:** https://migration-utility.vercel.app  

---

## 14. High-volume migration (50k–100k accounts/day)

| Topic | Detail |
|-------|--------|
| **Today (Vercel demo)** | Not suitable — 30s timeout, no worker, ephemeral storage |
| **Today (Docker + worker)** | Phases 1–4: chunked staging, Kraken sub-batching, parallel workers, summary audit mode |
| **50k–100k/day target** | Achievable with Phase 5 wave scheduler + UAT dress rehearsal |
| **Deep dive** | [HIGH_VOLUME_MIGRATION.md](./HIGH_VOLUME_MIGRATION.md) — bottlenecks, roadmap, sizing |

**Customer message:** The platform supports governed waves at scale; very high daily throughput is a **deployment + engineering** programme (typically 2–4 weeks beyond Phase 1), not a single toggle.

---

*Document prepared for client presentations. For the latest capability status, see [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md).*
