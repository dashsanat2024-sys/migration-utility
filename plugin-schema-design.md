# Migration Utility — Destination-as-Plugin Redesign

## The core shift

Today (v0.7) the destination is a hard-coded adapter key (`kraken`, `sap`, `file_export`) chosen from a dropdown, and the field catalog is something a user uploads manually for *both* sides. That works, but it puts the burden of knowing the destination's contract on the human.

In real migrations like **Severn Trent Water → Kraken**, the direction of authority is reversed: Kraken *is* the platform of record and publishes a fixed account/billing/CRM data contract. The legacy system (Severn Trent's CAST mainframe billing data) has to conform to *Kraken's* shape — not the other way round. Kraken's own delivery teams describe this as a repeatable, audited "Build, Operate and Transfer" migration model precisely because the destination schema doesn't move — only the mapping into it does.

So the redesign treats **every destination as a plugin that owns and publishes its own schema**, and the source's job is only ever to map onto that already-known contract.

```
┌────────────────────┐      schema.json       ┌─────────────────────────┐
│  Destination Plugin │ ──────────────────────▶│   Schema Contract Panel  │
│  (kraken-billing,    │   {fields, types,       │   (always visible,      │
│   sap-crm, file_export,│  required, constraints}│    read from plugin,    │
│   custom plugin…)     │                         │    never hand-typed)    │
└────────────────────┘                         └────────────┬─────────────┘
                                                              │ source fields map onto this
                                                ┌─────────────▼─────────────┐
                                                │   Source extract fields    │
                                                │   (CSV/JSON/XML, any       │
                                                │    legacy system)          │
                                                └────────────────────────────┘
```

## What changes structurally

| Today | Redesign |
|---|---|
| Destination = adapter key in `connectors/registry.py` | Destination = **plugin package** with a `manifest.json` (id, label, version, auth config) + a `schema.json` it publishes at runtime |
| Both source and target field catalogs uploaded by user as CSV | **Destination schema is fetched from the plugin**, not uploaded. Only the *source* catalog is uploaded/parsed |
| `target_fields` table is generic rows | Destination schema includes **type, required/optional, constraints (enum, regex, max length), and a stable field key** — enough to drive validation and UI rendering without extra config |
| Adding a new destination = backend code change | Adding a new destination = **dropping in a plugin** that implements a small interface: `get_schema()`, `validate(payload)`, `load(payload)`. The UI has nothing destination-specific in it at all |
| Mapping screen treats both sides symmetrically | Mapping screen is **asymmetric on purpose**: destination fields are fixed sockets (required fields visually "locked" until filled); source fields are the moving part being plugged in |

### Plugin interface (conceptual)

```python
class DestinationPlugin(Protocol):
    id: str                      # "kraken-billing-v3"
    label: str                   # "Kraken Billing Import"
    version: str

    def get_schema(self) -> Schema:
        """Returns required/optional fields, types, constraints.
        Kraken's plugin calls its own /schema endpoint or ships a
        versioned schema.json; SAP's plugin maps IDoc segments;
        file_export's plugin reads a configurable JSON schema file."""

    def validate(self, payload: dict) -> list[ValidationError]: ...
    def load(self, payload: dict) -> LoadResult: ...
```

This is the same shape used by real ETL/iPaaS tools (Informatica, MuleSoft, Boomi, Astera) — connectors are modular and metadata-driven, and mapping is always described as "source schema → target schema," with the target schema treated as the authority once chosen. It's also exactly how Kraken's own onboarding works at scale: 40+ utilities across 27 countries map into the *same* Kraken contract rather than Kraken adapting per-client.

## What this means for the UI

1. **A visible "Destination plugin" card, not a dropdown.** It shows which plugin is active, its version, and live counts of required / optional / mapped fields — sourced directly from `get_schema()`, never hand-maintained.
2. **Required fields are rendered as locked sockets.** Amber border = required and still empty (blocks the run). Dashed grey = optional. Green = mapped and passing transform validation. This status is the same vocabulary used in the Reconciliation and Runs panels, so a user never has to relearn color meaning between screens.
3. **Swapping the plugin reloads the whole right-hand mapping panel.** Going from `kraken-billing-v3` to `sap-crm` or a custom plugin doesn't change any code — it changes which schema.json is loaded, and the mapping rows reset against the new contract. This is the single biggest proof-point that the tool is genuinely generic rather than "Kraken-shaped with extra labels," which was a risk in the current vendor-neutral-naming approach.
4. **Auto-suggest still works, but in one direction.** Fuzzy matching proposes *source → destination* links (e.g. `CUST_ACCOUNT_NO` → `account_number`), the same fuzzy-catalog matching already in `fields/service.py`, just no longer needing a destination catalog upload step.
5. **Transform column stays inline**, reusing the existing transform type vocabulary (`copy`, `lookup`, `concat`, `pad_left`, `conditional`, etc.) so the rule engine doesn't need to change — only where the destination side of the mapping comes from changes.
6. **Workflow locking is unchanged**: draft → in_review → approved → signed_off still governs who can edit mappings, since that's an org-process concern, not a schema concern.

## Visual language (why these choices)

- **Dark, data-dense, mono for field names** — kept from the existing design system (`--bg`, `--bg-card`, JetBrains Mono) because this is operational tooling used by mapping leads and business analysts running the same screen for hours, not a marketing surface. Consistency with the documented design tokens matters more than novelty here.
- **Status color is the one piece of "branding"** — amber (pending/required), green (valid), red (failing). This mirrors `StatusBadge` and `WorkflowStepper`, already documented components, so the new mapping screen doesn't introduce a parallel color vocabulary.
- **The plugin card uses a gradient icon tile** as the one deliberately distinctive visual element — signaling "this is a pluggable, swappable unit" the way an app icon signals an installed extension, which is the actual mental model we want the user to form.

## Suggested incremental build order

1. Define `Schema` / `SchemaField` Pydantic models + the plugin `Protocol` (backend-only, no UI change yet)
2. Port `kraken.py` and `sap.py` adapters to implement `get_schema()` — for Kraken this can start as a static versioned JSON checked into the plugin folder, later swapped for a live `/schema` call against Kraken's account API
3. Add `GET /projects/{id}/destination/schema` endpoint that proxies to the active plugin
4. Update `FieldCatalogPanel` to stop accepting a target-fields upload and instead fetch from that endpoint
5. Rebuild the mapping table with the locked/dashed/filled chip states shown in the prototype
6. Add the "Swap destination plugin" action — re-running step 3/4 against a different plugin id, with a confirmation step if mappings already exist (since switching schemas can orphan mappings)

This keeps the validation engine, transform engine, workflow state machine, and run/reconciliation pipeline completely untouched — only the *source of truth for the destination schema* moves from "uploaded CSV" to "plugin-published contract."
