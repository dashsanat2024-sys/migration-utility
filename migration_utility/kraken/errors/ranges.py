"""Kraken error code ranges from developer.pwl.kraken.tech index (~920 codes total)."""

from __future__ import annotations

from typing import TypedDict


class CodeRange(TypedDict):
    prefix: str  # KT-CT or KT-GB
    start: int
    end: int
    category: str
    label: str
    migration_relevance: str  # high | medium | low | none
    default_phase: str
    default_owner: str


def _ct(
    start: int,
    end: int,
    category: str,
    label: str,
    *,
    relevance: str = "medium",
    phase: str = "at_load",
    owner: str = "migration_engineer",
) -> CodeRange:
    return {
        "prefix": "KT-CT",
        "start": start,
        "end": end,
        "category": category,
        "label": label,
        "migration_relevance": relevance,
        "default_phase": phase,
        "default_owner": owner,
    }


def _gb(
    start: int,
    end: int,
    category: str,
    label: str,
    *,
    relevance: str = "high",
    phase: str = "pre_migration",
    owner: str = "mapping_lead",
) -> CodeRange:
    return {
        "prefix": "KT-GB",
        "start": start,
        "end": end,
        "category": category,
        "label": label,
        "migration_relevance": relevance,
        "default_phase": phase,
        "default_owner": owner,
    }


# Core KT-CT ranges (shared across all Kraken instances)
KT_CT_RANGES: list[CodeRange] = [
    _ct(10001, 10044, "contracts_agreements", "Contracts & agreements", relevance="high", phase="pre_migration"),
    _ct(10201, 10205, "auto_topup_prepay", "Auto top-up / prepay", relevance="none", phase="at_load"),
    _ct(10301, 10358, "leave_supplier_switching", "Leave-supplier / switching", relevance="high", phase="operational", owner="billing_ops"),
    _ct(10703, 10703, "misc", "Miscellaneous", relevance="low"),
    _ct(10801, 10821, "misc", "Miscellaneous", relevance="low"),
    _ct(10901, 10991, "account_business_migration", "Account / business / migration applications", relevance="high", phase="pre_migration"),
    _ct(11100, 11112, "authorization", "Authorization / business linkage", relevance="medium", phase="at_load"),
    _ct(1111, 1163, "authorization", "Authorization (legacy numeric)", relevance="medium", phase="at_load"),
    _ct(11201, 11218, "account_application", "Account application detail", relevance="high", phase="pre_migration"),
    _ct(11301, 11333, "contracts_agreements", "Contract notes / journeys", relevance="medium"),
    _ct(11401, 11404, "enrollment", "Enrollment", relevance="medium"),
    _ct(1140, 1199, "enrollment", "Enrollment & rate limits", relevance="medium", owner="migration_engineer"),
    _ct(12001, 12106, "pricing_quoting", "Pricing / quoting", relevance="medium", phase="pre_migration"),
    _ct(12201, 12301, "misc", "Miscellaneous", relevance="low"),
    _ct(12401, 12612, "telco", "Telco-specific", relevance="none"),
    _ct(12701, 12905, "misc", "Miscellaneous", relevance="low"),
    _ct(13001, 13104, "billing_charges", "Billing / charges", relevance="high", phase="pre_migration", owner="billing_ops"),
    _ct(13201, 13808, "misc", "Miscellaneous", relevance="low"),
    _ct(1401, 1409, "auth_session", "Auth / session", relevance="low", phase="at_load"),
    _ct(14101, 14802, "misc", "Miscellaneous", relevance="low"),
    _ct(1501, 1701, "auth_session", "Session / token", relevance="low", phase="at_load"),
    _ct(3810, 3997, "meters_devices", "Meters & devices", relevance="high", phase="pre_migration", owner="metering"),
    _ct(4010, 4413, "misc", "Miscellaneous", relevance="medium"),
    _ct(4501, 4930, "misc", "Miscellaneous", relevance="medium"),
    _ct(5211, 5821, "tariffs_pricing", "Tariffs / pricing", relevance="high", phase="pre_migration", owner="mapping_lead"),
    _ct(6323, 6732, "misc", "Miscellaneous", relevance="medium"),
    _ct(7010, 7731, "misc", "Miscellaneous", relevance="medium"),
    _ct(7810, 8011, "misc", "Miscellaneous", relevance="medium"),
    _ct(8101, 8956, "account_business_migration", "Account / business linkage detail", relevance="high"),
    _ct(9010, 9911, "misc", "Miscellaneous", relevance="medium"),
]

# UK market KT-GB ranges (Severn Trent / UK water)
KT_GB_RANGES: list[CodeRange] = [
    _gb(10101, 10103, "uk_market", "UK market rules"),
    _gb(10206, 10208, "uk_market", "UK prepay rules"),
    _gb(10501, 10504, "uk_market", "UK market rules"),
    _gb(10601, 10609, "uk_market", "UK market rules"),
    _gb(10701, 10701, "uk_market", "UK market rules"),
    _gb(11001, 11019, "uk_market", "UK market rules"),
    _gb(1120, 1121, "uk_market", "UK market rules"),
    _gb(12401, 12402, "uk_market", "UK market rules"),
    _gb(12801, 12803, "uk_market", "UK market rules"),
    _gb(1301, 1301, "uk_market", "UK market rules"),
    _gb(13901, 13903, "uk_market", "UK market rules"),
    _gb(14001, 14002, "uk_market", "UK market rules"),
    _gb(1501, 1502, "uk_market", "UK market rules"),
    _gb(3810, 3812, "uk_meters", "UK meter rules", owner="metering"),
    _gb(3910, 3931, "uk_meters", "UK meter rules", owner="metering"),
    _gb(4011, 4058, "uk_market", "UK market validation"),
    _gb(4101, 4144, "uk_market", "UK market validation"),
    _gb(4210, 4245, "uk_market", "UK market validation"),
    _gb(4301, 4305, "uk_market", "UK market validation"),
    _gb(4513, 4513, "uk_market", "UK market validation"),
    _gb(4610, 4629, "uk_market", "UK market validation"),
    _gb(5110, 5117, "uk_tariffs", "UK tariff rules", owner="mapping_lead"),
    _gb(5411, 5419, "uk_tariffs", "UK tariff rules", owner="mapping_lead"),
    _gb(5601, 5611, "uk_market", "UK market validation"),
    _gb(6111, 6219, "uk_billing", "UK billing rules", owner="billing_ops"),
    _gb(6312, 6314, "uk_billing", "UK billing rules", owner="billing_ops"),
    _gb(6411, 6640, "uk_market", "UK market validation"),
    _gb(6811, 6814, "uk_market", "UK market validation"),
    _gb(7601, 7601, "uk_market", "UK market validation"),
    _gb(8801, 8801, "uk_market", "UK market validation"),
    _gb(9310, 9327, "uk_market", "UK market validation"),
    _gb(9510, 9521, "uk_market", "UK market validation"),
    _gb(9710, 9711, "uk_market", "UK market validation"),
]

ALL_RANGES: list[CodeRange] = KT_CT_RANGES + KT_GB_RANGES

CATEGORY_LABELS: dict[str, str] = {
    "contracts_agreements": "Contracts & agreements",
    "account_business_migration": "Account / business / migration",
    "leave_supplier_switching": "Leave-supplier / switching",
    "meters_devices": "Meters & devices",
    "billing_charges": "Billing & charges",
    "tariffs_pricing": "Tariffs & pricing",
    "pricing_quoting": "Pricing & quoting",
    "enrollment": "Enrollment",
    "account_application": "Account application",
    "authorization": "Authorization",
    "auth_session": "Auth / session",
    "auto_topup_prepay": "Auto top-up / prepay",
    "uk_market": "UK market (KT-GB)",
    "uk_meters": "UK meters (KT-GB)",
    "uk_tariffs": "UK tariffs (KT-GB)",
    "uk_billing": "UK billing (KT-GB)",
    "telco": "Telco (not relevant)",
    "misc": "Miscellaneous",
}
