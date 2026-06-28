# Migration Utility — Capability Matrix (Sales / RFP One-Pager)

**Version 0.10.0** · Honest status for customer conversations  
Legend: **Yes** = shipped · **Partial** = available with constraints · **Roadmap** = planned · **No** = not offered

| Capability | Status | Notes |
|------------|--------|-------|
| Vendor-neutral destination plugins | **Yes** | Kraken/SAP as references; UI avoids vendor lock-in labels |
| File extract ingest (CSV/JSON/XML) | **Yes** | Staging in PostgreSQL |
| Field mapping & transform rules | **Yes** | Workflow states: draft → in_review → approved → signed_off |
| Validation rule engine | **Yes** | Required, pattern, range, conditional, lookups |
| Tariff / product mapping (utilities) | **Yes** | Optional per industry profile |
| Candidate selection profiles | **Yes** | Filter which records enter a run |
| Migration run pipeline (E→V→T→L) | **Yes** | Sync default; async with worker |
| Async worker + queued runs | **Yes** | `RUNNER_MODE=worker` + worker process |
| Run progress & checkpoints | **Yes** | `progress_pct`, resume from failed run |
| On-prem / VPC Docker deploy | **Yes** | docker-compose: postgres, api, ui, worker |
| Corporate HTTP proxy | **Yes** | `HTTP_PROXY` / `HTTPS_PROXY` |
| mTLS to destination APIs | **Yes** | Client cert + CA bundle env vars |
| Data profiling on upload | **Yes** | Column stats + anomaly report |
| Exception queue (HITL) | **Yes** | Assign, override, resolve, audit history |
| Kraken error catalog (~920 codes) | **Yes** | Range-indexed; 57 with confirmed API messages |
| Account health & cohort readiness | **Yes** | Static data + operational blockers before migration |
| Fallout root-cause classification | **Yes** | Kraken code, owner role, remediation routing |
| Migration testing plan (dress rehearsal) | **Yes** | Mapping, product-build, volume, pre-prod phases |
| RBAC + JWT login | **Partial** | Opt-in `AUTH_ENABLED=true`; no SSO yet |
| Workflow approval tied to login | **Partial** | When auth enabled; demo mode without |
| Live destination API load | **Partial** | Kraken/SAP live paths; customer URL/creds |
| Reconciliation & BI export | **Yes** | Funnel, variance, JSON export |
| Bulk scale (100M+ rows) | **Partial** | Chunked batches; needs sizing/tuning |
| Serverless SaaS demo | **Yes** | Vercel; sync runs only unless external worker |
| SSO / SAML / OIDC | **Roadmap** | v1.x |
| Document migration | **Roadmap** | UI placeholder |
| Database-to-database replication | **Roadmap** | UI placeholder |
| Autonomous AI data repair | **No** | Profiling + manual override only |
| Firewall bypass without customer proxy | **No** | Customer network team configures egress |

---

## Quick deployment modes

| Mode | Best for | Worker | Auth |
|------|----------|--------|------|
| **Local dev** | Consultants, POC | Optional | Off (default) |
| **Docker Compose** | Customer VPC pilot | Included service | Enable for pilot UAT |
| **Vercel demo** | Sales demo, light trials | Not on platform | Off |

---

## P0 / P1 delivery checklist (v0.9)

- [x] P0 — Customer-deployable runner (Docker, proxy, mTLS HTTP client)  
- [x] P0 — Async worker, queued runs, progress, resume  
- [x] P1 — Data profiling + anomaly report on upload  
- [x] P1 — RBAC + approval UI with real users (when auth enabled)  
- [x] P1 — Exception queue (assign, override, audit)  

---

## Competitive positioning (honest)

**Strengths:** End-to-end migration workflow in one tool; plugin model; utilities templates; reconciliation; exception queue; deployable in customer network.

**Gaps vs enterprise ETL/iPaaS:** No native SSO, limited pre-built connectors, no guaranteed petabyte scale, no proprietary “zero-touch” AI migration.

Use this matrix to set expectations early and attach [CUSTOMER_FAQ_RFP.md](./CUSTOMER_FAQ_RFP.md) for narrative RFP answers.
