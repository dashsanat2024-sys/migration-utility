from __future__ import annotations

from migration_utility.plugins.base import DestinationPlugin
from migration_utility.plugins.schema import DestinationSchema, SchemaField

# Sourced from Severn Trent Kraken developer portal (GraphQL introspection):
# https://developer.st.kraken.tech/graphql/reference/
# See kraken-schema-reference.md in repo root.

_ACCOUNT_STATUS = [
    "PENDING",
    "ACTIVE",
    "INCOMPLETE",
    "DORMANT",
    "ENROLMENT_ERROR",
    "ENROLMENT_REJECTED",
    "VOID",
    "WITHDRAWN",
]
_ACCOUNT_TYPE = [
    "DOMESTIC",
    "BUSINESS",
    "OCCUPIER",
    "VACANT",
    "MANAGED",
    "PORTFOLIO_LEAD",
]
_BRAND = ["SEVERN_TRENT_WATER", "HAFREN_DYFRDWY"]
_COMMS_PREF = ["EMAIL", "POSTAL_MAIL"]
_DOC_ACCESS = ["AUDIO", "BRAILLE", "LARGE_PRINT"]
_BILLING_PERIOD = ["MONTHLY", "QUARTERLY"]


def _enum(name: str, values: list[str]) -> dict:
    return {"enum": values, "enum_name": name}


def _group(name: str, **extra) -> dict:
    return {"group": name, **extra}


_KRAKEN_ACCOUNT_FIELDS: list[SchemaField] = [
    # --- AccountType core (GraphQL AccountType) ---
    SchemaField(
        name="number",
        data_type="string",
        required=True,
        description="Code that uniquely identifies the account (Kraken account number)",
        constraints=_group("core"),
    ),
    SchemaField(
        name="accountType",
        data_type="enum",
        required=True,
        description="Account taxonomy — DOMESTIC, BUSINESS, OCCUPIER, VACANT, etc.",
        constraints={**_group("core"), **_enum("AccountTypeChoices", _ACCOUNT_TYPE)},
    ),
    SchemaField(
        name="status",
        data_type="enum",
        required=True,
        description="Account lifecycle state after migration",
        constraints={**_group("core"), **_enum("AccountStatus", _ACCOUNT_STATUS)},
    ),
    SchemaField(
        name="brand",
        data_type="enum",
        description="Brand owning the account (Severn Trent Water vs Hafren Dyfrdwy)",
        constraints={**_group("core"), **_enum("BrandChoices", _BRAND)},
    ),
    SchemaField(
        name="balance",
        data_type="int",
        required=True,
        description="Current balance in minor currency units (GraphQL Int!)",
        constraints=_group("core"),
    ),
    SchemaField(
        name="overdueBalance",
        data_type="int",
        description="Overdue balance in minor currency units",
        constraints=_group("core"),
    ),
    SchemaField(
        name="billingName",
        data_type="string",
        description="Dedicated billing name (distinct from address.name)",
        constraints=_group("core"),
    ),
    SchemaField(
        name="billingEmail",
        data_type="string",
        description="Billing contact email",
        constraints=_group("core"),
    ),
    SchemaField(
        name="createdAt",
        data_type="datetime",
        description="Datetime the account was originally created",
        constraints=_group("core"),
    ),
    SchemaField(
        name="urn",
        data_type="string",
        description="Unique reference from 3rd-party enrolment — cross-system migration linkage",
        constraints={**_group("core"), "migration_provenance": True},
    ),
    SchemaField(
        name="isMeasured",
        data_type="bool",
        description="Metered vs unmetered billing",
        constraints=_group("core"),
    ),
    SchemaField(
        name="commsDeliveryPreference",
        data_type="enum",
        description="Preferred communications channel",
        constraints={**_group("core"), **_enum("CommsDeliveryPreference", _COMMS_PREF)},
    ),
    SchemaField(
        name="documentAccessibility",
        data_type="enum",
        description="Accessible document format preference",
        constraints={**_group("core"), **_enum("DocumentAccessibilityChoices", _DOC_ACCESS)},
    ),
    # --- Water-specific flags (GraphQL Boolean!) ---
    SchemaField(
        name="isOnSteppedTariff",
        data_type="bool",
        required=True,
        description="Rising Block Tariff (stepped rates) for fresh and waste water",
        constraints=_group("water"),
    ),
    SchemaField(
        name="hasActiveWatersureAgreement",
        data_type="bool",
        required=True,
        description="Active Watersure social tariff agreement",
        constraints=_group("water"),
    ),
    SchemaField(
        name="hasActiveSocialAgreement",
        data_type="bool",
        required=True,
        description="Active social tariff / vulnerability support agreement",
        constraints=_group("water"),
    ),
    SchemaField(
        name="hasActiveHardshipAgreements",
        data_type="array",
        description="Active hardship agreements (e.g. Big Difference Scheme)",
        constraints=_group("water"),
    ),
    # --- Legacy flattened billing address (kept alongside structured address) ---
    SchemaField(
        name="billingAddressLine1",
        data_type="string",
        description="Legacy billing address line 1",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingAddressLine2",
        data_type="string",
        description="Legacy billing address line 2",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingAddressLine3",
        data_type="string",
        description="Legacy billing address line 3",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingAddressLine4",
        data_type="string",
        description="Legacy billing address line 4",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingAddressLine5",
        data_type="string",
        description="Legacy billing address line 5",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingAddressPostcode",
        data_type="string",
        description="Legacy billing postcode",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    SchemaField(
        name="billingCountryCode",
        data_type="string",
        description="Legacy billing country code",
        constraints={**_group("billing_address"), "legacy_shape": True},
    ),
    # --- Structured RichAddressType (modern shape — populate both during transition) ---
    SchemaField(
        name="address.line1",
        data_type="string",
        description="Structured address line 1 (RichAddressType / libaddressinput)",
        constraints={**_group("structured_address"), "graphql_path": "address.line1"},
    ),
    SchemaField(
        name="address.line2",
        data_type="string",
        description="Structured address line 2",
        constraints={**_group("structured_address"), "graphql_path": "address.line2"},
    ),
    SchemaField(
        name="address.postcode",
        data_type="string",
        description="Structured address postcode",
        constraints={**_group("structured_address"), "graphql_path": "address.postcode"},
    ),
    SchemaField(
        name="address.countryCode",
        data_type="string",
        description="Structured address country code",
        constraints={**_group("structured_address"), "graphql_path": "address.countryCode"},
    ),
    # --- Account application — migration provenance (first-class in Kraken) ---
    SchemaField(
        name="isMigrated",
        data_type="bool",
        description="Whether this account application is a migration gain vs regular gain",
        constraints={**_group("migration"), "migration_provenance": True},
    ),
    SchemaField(
        name="migrationSource",
        data_type="string",
        description="Source system for migrated account (previous supplier or account management system)",
        constraints={**_group("migration"), "migration_provenance": True},
    ),
    SchemaField(
        name="dateOfSale",
        data_type="date",
        description="Date the account decided to switch supplier",
        constraints=_group("migration"),
    ),
    SchemaField(
        name="preferredSsd",
        data_type="date",
        description="Preferred supply start date",
        constraints=_group("migration"),
    ),
    SchemaField(
        name="salesChannel",
        data_type="string",
        description="Sales channel for the account application",
        constraints=_group("migration"),
    ),
    SchemaField(
        name="salesSubchannel",
        data_type="string",
        description="Sales sub-channel for the account application",
        constraints=_group("migration"),
    ),
    # --- BillingOptionsType ---
    SchemaField(
        name="billingOptions.isFixed",
        data_type="bool",
        required=True,
        description="Fixed billing cycle vs flexible (meter-read driven)",
        constraints={**_group("billing_options"), "graphql_path": "billingOptions.isFixed"},
    ),
    SchemaField(
        name="billingOptions.periodStartDay",
        data_type="int",
        description="Day of month billing period starts",
        constraints={**_group("billing_options"), "graphql_path": "billingOptions.periodStartDay"},
    ),
    SchemaField(
        name="billingOptions.periodLength",
        data_type="enum",
        description="Billing period length",
        constraints={
            **_group("billing_options"),
            **_enum("AccountBillingOptionsPeriodLength", _BILLING_PERIOD),
            "graphql_path": "billingOptions.periodLength",
        },
    ),
    SchemaField(
        name="billingOptions.nextBillingDate",
        data_type="date",
        description="Next scheduled billing date",
        constraints={**_group("billing_options"), "graphql_path": "billingOptions.nextBillingDate"},
    ),
    # --- Payment / consent provenance (enum values for migrated data) ---
    SchemaField(
        name="paymentStatus",
        data_type="enum",
        description="Account payment status — use HISTORIC for payments imported from legacy system",
        constraints={
            **_group("provenance"),
            **_enum(
                "AccountPaymentStatusOptions",
                ["ACTIVE", "HISTORIC", "THIRD_PARTY", "CANCELLED"],
            ),
            "migration_provenance": True,
        },
    ),
    SchemaField(
        name="repaymentStatus",
        data_type="enum",
        description="Repayment status — HISTORIC reserved for legacy-imported repayments",
        constraints={
            **_group("provenance"),
            **_enum(
                "AccountRepaymentStatusOptions",
                ["ACTIVE", "HISTORIC", "CANCELLED"],
            ),
            "migration_provenance": True,
        },
    ),
    SchemaField(
        name="consentEventSource",
        data_type="enum",
        description="Consent record provenance — MIGRATION or DATA_IMPORT for GDPR audit trail",
        constraints={
            **_group("provenance"),
            **_enum(
                "ConsentEventSource",
                [
                    "MIGRATION",
                    "DATA_IMPORT",
                    "ONBOARDING",
                    "CONSUMER_SITE",
                    "API_SITE",
                    "THIRD_PARTY_VENDOR",
                    "SUPPORT_SITE",
                    "COMMAND_JOB",
                ],
            ),
            "migration_provenance": True,
        },
    ),
]


class KrakenBillingPlugin(DestinationPlugin):
    id = "kraken-billing-v3"
    label = "Kraken Account — Severn Trent Water"
    version = "4.0.0"
    adapter_key = "kraken"
    transport = "GraphQL · REST"

    def get_schema(self, entity: str = "account") -> DestinationSchema | None:
        if entity == "account":
            return DestinationSchema(
                entity="account",
                description=(
                    "Kraken GraphQL AccountType contract (Severn Trent Water). "
                    "Sourced from developer.st.kraken.tech — ~80 fields trimmed to "
                    "migration-relevant sockets including migration provenance."
                ),
                fields=_KRAKEN_ACCOUNT_FIELDS,
            )
        if entity == "tariff":
            return DestinationSchema(
                entity="tariff",
                description="Kraken product / agreement rates (water supply point)",
                fields=[
                    SchemaField(
                        name="productCode",
                        data_type="string",
                        required=True,
                        description="Destination product / tariff code",
                        constraints={"enum_ref": "tariff_mapping"},
                    ),
                    SchemaField(name="displayName", data_type="string", description="Product display name"),
                    SchemaField(
                        name="freshWaterWholesaler",
                        data_type="enum",
                        description="UK water wholesaler code",
                        constraints={
                            "enum": [
                                "SEVERN_TRENT",
                                "THAMES",
                                "ANGLIAN",
                                "YORKSHIRE",
                                "UNITED_UTILITIES",
                                "SOUTH_WEST",
                                "WESSEX",
                                "HAFREN_DYFRDWY",
                            ],
                            "enum_name": "FreshWaterSupplyPointWholesalerCode",
                        },
                    ),
                ],
            )
        return None
