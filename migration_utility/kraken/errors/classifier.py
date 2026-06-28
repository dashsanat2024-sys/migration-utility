"""Map validation findings and Kraken API responses to root-cause taxonomy."""

from __future__ import annotations

import re
from typing import Any

from migration_utility.kraken.errors.catalog import get_kraken_error_catalog

_CODE_RE = re.compile(r"KT-(CT|GB)-(\d+)", re.I)

# Check ID → predicted Kraken codes (pre-migration)
CHECK_TO_KRAKEN: dict[str, list[str]] = {
    "missing_account_number": ["KT-CT-10005", "KT-CT-10006"],
    "missing_business_ref": ["KT-CT-10021"],
    "missing_required_kraken_field": ["KT-CT-10039"],
    "invalid_contract_term": ["KT-CT-10009", "KT-CT-10010"],
    "duplicate_party_contract": ["KT-CT-10001", "KT-CT-10042"],
    "contract_party_invalid": ["KT-CT-10020", "KT-CT-10031"],
    "contract_not_started": ["KT-CT-10025"],
    "contract_expired": ["KT-CT-10024"],
    "contract_terminated": ["KT-CT-10022"],
    "active_contract_journey": ["KT-CT-10008", "KT-CT-10035"],
    "ongoing_provider_switch": ["KT-CT-10027", "KT-CT-10301"],
    "leave_supplier_in_progress": ["KT-CT-10305", "KT-CT-10310", "KT-CT-10311"],
    "pending_payment": ["KT-CT-13001"],  # billing range — indexed
    "bill_due_unpaid": ["KT-CT-13001"],
    "meter_appointment_pending": ["KT-CT-3810"],  # meters range — indexed
    "invalid_meter_device": ["KT-CT-10202", "KT-CT-3810"],
    "invalid_account_type": ["KT-CT-10901"],
    "invalid_tariff_mapping": ["KT-CT-5211", "KT-GB-5110"],
    "uk_market_validation": ["KT-GB-4011"],
    "duplicate_account_number": ["KT-CT-10001"],
    "negative_balance_anomaly": ["KT-CT-13001"],
    "overdue_balance_blocker": ["KT-CT-13001"],
}

ROOT_CAUSE_BY_CHECK: dict[str, str] = {
    "missing_account_number": "data_quality",
    "missing_business_ref": "data_quality",
    "missing_required_kraken_field": "mapping",
    "invalid_contract_term": "mapping",
    "duplicate_party_contract": "data_quality",
    "contract_party_invalid": "mapping",
    "contract_not_started": "operational_blocker",
    "contract_expired": "operational_blocker",
    "contract_terminated": "operational_blocker",
    "active_contract_journey": "operational_blocker",
    "ongoing_provider_switch": "operational_blocker",
    "leave_supplier_in_progress": "operational_blocker",
    "pending_payment": "operational_blocker",
    "bill_due_unpaid": "operational_blocker",
    "meter_appointment_pending": "operational_blocker",
    "invalid_meter_device": "data_quality",
    "invalid_account_type": "mapping",
    "invalid_tariff_mapping": "mapping",
    "uk_market_validation": "kraken_validation",
    "duplicate_account_number": "data_quality",
    "negative_balance_anomaly": "data_quality",
    "overdue_balance_blocker": "operational_blocker",
}

OWNER_BY_CHECK: dict[str, str] = {
    "pending_payment": "billing_ops",
    "bill_due_unpaid": "billing_ops",
    "meter_appointment_pending": "metering",
    "invalid_meter_device": "metering",
    "active_contract_journey": "billing_ops",
    "ongoing_provider_switch": "billing_ops",
    "leave_supplier_in_progress": "billing_ops",
    "invalid_tariff_mapping": "mapping_lead",
    "missing_required_kraken_field": "mapping_lead",
    "invalid_contract_term": "mapping_lead",
}


def classify_validation_finding(check_id: str, message: str = "") -> dict[str, Any]:
    catalog = get_kraken_error_catalog()
    codes = CHECK_TO_KRAKEN.get(check_id, [])
    primary = catalog.get(codes[0]) if codes else None
    return {
        "check_id": check_id,
        "root_cause_category": ROOT_CAUSE_BY_CHECK.get(check_id, "data_quality"),
        "owner_role": OWNER_BY_CHECK.get(check_id, primary.get("owner_role") if primary else "data_team"),
        "kraken_error_codes": codes,
        "primary_kraken_code": codes[0] if codes else None,
        "kraken_error_type": primary.get("error_type") if primary else None,
        "remediation_hint": message or (primary.get("trigger") if primary else ""),
        "is_blocker": primary.get("is_blocker", True) if primary else True,
    }


def classify_kraken_response(payload: dict[str, Any] | str) -> dict[str, Any]:
    """Classify a Kraken API error payload or message string."""
    catalog = get_kraken_error_catalog()
    text = payload if isinstance(payload, str) else (
        payload.get("message")
        or payload.get("error")
        or payload.get("detail")
        or str(payload.get("code", ""))
    )
    entry = catalog.lookup_by_message(str(text))
    if not entry:
        match = _CODE_RE.search(str(text))
        if match:
            entry = catalog.get(f"KT-{match.group(1).upper()}-{match.group(2)}")
    if not entry:
        return {
            "root_cause_category": "kraken_application",
            "owner_role": "migration_engineer",
            "kraken_error_codes": [],
            "primary_kraken_code": None,
            "remediation_hint": str(text)[:500],
            "is_blocker": True,
        }

    error_type = entry.get("error_type", "UNKNOWN")
    if error_type == "VALIDATION":
        root = "kraken_validation"
    elif error_type == "NOT_FOUND":
        root = "data_quality"
    elif error_type == "APPLICATION":
        root = "kraken_application"
    elif error_type == "SERVICE_AVAILABILITY":
        root = "environment"
    else:
        root = "kraken_application"

    return {
        "root_cause_category": root,
        "owner_role": entry.get("owner_role", "migration_engineer"),
        "kraken_error_codes": [entry["code"]],
        "primary_kraken_code": entry["code"],
        "kraken_error_type": error_type,
        "kraken_message": entry.get("message"),
        "remediation_hint": entry.get("trigger") or entry.get("message"),
        "is_blocker": entry.get("is_blocker", True),
        "migration_phase": entry.get("migration_phase"),
    }
