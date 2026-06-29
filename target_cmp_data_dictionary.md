# Target/CMP Sample Extract — Data Dictionary

**This file is illustrative test data, not a real export.** As established earlier in this
project: "Target/CMP" is a fictional stand-in for a legacy CRM/billing system, used only so
the migration utility prototype has something concrete to map *from*. None of the customer
names, account numbers, addresses, or reference codes below are real. Postcodes are real UK
formats but not tied to actual addresses. Use this freely for UI/QA testing — just don't treat
it as a real Severn Trent or Kraken data sample.

## File

`target_cmp_sample_extract.csv` — 20 rows, 15 columns, comma-delimited, header row included.

For AI QA specifically, use:

`samples/severn_trent/target_cmp_ai_gap_sample.csv` — compact 8-row sample intentionally containing enum and transform gaps (`CUST_TYPE_FLAG = X`, `ACCT_STATUS_CODE = Z`, `DOC_FORMAT_PREF = AUDIOBOOK`, `DOC_FORMAT_PREF = STD`) so **AI lookup gaps** and **AI transform rules** produce non-zero review items.

## Column reference

| Column | Type | Example | Notes |
|---|---|---|---|
| `CUST_ACCOUNT_NO` | string (9 digits) | `410583920` | Primary key in the source system. Maps to Kraken's `number` (required). |
| `CUST_TYPE_FLAG` | char(1) enum | `D`, `B`, `V`, `O` | `D`=Domestic, `B`=Business, `V`=Vacant, `O`=Occupier-unknown. Maps to Kraken's `accountType` (`AccountTypeChoices`) via lookup transform. |
| `CUST_TITLE` | string | `Mr`, `Mrs`, `Ms`, `Miss` | Blank for business/vacant accounts. |
| `CUST_FNAME` | string | `James` | Blank for business/vacant accounts. For business accounts, the business name is in this field instead (see rows 3, 9, 14). |
| `CUST_SNAME` | string | `Whitlock` | Blank for business/vacant accounts. |
| `ADDR_LINE_1` / `ADDR_LINE_2` | string | `14 Mulberry Close` | `ADDR_LINE_2` mostly blank; used for flat/unit numbers. |
| `ADDR_TOWN` | string | `Loughborough` | |
| `ADDR_POSTCODE` | string | `LE11 3QP` | Real UK postcode format, fictional assignment. |
| `STEPPED_RATE_FLAG` | char(1) bool | `Y` / `N` | Maps to Kraken's `isOnSteppedTariff` (required Boolean) via conditional transform. |
| `COMPLAINT_FLAG` | char(1) bool | `Y` / `N` | Whether the account has an open complaint. No direct 1:1 in the trimmed `AccountType` field list used in the prototype — a good example of a source field with no obvious destination match, useful for testing the "unmapped source field" state. |
| `ACCT_STATUS_CODE` | char(1) enum | `A`, `P`, `W`, `D` | `A`=Active, `P`=Pending, `W`=Withdrawn, `D`=Dormant. Maps to Kraken's `status` (`AccountStatus`, required) via lookup — note the source codes don't line up 1:1 with Kraken's enum values, so this is a good test case for the lookup/transform UI. |
| `DOC_FORMAT_PREF` | string enum | `STD`, `LARGE`, `BRAILLE` | Maps to Kraken's `documentAccessibility` (optional) — `STD` has no Kraken equivalent (Kraken only has `AUDIO`/`BRAILLE`/`LARGE_PRINT`, no "standard" value), another good edge case: what happens when a source value has no destination mapping at all. |
| `LEGACY_SYS_REF` | string (14 chars) | `CMP-0019204477` | Maps to Kraken's `urn` (optional) — the field Kraken explicitly provides for "reference number from a 3rd party enrolment." |
| `DATE_ACCOUNT_OPENED` | date (ISO) | `2014-03-11` | No direct field in the trimmed `AccountType` list in the prototype; real Kraken has `createdAt`, but that's typically system-set on record creation rather than backfilled — another useful edge case for transform/exclusion logic. |

## Edge cases deliberately included

- **Row 3, 9, 14** — business accounts (`CUST_TYPE_FLAG = B`) where `CUST_TITLE`/`CUST_SNAME` are blank and the business name sits in `CUST_FNAME`. Tests whether the mapping/transform layer handles conditional field reuse correctly.
- **Row 5** — vacant account (`V`) with no name fields populated at all.
- **Row 17** — `O` (occupier-unknown), a fourth account-type value, deliberately not pre-empted by the lookup transform shown in the UI mockup (which only handled `D`/`B`/`V`) — useful for testing "what happens when a lookup table doesn't cover every source value."
- **Rows with `COMPLAINT_FLAG = Y`** (rows 3, 7, 12) — fields with no destination match in the trimmed schema, to test the "source field with nowhere to go" UI state.
- **Rows 4, 11, 20** — non-`A` status codes (`P`=Pending, `W`=Withdrawn, `D`=Dormant respectively) to exercise the full `lookup` transform against Kraken's `AccountStatus` enum, not just the happy path.

## Suggested first test

Upload this file as the source extract in the prototype's "Upload source extract" step, then
confirm:
1. Auto-suggest mapping correctly proposes `CUST_ACCOUNT_NO → number` and `STEPPED_RATE_FLAG → isOnSteppedTariff` (close name/semantic match).
2. The `ACCT_STATUS_CODE → status` mapping requires a manual lookup table, since the codes don't match Kraken's enum names directly.
3. `COMPLAINT_FLAG` and `DATE_ACCOUNT_OPENED` surface as "mapped nowhere" — a good check that the UI doesn't silently drop unmapped source columns without flagging them.
