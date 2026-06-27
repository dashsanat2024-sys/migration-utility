# Kraken Account/Billing Schema — Severn Trent Water (Real, Sourced)

Pulled directly from Severn Trent's own public Kraken developer portal:
**https://developer.st.kraken.tech/graphql/reference/** (GraphQL, introspectable schema)
and **https://developer.st.kraken.tech/rest/** (REST, OpenAPI-based)

This is not a hypothetical — Severn Trent licenses the Kraken platform and publishes
this exact schema for partners/integrators. It's the clearest evidence available that
the "destination publishes its own schema, source maps onto it" model in the redesign
is how this actually works in production, not a simplification for the mockup.

---

## 1. Core object: `AccountType`

> "The account object can be one of several attached to a Portfolio... Typically a
> person has a single account attached to a portfolio and properties on the same
> account will appear on the same bill."

Selected real fields (there are ~80 on the full object; trimmed to migration-relevant ones):

| Field | Type | Notes |
|---|---|---|
| `id` | `ID!` | |
| `number` | `String` | "A code that uniquely identifies the account." — this is the account number used everywhere downstream |
| `accountType` | `AccountTypeChoices` | enum — see below |
| `status` | `AccountStatus` | enum — see below |
| `brand` | `String` | which brand owns the account (Severn Trent Water vs Hafren Dyfrdwy) |
| `balance` | `Int!` | current balance, minor currency units |
| `overdueBalance` | `Int` | |
| `billingName` | `String` | "very unlikely" to use `address.name`; this is the dedicated billing name field |
| `billingEmail` / `billingAddress` / `billingAddressLine1-5` / `billingAddressPostcode` / `billingCountryCode` | `String` | flattened legacy-style address fields, kept alongside the newer `address(RichAddressType)` |
| `address` | `RichAddressType` | libaddressinput-based structured address |
| `createdAt` | `DateTime` | "the datetime the account was originally created" |
| `commsDeliveryPreference` | `CommsDeliveryPreference` | enum: `EMAIL` / `POSTAL_MAIL` |
| `documentAccessibility` | `DocumentAccessibilityChoices` | enum: `AUDIO` / `BRAILLE` / `LARGE_PRINT` |
| `isMeasured` | `Boolean` | metered vs unmetered billing |
| `isOnSteppedTariff` | `Boolean!` | "whether the account is on a Rising Block Tariff (stepped rates) for both fresh and waste water" — water-specific |
| `hasActiveWatersureAgreement` | `Boolean!` | water-specific social tariff flag |
| `hasActiveSocialAgreement` / `hasActiveHardshipAgreements` | `Boolean!` / `[HardshipAgreementType]` | social tariff / vulnerability support — maps to things like Severn Trent's "Big Difference Scheme" |
| `directDebitInstructions` | connection | DD setup, paginated |
| `paymentMethods` | connection (`PaymentInstructionConnectionTypeConnection`) | |
| `billingOptions` | `BillingOptionsType` | billing cycle info (see below) |
| `properties` | `[PropertyType]` | properties linked to the account |
| `ledgers` | `[LedgerType]` | "similar to a bank account" — financial bookkeeping |
| `urn` | `String` | "Unique reference number from a 3rd party enrolment" — **this is explicitly the field designed for cross-system migration linkage** |

## 2. Account application — explicit migration metadata

`AccountApplicationConnectionTypeConnection` → node fields include, verbatim from the schema:

| Field | Type | Description (verbatim, trimmed) |
|---|---|---|
| `isMigrated` | `Boolean` | "Whether this account application represents a migration into the current system or a regular gain." |
| `migrationSource` | `String` | "The source system for a migrated account. This could be the previous supplier or the previous account management system." |
| `dateOfSale` | `Date` | date the account decided to switch |
| `preferredSsd` | `Date` | preferred supply start date |
| `salesChannel` / `salesSubchannel` | `String` | |

This is a genuinely important finding: **Kraken's own schema has a first-class `migrationSource` field** — confirmation that Kraken is designed from the ground up to receive migrated accounts and track provenance, exactly the workflow this utility automates.

## 3. Billing cycle: `BillingOptionsType`

| Field | Type | Notes |
|---|---|---|
| `isFixed` | `Boolean!` | fixed cycle vs flexible (driven by meter reads) |
| `periodStartDay` | `Int` | day of month billing starts |
| `periodLength` | `AccountBillingOptionsPeriodLength` | enum: `MONTHLY` / `QUARTERLY` |
| `periodLengthMultiplier` | `Int` | |
| `currentBillingPeriodStartDate` / `currentBillingPeriodEndDate` | `Date` | null if flexible |
| `nextBillingDate` | `Date` | |

## 4. Address: `RichAddressType` / legacy `BillingAddressType`

`RichAddressType` (modern, libaddressinput-based) — `countryCode`, `line1`-`line5`, `postcode`.
The legacy flattened fields (`billingAddressLine1`...`billingAddressLine5`, `billingAddressPostcode`, `billingCountryCode`, `billingDeliveryPointIdentifier`) are kept on `AccountType` directly for backward compatibility — this dual representation is itself a useful pattern: **Kraken's own schema models "legacy shape + modern shape coexisting,"** which mirrors exactly what a migration mapping tool has to bridge.

## 5. Water-specific structures (confirms this is the Severn Trent/water instance, not generic energy Kraken)

- `Agreement` → "An agreement for a **water supply point**" — `supplyPoint(SupplyPointNode)`, `productRates`
- `FreshWaterSupplyPointWholesalerCode` enum — real UK water wholesaler codes: `SEVERN_TRENT`, `THAMES`, `ANGLIAN`, `YORKSHIRE`, `UNITED_UTILITIES`, `SOUTH_WEST`, `WESSEX`, `HAFREN_DYFRDWY`, etc.
- `FreshWaterSupplyPointPropertyType` enum — `DETACHED`, `SEMI_DETACHED`, `TERRACED`, `FLAT`, `BULK_SUPPLY`
- `LinkedServiceService` enum — `FRESH`, `WASTE`, `COMBINED_DRAINAGE`, `SURFACE_DRAINAGE`, `RAINWATER_HARVESTING` — UK water service categories, not energy
- `MeterAlertTypeChoices` — `LEAK`, `DEFECT` (water leak detection, not gas/electric meter alerts)
- `WaterMeterStatus`, `WaterMeterCategory`, `WaterMeterCapabilityType` — separate from the generic `MeterStatus`/`MeterCategory` enums, water gets its own variants
- `ConsumptionUnit` enum includes `cubicMetres` alongside `kWh`/`MJ`/`Smc` — multi-utility unit support in one enum

## 6. Key enums relevant to a migration mapping/validation layer

| Enum | Values (sample) | Use in mapping |
|---|---|---|
| `AccountStatus` | `PENDING`, `ACTIVE`, `INCOMPLETE`, `DORMANT`, `ENROLMENT_ERROR`, `ENROLMENT_REJECTED`, `VOID`, `WITHDRAWN` | target value for a migrated account's lifecycle state |
| `AccountTypeChoices` | `DOMESTIC`, `BUSINESS`, `OCCUPIER`, `VACANT`, `MANAGED`, `PORTFOLIO_LEAD`, + third-party-billed variants | classify legacy account records into Kraken's account taxonomy |
| `BrandChoices` | `SEVERN_TRENT_WATER`, `HAFREN_DYFRDWY` | which brand a migrated account belongs to |
| `DirectDebitInstructionStatus` / `PaymentInstructionStatus` | `ACTIVE`, `PROVISIONAL`, `FAILED` | legacy DD mandates land as `PROVISIONAL` until re-confirmed — a real transform/validation rule a migration would need |
| `AccountPaymentStatusOptions` | includes `HISTORIC` — *"Payments made in a previous system and then imported into Kraken"* and `THIRD_PARTY` — *"recorded for financial purposes in a different system but should be added to statements"* | **Kraken's schema has explicit status values reserved for migrated/imported data**, distinct from live transactional states |
| `AccountRepaymentStatusOptions` | also has `HISTORIC` for the same reason | same pattern on the repayments side |
| `ConsentEventSource` | `MIGRATION`, `DATA_IMPORT`, `ONBOARDING`, `CONSUMER_SITE`, `API_SITE`, `THIRD_PARTY_VENDOR`, `SUPPORT_SITE`, `COMMAND_JOB` | **`MIGRATION` and `DATA_IMPORT` are first-class consent-provenance values** — every consent record carries where it came from, which matters a lot for GDPR-sensitive utility customer data |

## 7. What this confirms for the Migration Utility design

1. **The "destination publishes a schema, source maps onto it" model is exactly right** — this is a real, large (700-field+), versioned, introspectable GraphQL schema that Severn Trent's own integration partners build against. Nobody negotiates the shape of `AccountType`; they map their legacy fields onto it.
2. **Migration provenance is a first-class concept in Kraken**, not bolted on: `migrationSource`, `isMigrated`, `HISTORIC` payment/repayment statuses, and `MIGRATION`/`DATA_IMPORT` consent sources all exist specifically so that migrated data is distinguishable from live Kraken-native data after the fact. A well-designed mapping/transform layer should let users set these provenance fields explicitly (e.g. a `migration_source` constant transform, a default of `HISTORIC` for back-dated payment records) rather than just discarding them.
3. **Legacy/modern field duality is built into Kraken itself** (flattened `billingAddressLine1..5` vs structured `address.line1..5`) — a sign that real migrations often need to populate *both* shapes during transition, which the transform engine's existing `concat`/`copy` types already support.
4. **Required vs optional is genuinely nuanced in a real schema** — `number`, `id` are effectively required; many others (`billingEmail`, `urn`, `documentAccessibility`) are nullable/optional but still meaningful to map if available. The schema contract panel's "required (amber) / optional (dashed grey)" distinction in the prototype should be driven by GraphQL's own `!`/nullable markers, which the plugin can read directly from introspection rather than needing separate manual annotation.

## 8. Sources

- GraphQL reference (objects): https://developer.st.kraken.tech/graphql/reference/objects
- GraphQL reference (enums): https://developer.st.kraken.tech/graphql/reference/enums
- REST reference index: https://developer.st.kraken.tech/rest/
- Kraken/Severn Trent partnership background: Kraken Technologies Wikipedia entry; Kraken Technologies Annual Report FY24/25
