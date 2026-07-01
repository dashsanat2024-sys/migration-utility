# Architecture vs implementation (UI update)

Reference: [architecture_comparison.html](./architecture_comparison.html) (original TCS reference vs Arthavi build).

**Last updated:** v0.12 UI — guided journey, wave programme panel, STW branding removed from UI.

## Guided user flow (5 phases)

| Phase | UI tabs | Reference capability |
|-------|---------|-------------------|
| 1 · Prepare | Guided Setup, Upload & Stage | File extract, staging |
| 2 · Map & Transform | Schema & Mapping, Rules, Tariffs, Utility Transforms | Field mapping, validation, industry transforms |
| 3 · Select & Health | Candidate Selection, Account Health | Inclusion/exclusion, cohort readiness |
| 4 · Execute | Migration Runs, Wave Programme | Single run, resume, daily waves |
| 5 · Reconcile | Reconciliation, Errors & Exceptions | Funnel, BI export, exception queue |

## Gap status (post UI work)

| Area | Status | Notes |
|------|--------|-------|
| Candidate selection | **Built** | `CandidatesPanel` + wizard step; criteria preview |
| Migration runs | **Built** | Async worker, resume from checkpoint |
| Wave orchestration | **Built** | `WavesPanel` + Phase 5 API |
| Tariff mapping | **Built** | Tariff wizard + mapping service |
| Utility transforms | **Built** | Former STW rules; generic labels in UI |
| Account health gate | **Built** | Required for wave scheduling when enabled |
| Prod/replica DB replication | Roadmap | Not in scope for file-upload MVP |
| Legacy system webhooks | Roadmap | Post-migration callbacks |
| Custom report builder | Partial | BI export exists; drag-drop builder TBD |
| Document transfer | Roadmap | Document migration type disabled |

## UI branding

- Vendor-specific names removed from labels (utility transforms, generic connector names).
- Backend API paths retain `stw-transform-rules` for compatibility; UI shows **Utility Transforms**.
- Default project landing tab: **Guided Setup** (wizard).
