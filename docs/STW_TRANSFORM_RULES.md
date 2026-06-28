# STW transformation rules

Severn Trent Water (STW) → Kraken utility transforms implemented from:

- `property_type_transformation_rule.jpeg`
- `area_code_transformation_rule.jpeg`
- `rateband_transformation_rule.jpeg`

## Backend

| Module | Role |
|--------|------|
| `migration_utility/transforms/stw/` | Rule logic + defaults |
| `migration_utility/rules/engine.py` | Transform types `stw_property_type`, `stw_area_code`, `stw_rateband_lookup` |
| `migration_utility/api/routes/stw_transform_rules.py` | GET/PUT rules, tariff table, preview, reset |

Project overrides live in `project.config`:

- `stw_transform_rules` — partial overrides merged with defaults
- `stw_tariff_table` — rate band lookup rows

## Property type

- Standard map: Terraced / Semi Detached / Detached → Kraken enums
- **Not Known** → `DETACHED` for STW Measured & Assessed only
- **MDD override** for metered (STW Measured, BDS, Watersure) and unmeasured Assessed
- **Flat rule**: address contains flat/apartment/studio → `FLAT` (Unmeasured, BDS, Watersure)

## Area code

- Target zone labels → `ZONE_1` … `ZONE_14` (incl. Chester→ZONE_8, Wrexham→ZONE_10)
- Assessed: ASB/AVB/MDD suffix → zone (MDD wins)
- BDS blank → `ZONE_1`; OWC/STW Measured/Watersure blank → tariff table
- Propagate fresh/waste area code (except OWC)

## Rate band

Category-specific lookup keys on `stw_tariff_table` (product + rate band + year; optional area code / property type / Kraken product for drainage).

## UI

Utility projects: **STW Transforms** tab — edit lookup tables, advanced JSON, preview sample records.

Wire field mappings with transform types above in **Rules & Transforms**.
