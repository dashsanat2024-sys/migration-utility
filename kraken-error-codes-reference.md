# Kraken API Error Code Reference (Real, Sourced)

**Source:** `developer.pwl.kraken.tech/graphql/reference/error-codes` (Portsmouth Water's
public Kraken developer portal). Severn Trent's own portal (`developer.st.kraken.tech`)
references this same error-codes page but doesn't render the detail server-side at the URL
I could fetch — Portsmouth Water's instance, on the **same shared Kraken core platform**,
does. Every `KT-CT-*` code is identical across all Kraken water/energy/telco instances
(Severn Trent, Portsmouth Water, Octopus Energy, TalkTalk, MAINGAU, etc.) — confirmed by
cross-checking the same code numbers appearing verbatim across multiple instances' docs
during research. `KT-GB-*` codes are UK-market-specific and apply to any UK Kraken
deployment, including Severn Trent.

**Scope confirmed from the live page:** **~920 total error codes** — roughly **700 `KT-CT-*`**
(core, shared across every Kraken deployment worldwide) and **~220 `KT-GB-*`** (UK market
rules, relevant to Severn Trent as a UK water utility).

**Honesty about coverage:** the source page is long enough that a single fetch reliably
returns full detail (type + message + description) for only the first ~70 codes before the
response is truncated — this happens consistently regardless of how the page is requested,
suggesting it's the practical ceiling for one retrieval rather than something I can page
around easily. Section 1 below has **every code number that exists**, which is itself useful
for recognizing/categorizing codes you encounter. Section 2 has **full detail** for every code
I was able to actually retrieve. I did not invent descriptions for codes outside Section 2 —
where I don't have the real text, I've left it out rather than guess.

---

## 1. Complete code index (all ~920 codes, organized by range)

### `KT-CT-*` — Core errors (shared across all Kraken instances)

**Contracts & agreements** (`10001`–`10044`): 10001, 10003, 10005–10013, 10015, 10017–10044

**Auto top-up / prepay** (`10201`–`10205`): 10201–10205

**Leave-supplier / switching process** (`10301`–`10358`): 10301–10312, 10313–10358

**Misc single codes**: 10703, 10801, 10820, 10821

**Account / business / migration applications** (`10901`–`10991`): 10901–10978, 10982–10991

**Authorization / business linkage** (`11100`–`11112`, `1111`–`1163`): 11100–11112, 1111–1163 (mixed 4 and 5-digit — note `1111` itself is the classic "Unauthorized" code referenced in Kraken's own API announcements)

**Account application detail** (`11201`–`11218`): 11201–11218

**Contract notes / journeys cont'd** (`11301`–`11333`): 11301–11333

**Enrollment** (`11401`–`11404`, `1140`–`1199`): 11401–11404, 1140–1199 (includes `1188` query complexity limit, `1189` max node count, `1199` rate limit — all confirmed from guides)

**Pricing / quoting** (`12001`–`12106`): 12001–12106

**Misc** (`12201`–`12301`): 12201–12301

**Telco-specific** (`12401`–`12612`): 12401–12612 (energy/telco-only fields per changelog; unlikely relevant to a water migration)

**Misc** (`12701`–`12905`): 12701, 12702, 12901–12905

**Billing/charges** (`13001`–`13104`): 13001–13104

**Misc** (`13201`–`13808`): 13201–13204, 13401, 13501, 13601–13605, 13701–13708, 13801–13808

**Auth/session** (`1401`–`1409`): 1401–1409

**Misc** (`14101`–`14802`): 14101–14103, 14201–14222, 14401–14403, 14601–14603, 14801, 14802

**Session/token** (`1501`–`1701`): 1501–1516, 1601–1609, 1701

**Meters & devices** (`3810`–`3997`): 3810–3838, 3921–3997 — this range is meter/device-heavy and likely the most relevant range for a utility migration beyond accounts/contracts

**Misc** (`4010`–`4413`): 4010, 4011, 4023, 4101, 4110–4150, 4155, 4177–4199, 4231–4237, 4301–4390, 4410–4413

**Misc** (`4501`–`4930`): 4501, 4616–4647, 4710–4723, 4810, 4910–4930

**Tariffs/pricing** (`5211`–`5821`): 5211–5213, 5311–5316, 5411–5427, 5450, 5460–5466, 5511–5523, 5611–5615, 5711–5713, 5811–5821

**Misc** (`6323`–`6732`): 6323, 6420–6434, 6611–6637, 6710–6732

**Misc** (`7010`–`7731`): 7010–7012, 7023, 7123–7127, 7223, 7323, 7423–7429, 7523, 7610–7663, 7701, 7702, 7711–7731

**Misc** (`7810`–`8011`): 7810, 7813, 7899, 8010, 8011

**Misc** (`8101`–`8956`): 8101–8107, 8201–8227, 8310–8312, 8411–8416, 8501, 8610, 8611, 8710, 8801, 8802, 8901–8956 (account/business linkage detail — overlaps conceptually with the 10901-range)

**Misc** (`9010`–`9911`): 9010–9023, 9201–9225, 9401–9411, 9601–9606, 9701–9709, 9901–9911

### `KT-GB-*` — UK market-specific errors (apply to Severn Trent as a UK water utility)

10101–10103, 10206–10208, 10501–10504, 10601–10609, 10701, 11001–11019, 1120, 1121,
12401, 12402, 12801–12803, 1301, 13901–13903, 14001, 14002, 1501, 1502, 3810–3812,
3910–3922, 3930, 3931, 4011–4015, 4019–4058, 4101–4144, 4210–4245, 4301–4305, 4513,
4610–4629, 5110–5117, 5411–5419, 5601, 5602, 5610, 5611, 6111, 6211, 6212, 6216, 6219,
6312, 6314, 6411–6416, 6610–6640, 6811–6814, 7601, 8801, 9310–9327, 9510–9521, 9710, 9711

---

## 2. Fully detailed entries (confirmed text, retrieved directly)

Format: **Code** — Error Type — what triggers it — the literal `message` string returned to the API caller.

| Code | Type | Trigger | API `message` |
|---|---|---|---|
| KT-CT-10001 | VALIDATION | Creating a contract that overlaps an existing one for the same party | "Party is already under contract." |
| KT-CT-10003 | NOT_FOUND | Contract lookup failed | "Contract not found." |
| KT-CT-10005 | VALIDATION | Neither an identifier nor account number supplied when searching for a contract | "Missing required parameter: either identifier or accountNumber must be provided." |
| KT-CT-10006 | NOT_FOUND | Account lookup failed | "Account not found." |
| KT-CT-10007 | APPLICATION | Contract termination failed for an internal reason | "Unable to terminate contract." |
| KT-CT-10008 | APPLICATION | An action attempted on a contract that has an active journey in progress | "The contract is currently undergoing an active journey." |
| KT-CT-10009 | VALIDATION | A supplied contract term doesn't match the expected format | "Provided term term is not of the valid format." |
| KT-CT-10010 | VALIDATION | Two terms of the same type supplied in one term set | "Duplicate term type found in the provided term set." |
| KT-CT-10011 | APPLICATION | Varying contract terms failed internally | "Unable to vary contract terms." |
| KT-CT-10012 | APPLICATION | A contract variation would breach the contract | "Contract variation implies breach." |
| KT-CT-10013 | VALIDATION | Termination date requested is after the contract's end date | "Requested termination date is invalid." |
| KT-CT-10015 | VALIDATION | Supply point termination context couldn't be serialized | "Supply point termination context is not serializable." |
| KT-CT-10017 | NOT_FOUND | Contract journey lookup failed | "The contract journey could not be found." |
| KT-CT-10018 | VALIDATION | Invalid contract subject specification | "The provided contract subject is invalid." |
| KT-CT-10019 | APPLICATION | Creating a contract would itself breach it | "Contract creation implies breach." |
| KT-CT-10020 | VALIDATION | Malformed contract-party payload | "The provided contract party payload is invalid." |
| KT-CT-10021 | NOT_FOUND | Business lookup failed | "Business not found." |
| KT-CT-10022 | VALIDATION | Action attempted on an already-terminated contract | "Contract already terminated." |
| KT-CT-10023 | VALIDATION | Action attempted on an already-revoked contract | "Contract is already revoked." |
| KT-CT-10024 | VALIDATION | Action attempted on an expired contract | "Contract already expired." |
| KT-CT-10025 | VALIDATION | Action attempted on a contract that hasn't started | "Contract has not started yet." |
| KT-CT-10026 | VALIDATION | Actualizing the contract would breach it | "Contract actualization implies breach." |
| KT-CT-10027 | VALIDATION | Termination blocked because a supplier-switch is already in progress | "There is an ongoing provider switch." |
| KT-CT-10028 | VALIDATION | Agreements supplied span more than one market | "Contract market mismatch." |
| KT-CT-10029 | VALIDATION | Contract query submitted with no filters at all | "Missing contract filters." |
| KT-CT-10030 | SERVICE_AVAILABILITY | Filtering contracts by subject isn't implemented yet | "Filter by subject is not implemented." |
| KT-CT-10031 | VALIDATION | Contract query supplied both/neither of account+business party filters | "Invalid party filter." |
| KT-CT-10032 | VALIDATION | Action attempted on a contract that's already started (when it shouldn't be) | "Contract has already started." |
| KT-CT-10033 | VALIDATION | A specified term failed to save | "Unable to save term." |
| KT-CT-10034 | APPLICATION | Contract journey type not recognized | "Unknown contract journey type." |
| KT-CT-10035 | APPLICATION | Tried to process a contract journey that isn't active | "Cannot process a non-active contract journey." |
| KT-CT-10036 | APPLICATION | No manager configured to process this contract journey type | "The contract journey manager is not found." |
| KT-CT-10037 | SERVICE_AVAILABILITY | Contract-notes feature toggled off for this client | "Contract notes feature is disabled." |
| KT-CT-10038 | VALIDATION | Note-reason slug doesn't match any configured reason | "Contract note reason not found." |
| KT-CT-10039 | VALIDATION | Mutation called with none of its (individually optional) affected fields | "At least one of the affected fields must be provided." |
| KT-CT-10040 | APPLICATION | Contract rescission failed internally | "Unable to rescind contract." |
| KT-CT-10041 | VALIDATION | Action attempted on an already-rescinded contract | "Contract is already rescinded." |
| KT-CT-10042 | VALIDATION | Supplied agreements already belong to a different contract | "One or more agreements are already attached to a different contract." |
| KT-CT-10043 | VALIDATION | Neither an account-contract nor business-contract identifier supplied | "At least one contract identifier must be provided." |
| KT-CT-10044 | VALIDATION | Termination date requested is on/before the contract start date | "Termination date must be after the contract start date." |
| KT-CT-10201 | SERVICE_AVAILABILITY | Auto top-up feature disabled for this client | "Endpoint disabled." |
| KT-CT-10202 | VALIDATION | Device ID supplied doesn't match any device | "Invalid data." |
| KT-CT-10203 | VALIDATION | Auto top-up attempted on a non-prepay device | "Invalid data." |
| KT-CT-10204 | VALIDATION | Top-up amount below the configured minimum | "Invalid data." |
| KT-CT-10205 | NOT_FOUND | No active auto-top-up config matches the account/device pair | "Active auto top-up config not found." |
| KT-CT-10301 | VALIDATION | Leave-supplier process couldn't be started (validation failure) | "Unable to instigate leave supplier process." |
| KT-CT-10302 | NOT_FOUND | Invalid reference for a leave-supplier process | "Invalid data." |
| KT-CT-10303 | SERVICE_AVAILABILITY | `PrepareAccount` mutation disabled in this environment | "Mutation not enabled in this environment." |
| KT-CT-10304 | SERVICE_AVAILABILITY | Leave-supplier mutations disabled in this environment | "Mutation not enabled in this environment." |
| KT-CT-10305 | APPLICATION | Can't cancel leave-supplier process — market actions are no longer cancellable | "Failed to cancel leave supplier process - market actions are no longer cancellable." |
| KT-CT-10306 | SERVICE_AVAILABILITY | Cancellation workflow for leave-supplier process isn't configured | "Failed to cancel leave supplier process - the cancellation workflow has not been configured." |
| KT-CT-10307 | APPLICATION | Cancelling the underlying market actions failed | "Failed to cancel leave supplier process - failed to cancel market actions." |
| KT-CT-10308 | APPLICATION | Generic leave-supplier cancellation failure | "Failed to cancel leave supplier process." |
| KT-CT-10309 | SERVICE_AVAILABILITY | Leave-supplier update service not enabled | "Failed to update leave supplier process - the service is not enabled." |
| KT-CT-10310 | APPLICATION | Process status doesn't allow updates right now | "Failed to update leave supplier process. The process status is not in updatable status." |
| KT-CT-10311 | APPLICATION | Process status doesn't allow cancellation right now | "Failed to cancel leave supplier process. The process status is not in cancellable status." |
| KT-CT-10312 | SERVICE_AVAILABILITY | Enrollment mutation disabled in this environment | "Mutation not enabled in this environment." |

*(Detail retrieval reliably stops around this point per fetch — see note above. The index in Section 1 has every remaining code number, but I don't have verified message/description text for codes after ~10312 to report responsibly.)*

---

## 3. What's most relevant to a Target/CMP → Kraken migration utility

Based on the **confirmed** entries above plus the index of categories:

- **`10006` (Account not found)** and **`10021` (Business not found)** are the two most likely errors a bulk account-import job would hit per-record — worth building explicit retry/dead-letter handling around both in the migration utility's error-handling UI.
- **`10039` ("at least one of the affected fields must be provided")** is a generically useful pattern: many Kraken mutations require *something* to change, which matters for idempotent re-runs of a migration batch (re-submitting an unchanged record may itself error).
- **The `3810`–`3997` meter/device range** and **`8901`+ account/business-linkage range** are, by category, the most relevant to a water-utility CRM/billing migration, but I don't have confirmed message text for these yet — flagged in the index as priority ranges to fetch in detail if/when this matters for real implementation.
- **`KT-GB-*` codes** apply specifically because Severn Trent is a UK deployment — any GB-market validation logic (e.g. regulatory identifiers, UK-specific billing rules) would surface through this prefix rather than `KT-CT-*`.

## 4. Sources

- Full error code reference (index + first ~70 detailed entries): https://developer.pwl.kraken.tech/graphql/reference/error-codes
- Kraken API announcement confirming `KT-CT-1111`/`KT-CT-1143` authorization error behavior: https://announcements.kraken.tech/announcements/public/56/
- GraphQL guides confirming `KT-CT-1188` (query complexity), `KT-CT-1189` (max node count), `KT-CT-1199` (rate limit): Kraken GraphQL API Guides documentation
