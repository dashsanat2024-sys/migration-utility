# Account Health & Kraken Fallout Strategy

**Version:** 0.10.0  
**Audience:** Migration programme leads, data owners, Kraken integration teams

---

## Problem statement

Kraken exposes **~920 GraphQL error codes** (`KT-CT-*` core + `KT-GB-*` UK market). Discovering data or operational issues **during** a migration run is expensive. The goal is to **identify blockers upfront**, assign them to the right owners, remediate, and reprocess — before production cutover.

---

## Strategy pillars

### 1. Early data profiling (static)

On ingest, the platform already computes column stats and anomalies. Account Health extends this with **per-account checks** against:

- Kraken required fields (from destination plugin schema)
- Account type enums, business references, duplicate account numbers
- Contract/party data quality patterns linked to `KT-CT-10001`–`10044`, `10901+`

### 2. Operational account health (transient)

Static data alone is insufficient. These **operational blockers** exclude accounts from a migration cohort even when data looks valid:

| Signal (source extract) | Example Kraken risk | Owner |
|-------------------------|---------------------|-------|
| Pending payment | Billing/charges range `13001+` | Billing ops |
| Unpaid bill due | Billing/charges | Billing ops |
| Meter appointment scheduled | Meters/devices `3810–3997` | Metering |
| Active contract journey | `KT-CT-10008`, `10035` | Billing ops |
| Ongoing provider switch | `KT-CT-10027`, `10301+` | Billing ops |
| Leave-supplier in progress | `KT-CT-10305–10311` | Billing ops |

Source field names are configurable via aliases in `account_health/checks.py` (e.g. `pendingPayment`, `PENDING_PAYMENT`).

### 3. Cohort readiness score

Each account receives a **readiness score (0–100)** and status:

| Status | Meaning |
|--------|---------|
| **ready** | Score ≥ 85, no blockers — eligible for migration wave |
| **conditional** | Score 60–84 or warnings only — review before including |
| **blocked** | Blocker present or score < 60 — exclude until remediated |

Cohort score = average of all assessed accounts.

### 4. Kraken error code catalog

Indexed in `migration_utility/kraken/errors/`:

- **57 codes** with confirmed message text (sourced from [Portsmouth Water Kraken developer portal](https://developer.pwl.kraken.tech/graphql/reference/error-codes))
- **~920 codes** indexed by numeric range and category
- API: `GET /api/kraken/error-codes`, `/summary`, `/pre-migration`

Health checks **predict** which Kraken codes would fire if the account were loaded today.

### 5. Fallout management

Blocked/conditional accounts sync to the **exception queue** with:

- `kraken_error_code` — primary predicted or actual code
- `root_cause_category` — `data_quality`, `operational_blocker`, `mapping`, `kraken_validation`, etc.
- `owner_role` — `billing_ops`, `metering`, `mapping_lead`, `migration_engineer`
- `remediation_hint` — human-readable fix guidance
- `fallout_status` — `open` → remediated → reprocessed

Kraken **load failures** during runs are auto-classified via the same taxonomy.

**Workflow:** Assess → Sync fallout → Assign owner → Remediate source → Reprocess → Re-assess.

---

## Testing approach (built into UI)

`GET /api/projects/{id}/migration-testing/plan` returns phases:

1. **Mapping validation** — field catalog + transform preview
2. **Product-build validation** — tariff mapping dry-run
3. **Account health gate** — cohort readiness before wave
4. **AI-led testing** (optional) — anomaly + Kraken code driven cases
5. **Parallel bill validation** (optional)
6. **Volume testing** — worker mode, chunk sizes, rate limits (`KT-CT-1199`)
7. **Dress rehearsal** — full pre-prod run with reconciliation

---

## UI

**Account Health** tab (Execution section):

- Run assessment on staged data
- Cohort readiness dashboard
- Predicted Kraken codes histogram
- Sync to fallout queue
- Migration testing checklist

**Errors & Exceptions** tab shows Kraken code, root cause, and owner on each fallout item.

---

## API quick reference

| Endpoint | Purpose |
|----------|---------|
| `POST /api/projects/{id}/account-health/assess` | Run full cohort assessment |
| `GET /api/projects/{id}/account-health/latest` | Latest assessment summary |
| `GET .../account-health/{id}/records?status=blocked` | Per-account findings |
| `POST .../account-health/{id}/sync-fallout` | Push to exception queue |
| `GET /api/kraken/error-codes/summary` | Catalog statistics |
| `GET /api/kraken/error-codes/pre-migration` | High-relevance pre-load codes |

---

## Honest limits

- Only **57** of ~920 Kraken codes have verified message text in our catalog; the rest are **indexed by range** for recognition and categorization — not invented descriptions.
- Operational checks depend on **source extract fields** being present; if legacy Target/CMP does not export payment/journey flags, those checks are no-ops until mappings are added.
- Live Kraken pre-validation (calling GraphQL dry-run mutations) is a future enhancement; current scoring is **rules-based prediction** from staged data + catalog mapping.

---

## Related docs

- [kraken-error-codes-reference.md](../kraken-error-codes-reference.md) — sourced error code research
- [CUSTOMER_FAQ_RFP.md](./CUSTOMER_FAQ_RFP.md) — customer-facing FAQ
- [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md) — sales matrix
