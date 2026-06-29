# High-Volume Migration Capacity — Analysis & Roadmap

**Question:** Can Migration Utility support **50,000–100,000 account migrations per day**?  
**Version analysed:** 0.11.0  
**Audience:** Customer technical leads, programme sponsors, engineering

---

## 1. Executive answer

| Deployment | 50k–100k accounts/day today? | Notes |
|------------|------------------------------|-------|
| **Vercel demo (serverless)** | **No** | 30s API timeout, no worker, ephemeral storage |
| **Docker Compose (default config)** | **Unlikely** | Single worker, full in-memory batch, selection cap 1,000 |
| **Docker/K8s with tuning (no code changes)** | **Partial (~10k–20k/day)** | Multiple scheduled runs, smaller waves, mock/fast destination |
| **With phased engineering (below)** | **Yes — achievable** | Chunked pipeline + parallel workers + destination batching |

**Honest customer statement:**  
The platform is **architected for governed migration workflows**, not yet optimised as a high-throughput bulk loader. Capacity is **Partial** in the capability matrix. Reaching 50k–100k/day is a **configuration + engineering** exercise, not a toggle — typically 2–4 weeks of implementation plus a dress-rehearsal load test.

---

## 2. Throughput requirement (what “50k–100k/day” means)

| Target | Per hour (24h) | Per minute | Per second |
|--------|----------------|------------|------------|
| **50,000/day** | ~2,083 | ~35 | ~0.58 |
| **100,000/day** | ~4,167 | ~69 | ~1.16 |

This is modest compared to streaming ETL systems — **if** each account can be validated, transformed, and loaded in under ~2 seconds end-to-end on average.

**Real constraint is usually the destination API**, not Python CPU:

- Kraken rate limits (`KT-CT-1199`) and enrollment throttling
- Network latency through corporate proxy
- Per-record vs bulk import contract with the destination vendor

---

## 3. Current architecture (relevant paths)

```
Upload CSV → PostgreSQL staging table
     ↓
Selection profile (optional) → tag rows to batch
     ↓
Worker claims run → Pipeline: ingest → validate → transform → load
     ↓
Load records + exception queue + reconciliation
```

**Key code paths:**

| Component | File | Behaviour today |
|-----------|------|-----------------|
| Staging extract | `connectors/staging.py` | Cursor-based `fetch_staged_rows(..., limit, after_row_number)` — **Phase 1 implemented** |
| Pipeline | `services/runner.py` → `_execute_batch_pipeline` | Loops chunks for staging source; checkpoint `last_row_number` per chunk |
| Chunk config | `config.py` → `run_chunk_size=500` | Honoured via `RUN_CHUNK_SIZE` env and `chunk_size` in batch config |
| Kraken load | `connectors/kraken.py` + `load_executor.py` | Sub-batched HTTPS with concurrency + rate-limit retry |
| Worker | `worker/runner_worker.py` | **One** queued run at a time per process |
| Selection default | `selection/service.py` | `max_candidates=1000` on seed profile |
| Load audit | `services/load_records.py` | One DB insert per loaded/failed record |

---

## 4. Bottlenecks (why 50k–100k is not guaranteed today)

### 4.1 Pipeline chunking (Phase 1 — implemented)

`StagingSourceConnector.extract()` reads staging rows in pages of `RUN_CHUNK_SIZE` (default 500) using `_row_number` cursor pagination.  
`RunService._execute_batch_pipeline()` loops validate → transform → load per chunk and writes `last_row_number` to `run.checkpoint` for resume.

**Remaining risk for 50k+:** Destination still receives one load call per chunk (not sub-batched); Kraken and audit DB writes are unchanged.

### 4.2 Destination load batching (Phase 2 — implemented)

`KrakenClient.import_accounts()` sub-batches via `LOAD_BATCH_SIZE` (default 200), runs up to `LOAD_CONCURRENCY` parallel requests, and retries HTTP 429 / `KT-CT-1199` with exponential backoff (`LOAD_RETRY_MAX`).

**Remaining risk for 50k+:** Single worker process, selection cap, and per-record audit DB writes (Phases 3–4).

### 4.3 Single worker process

`process_next_queued_run()` claims one run; docker-compose ships one `worker` replica. No horizontal scale-out.

### 4.4 Selection volume cap

Default seed profile: `max_candidates=1000`.  
A single run with selection will not exceed 1,000 unless profile/config is changed.

### 4.5 Load record persistence overhead

100k accounts/day → 100k `load_records` rows/day with full request/response JSON.  
Bulk `INSERT` or summary-only mode not implemented.

### 4.6 Serverless unsuitable

Vercel: `maxDuration: 30` seconds, no background worker, `/tmp` storage.  
Not viable for bulk migration regardless of tuning.

### 4.7 Destination rate limits

Kraken documents `KT-CT-1199` (rate limit) in enrollment range.  
No adaptive throttling in the load adapter today.

---

## 5. What you *can* do today (operational workarounds)

Without code changes, a pilot can process **multiple waves per day**:

| Tactic | How | Approx. daily capacity |
|--------|-----|------------------------|
| **Multiple runs** | 10 runs × 5,000 accounts each | ~50k (if each run completes) |
| **Multiple batches per run** | Create run with 10 batches × 5,000 | Same, but one run entity |
| **Raise selection limit** | Set `max_candidates` / `candidate_limit` in profile & run config | Removes 1,000 cap |
| **Mock destination** | `KRAKEN_MOCK_MODE=true` | Fast — proves pipeline, not live API |
| **Dedicated worker VM** | Scale CPU/RAM; `RUNNER_MODE=worker` | Reduces OOM risk for ~10k batches |
| **Off-peak scheduling** | Cron/worker runs waves overnight | Spreads load; does not raise per-run throughput |

**Example run config (10k wave):**

```json
{
  "entity": "account",
  "use_selection": true,
  "candidate_limit": 10000,
  "use_rules": true,
  "require_approved_rules": true,
  "async": true
}
```

Create **5–10 waves/day** to approach 50k–100k.  
This is operationally fragile (manual scheduling, no chunking, memory spikes) — acceptable for dress rehearsal, not production cutover.

---

## 6. Implementation roadmap to 50k–100k/day

### Phase 1 — Chunked pipeline (P0) — **Done (v0.11.0+)**

**Goal:** Honour `RUN_CHUNK_SIZE`; constant memory per batch.

| Task | Status |
|------|--------|
| Cursor-based staging fetch | `fetch_staged_rows(..., limit=chunk_size, after_row_number=...)` |
| Chunk loop in pipeline | `_execute_batch_pipeline()` in `services/runner.py` |
| Checkpoint per chunk | `run.checkpoint.last_row_number` + resume via `resume_from_checkpoint` |
| Progress | `progress_pct` / message updated per chunk |

**Expected gain:** Stable 10k–50k per run without OOM; resume after failure mid-batch.

Set `RUN_CHUNK_SIZE=500` (default) or higher in `.env` / worker deployment.

### Phase 2 — Destination load batching & rate limits (P0) — **Done (v0.11.0+)**

| Task | Status |
|------|--------|
| Sub-batch API calls | `LOAD_BATCH_SIZE` (default 200) via `run_batched_load()` |
| Concurrency limit | `LOAD_CONCURRENCY` (default 4) with thread pool |
| Retry + backoff | HTTP 429 / `KT-CT-1199` — `LOAD_RETRY_MAX`, exponential backoff |
| Config | `LOAD_BATCH_SIZE`, `LOAD_CONCURRENCY`, `LOAD_MAX_RPS`, `LOAD_RETRY_MAX` |

**Expected gain:** Saturate allowed destination throughput without tripping rate limits.

Per-run overrides: pass `load_batch_size`, `load_concurrency`, etc. in `run_config`.

### Phase 3 — Parallel workers (P1, ~3–5 days)

| Task | Detail |
|------|--------|
| Run claiming | `SELECT … FOR UPDATE SKIP LOCKED` on `migration_runs` |
| Multiple worker replicas | K8s `replicas: 4` or systemd instances |
| Idempotent load | Destination idempotency keys / URN dedup |

**Expected gain:** 4× throughput with 4 workers (bounded by DB and destination).

### Phase 4 — Database & audit optimisation (P1, ~1 week)

| Task | Detail |
|------|--------|
| Staging indexes | `(_project_id, _status, _batch_id)`, `(_row_number)` |
| Bulk load record insert | `executemany` or `COPY` for audit rows |
| Summary-only mode | `LOAD_AUDIT_MODE=summary` — counts only, sample payloads |
| PgBouncer | Connection pooling for worker fleet |

**Expected gain:** Lower DB write amplification at 100k+/day.

### Phase 5 — Wave orchestration (P2, ~1 week)

| Task | Detail |
|------|--------|
| Daily wave scheduler | API/cron: create N runs of M accounts on schedule |
| Cohort readiness gate | Account health check before wave |
| Auto-pause on error rate | Stop wave if failure % exceeds threshold |

**Expected gain:** Operational “50k/day” or “100k/day” button for migration programme.

---

## 7. Target architecture (50k–100k/day)

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  Scheduler  │────►│  Run queue (PostgreSQL)                   │
│  (waves)    │     │  Wave 1..N × 10k accounts                 │
└─────────────┘     └───────────────┬──────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        ┌──────────┐          ┌──────────┐          ┌──────────┐
        │ Worker 1 │          │ Worker 2 │          │ Worker N │
        └────┬─────┘          └────┬─────┘          └────┬─────┘
             │ chunk 500           │                     │
             ▼                     ▼                     ▼
        ┌─────────────────────────────────────────────────────┐
        │  Staging (PostgreSQL) — indexed, cursor reads        │
        └─────────────────────────┬───────────────────────────┘
                                  │ batched HTTPS (100–500/rec)
                                  ▼
                        ┌──────────────────┐
                        │  Destination API  │
                        │  (rate-limited)   │
                        └──────────────────┘
```

---

## 8. Infrastructure sizing (indicative)

For **100k accounts/day** with live Kraken API (assumes ~2s average per account including API latency):

| Component | Recommendation |
|-----------|----------------|
| **API** | 2 vCPU, 4 GB RAM (stateless, light) |
| **Workers** | 4× (2 vCPU, 4 GB RAM) |
| **PostgreSQL** | 4 vCPU, 16 GB RAM, SSD; PgBouncer |
| **Landing storage** | 50 GB+ (extracts + exports) |
| **Network** | Low-latency path to destination; proxy configured |

**Dress rehearsal:** Run 10k wave in UAT; measure records/sec, p95 latency, error rate, `KT-CT-1199` frequency. Extrapolate before production cutover.

---

## 9. Customer FAQ (copy-paste)

**Q: Can you migrate 50k–100k accounts per day?**  
A: Yes, as a **programme target** with the right deployment (VPC Docker/Kubernetes, async workers, tuned chunk sizes) and **destination API capacity** agreed with the billing platform vendor. The current v0.11 release supports batch-oriented migration with async workers; sustained 50k–100k/day requires the chunked-pipeline and load-batching enhancements in our high-volume roadmap (Phases 1–2), plus a load test in your UAT environment.

**Q: What do we need from our side?**  
A: Destination API rate limits and bulk import contract, UAT credentials, network egress (proxy/mTLS if required), PostgreSQL hosting, and a dress-rehearsal window to validate throughput.

**Q: Is the hosted Vercel demo sufficient?**  
A: No. Use it for mapping and workflow UX only. Production volume runs deploy in your VPC with workers.

---

## 10. Recommended next steps

1. **Agree SLA** — 50k or 100k? Over what hours (8h batch window vs 24h)?  
2. **Dress rehearsal** — 10k accounts in customer UAT with live (or pre-prod) API  
3. ~~**Implement Phase 1**~~ — chunked pipeline ✅  
4. ~~**Implement Phase 2**~~ — destination batching + rate-limit handling ✅  
5. **Scale workers** — Phase 3 after load test shows DB/destination headroom  
6. **Update capability matrix** — move “Bulk scale” from Partial → Yes after validated test

---

## 11. Effort summary

| Phase | Effort | Unlocks |
|-------|--------|---------|
| Phase 1 — Chunked pipeline | Done | Memory-safe 10k–50k per run, resume |
| Phase 2 — Load batching | Done | Destination throughput, rate limits |
| Phase 3 — Parallel workers | ~3–5 days | Multi-run concurrency |
| Phase 4 — DB optimisation | ~1 week | 100k+ audit rows/day |
| Phase 5 — Wave scheduler | ~1 week | Operational “daily quota” UX |

**Total:** ~4–5 weeks engineering + 1 week UAT load test before customer commitment.

---

*Related: [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md) · [DEPLOYMENT_RUNNER.md](./DEPLOYMENT_RUNNER.md) · [CLIENT_PRESENTATION.md](./CLIENT_PRESENTATION.md)*
