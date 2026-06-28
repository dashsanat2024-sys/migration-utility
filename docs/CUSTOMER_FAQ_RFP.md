# Migration Utility — Customer FAQ / RFP Response

**Version:** 0.9.0  
**Audience:** Procurement, IT security, migration programme leads  
**Tone:** Honest capability statement — what we ship today vs what requires customer environment setup.

---

## 1. Product overview

**Q: What is Migration Utility?**  
A: A vendor-neutral data migration platform for structured records (accounts, products, master data). Teams upload source extracts, map fields to a destination schema, validate and transform, then load via REST adapters or file export. The UI guides mapping approval, run execution, reconciliation, and exception handling.

**Q: Is this tied to a single billing or ERP vendor?**  
A: No. Destination behaviour is pluggable via **destination plugins** (schema contract + load adapter). Kraken and SAP adapters ship as reference implementations; customers can add plugins or use generic REST/file export without naming a vendor in the UI.

---

## 2. Deployment & network (P0)

**Q: Can we run this inside our VPC / on-prem?**  
A: Yes. The stack is Docker-friendly: PostgreSQL, FastAPI API, optional **worker** process, React static UI. Deploy behind your reverse proxy; no mandatory SaaS dependency except whatever DB/hosting you choose.

**Q: Does it work through corporate HTTP proxies and mTLS?**  
A: Yes. Configure `HTTP_PROXY` / `HTTPS_PROXY`, `CLIENT_CERT_PATH`, `CLIENT_KEY_PATH`, and `CA_BUNDLE_PATH`. Outbound destination API calls (e.g. live REST import) use a shared HTTP client with these settings. See [DEPLOYMENT_RUNNER.md](./DEPLOYMENT_RUNNER.md).

**Q: Can migration runs execute asynchronously with progress and resume?**  
A: Yes. Set `RUNNER_MODE=worker`, run `python -m migration_utility.worker.runner_worker`, and enable `ASYNC_RUNS_ENABLED=true`. Runs queue with status `queued`; the worker claims them, updates `progress_pct` / `progress_message`, and stores checkpoints on failure. Failed runs can be resumed via API or UI.

**Q: What scale do you support?**  
A: Batch-oriented: configurable `RUN_CHUNK_SIZE` (default 500) passed through the pipeline. Large files are staged in PostgreSQL; very high volume (100M+ rows) typically needs dedicated worker sizing, DB tuning, and possibly external orchestration — we do not claim infinite scale out of the box.

---

## 3. Data quality & profiling (P1)

**Q: Do you profile data on upload?**  
A: Yes. Each ingest computes column stats (null %, distinct count, inferred type, samples) and an **anomaly report** (high null rate, constant columns, duplicate rows, etc.). Results appear in the UI and via `GET /projects/{id}/ingest/files/{file_id}/profile`.

**Q: Can you detect anomalies before migration runs?**  
A: Profiling runs at ingest time — before mapping sign-off and before load. Severity levels (high/medium/low) help prioritise data cleansing.

---

## 4. Security, RBAC & approvals (P1)

**Q: Do you support authentication and roles?**  
A: Yes (opt-in). Set `AUTH_ENABLED=true`. JWT login with seeded admin (`AUTH_SEED_EMAIL` / `AUTH_SEED_PASSWORD`). Roles align with mapping workflow: `mapping_lead`, `business_analyst`, `product_owner`, `migration_engineer`, `qa`.

**Q: Are workflow approvals tied to real users?**  
A: When auth is enabled, rule-set workflow transitions use the signed-in user's display name and role. Without auth, demo actor/role fields remain for local development.

**Q: SSO / SAML / OIDC?**  
A: Not built-in in v0.9. JWT login is the supported path; SSO can be added via reverse-proxy identity or future IdP integration.

---

## 5. Human-in-the-loop & exceptions (P1)

**Q: How are validation failures handled?**  
A: Failures from ingest and migration runs sync into an **exception queue** with assign, override (corrected payload), resolve, and audit history. UI: **Errors & Exceptions** tab.

**Q: Can analysts override bad rows without re-running the whole file?**  
A: Override stores corrected payload and history; reprocess/resume depends on workflow — ingest errors can be reprocessed; run validation exceptions are tracked for review and downstream re-run.

---

## 6. Validation & reconciliation

**Q: What validation is available?**  
A: Schema validation on ingest, configurable rule engine (required, pattern, range, conditional, lookups), destination payload validation against plugin schema, and candidate selection filters.

**Q: Reconciliation / BI export?**  
A: Funnel metrics, variance views, and JSON export for BI tools (e.g. Metabase) per project and per run.

---

## 7. Application compatibility

**Q: Which destination systems are supported?**  
A: Out of the box: **mock** (test), **file_export** (JSON files), **api_import** / Kraken-style REST (mock or live with `KRAKEN_MOCK_MODE=false`), **SAP** adapter (mock/live flags). New destinations = new plugin implementing schema + load.

**Q: Live API credentials?**  
A: Environment-specific; mTLS/proxy as above. Live Kraken/SAP endpoints must match customer contracts — adapters POST to configurable base URLs.

---

## 8. Known limitations (honest)

| Area | Limitation |
|------|------------|
| Serverless (Vercel) | Cold starts 3–5s; `/tmp` landing zone; worker not on serverless — use sync runs or external worker + DB |
| SSO | JWT only in v0.9 |
| Document / DB migration types | UI placeholders — not production-ready |
| Auto-optimisation of mappings | Suggestions only; no autonomous “fix my data” agent |
| Firewall traversal | Customer supplies proxy/mTLS config; we do not bypass firewalls |

---

## 9. Reference architecture (customer-deployed)

```
Browser → Reverse proxy (TLS) → React static UI
                              → FastAPI API → PostgreSQL
                              → Worker (optional, RUNNER_MODE=worker)
Outbound: API/Worker → [Proxy/mTLS] → Destination REST APIs
Inbound:  SFTP / manual upload → Landing zone → Ingest
```

---

## 10. Support & evidence

- Functional spec: [FUNCTIONAL_SPECIFICATION.md](./FUNCTIONAL_SPECIFICATION.md)  
- Capability matrix: [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md)  
- Runner deployment: [DEPLOYMENT_RUNNER.md](./DEPLOYMENT_RUNNER.md)  
- Automated tests: `pytest` (enterprise, ingest, pipeline, rules, mapping)

For RFP appendices, attach **CAPABILITY_MATRIX.md** as the one-page summary and this document as detailed FAQ responses.
