"""Account health check definitions — static data + transient operational blockers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

# Source field aliases (legacy Target/CMP → normalized keys)
ACCOUNT_ID_KEYS = ("number", "accountId", "account_id", "CUST_ACCOUNT_NO", "external_id")
BUSINESS_KEYS = ("businessId", "business_id", "BUSINESS_REF")
BALANCE_KEYS = ("balance", "BALANCE", "currentBalance")
OVERDUE_KEYS = ("overdueBalance", "overdue_balance", "OVERDUE_BAL")
PENDING_PAYMENT_KEYS = ("pendingPayment", "pending_payment", "PENDING_PAYMENT", "hasPendingPayment")
BILL_DUE_KEYS = ("billDue", "bill_due", "BILL_DUE", "unpaidBill", "hasUnpaidBill")
METER_APPT_KEYS = ("meterAppointment", "meter_appointment", "METER_APPT", "scheduledMeterVisit")
ACTIVE_JOURNEY_KEYS = ("activeJourney", "active_journey", "contractJourneyActive", "ACTIVE_JOURNEY")
PROVIDER_SWITCH_KEYS = ("providerSwitch", "provider_switch", "ongoingProviderSwitch", "SUPPLIER_SWITCH")
LEAVE_SUPPLIER_KEYS = ("leaveSupplier", "leave_supplier", "leaveSupplierInProgress")
CONTRACT_STATUS_KEYS = ("contractStatus", "contract_status", "CONTRACT_STATUS")
ACCOUNT_TYPE_KEYS = ("accountType", "account_type", "CUST_TYPE_FLAG")
TARIFF_KEYS = ("tariffCode", "tariff_code", "productCode", "TARIFF_CODE")


def _first(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return None


def _truthy(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("Y", "YES", "TRUE", "1", "T", "ACTIVE", "PENDING", "OPEN")


@dataclass(frozen=True)
class HealthCheck:
    id: str
    label: str
    kind: str  # static | operational | mapping
    severity: str  # blocker | warning | info
    weight: int  # points deducted from readiness score
    evaluate: Callable[[dict[str, Any], dict[str, Any]], str | None]
    """Return error message if check fails, else None."""


def _check_missing_account(record: dict, ctx: dict) -> str | None:
    if not _first(record, ACCOUNT_ID_KEYS):
        return "Missing account number / identifier required for Kraken import"
    return None


def _check_missing_required_fields(record: dict, ctx: dict) -> str | None:
    required = ctx.get("required_fields") or ["number", "accountType", "status", "balance"]
    missing = []
    for field in required:
        if field in ("number",):
            if not _first(record, ACCOUNT_ID_KEYS):
                missing.append(field)
        elif not record.get(field) and record.get(field) != 0:
            missing.append(field)
    if missing:
        return f"Missing Kraken required fields: {', '.join(missing)}"
    return None


def _check_duplicate_account(record: dict, ctx: dict) -> str | None:
    acct = _first(record, ACCOUNT_ID_KEYS)
    if not acct:
        return None
    seen: set[str] = ctx.setdefault("_seen_accounts", set())
    key = str(acct)
    if key in seen:
        return f"Duplicate account number {key} in cohort"
    seen.add(key)
    return None


def _check_pending_payment(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, PENDING_PAYMENT_KEYS)):
        return "Pending payment — account excluded until cleared"
    return None


def _check_bill_due(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, BILL_DUE_KEYS)):
        return "Unpaid bill due — resolve before migration"
    return None


def _check_meter_appointment(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, METER_APPT_KEYS)):
        return "Scheduled meter appointment — defer migration until complete"
    return None


def _check_active_journey(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, ACTIVE_JOURNEY_KEYS)):
        return "Active contract journey in progress"
    return None


def _check_provider_switch(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, PROVIDER_SWITCH_KEYS)):
        return "Ongoing provider switch blocks migration"
    return None


def _check_leave_supplier(record: dict, ctx: dict) -> str | None:
    if _truthy(_first(record, LEAVE_SUPPLIER_KEYS)):
        return "Leave-supplier process in progress"
    return None


def _check_contract_expired(record: dict, ctx: dict) -> str | None:
    status = str(_first(record, CONTRACT_STATUS_KEYS) or "").upper()
    if status in ("EXPIRED", "EXP"):
        return "Contract expired — review before import"
    return None


def _check_contract_terminated(record: dict, ctx: dict) -> str | None:
    status = str(_first(record, CONTRACT_STATUS_KEYS) or "").upper()
    if status in ("TERMINATED", "TERM", "REVOKED"):
        return "Contract terminated/revoked"
    return None


def _check_overdue_balance(record: dict, ctx: dict) -> str | None:
    overdue = _first(record, OVERDUE_KEYS)
    if overdue is not None:
        try:
            if int(overdue) > 0:
                return f"Overdue balance {overdue} — billing remediation required"
        except (TypeError, ValueError):
            pass
    return None


def _check_invalid_account_type(record: dict, ctx: dict) -> str | None:
    allowed = ctx.get("allowed_account_types") or {
        "DOMESTIC", "BUSINESS", "OCCUPIER", "VACANT", "MANAGED", "PORTFOLIO_LEAD",
        "D", "B", "DOM", "BUS",
    }
    raw = _first(record, ACCOUNT_TYPE_KEYS)
    if raw is None:
        return None
    normalized = str(raw).upper()
    mapping = {"D": "DOMESTIC", "B": "BUSINESS", "DOM": "DOMESTIC", "BUS": "BUSINESS"}
    normalized = mapping.get(normalized, normalized)
    if normalized not in allowed and raw not in allowed:
        return f"Invalid accountType {raw!r}"
    return None


def _check_missing_business_for_business_acct(record: dict, ctx: dict) -> str | None:
    acct_type = str(_first(record, ACCOUNT_TYPE_KEYS) or "").upper()
    if acct_type in ("BUSINESS", "B", "BUS") and not _first(record, BUSINESS_KEYS):
        return "Business account missing business reference (KT-CT-10021 risk)"
    return None


DEFAULT_HEALTH_CHECKS: list[HealthCheck] = [
    HealthCheck("missing_account_number", "Account number present", "static", "blocker", 40, _check_missing_account),
    HealthCheck("missing_required_kraken_field", "Kraken required fields", "mapping", "blocker", 30, _check_missing_required_fields),
    HealthCheck("duplicate_account_number", "Unique account number", "static", "blocker", 35, _check_duplicate_account),
    HealthCheck("invalid_account_type", "Valid account type enum", "mapping", "blocker", 25, _check_invalid_account_type),
    HealthCheck("missing_business_ref", "Business ref for business accounts", "static", "blocker", 25, _check_missing_business_for_business_acct),
    HealthCheck("pending_payment", "No pending payments", "operational", "blocker", 20, _check_pending_payment),
    HealthCheck("bill_due_unpaid", "No unpaid bills due", "operational", "blocker", 20, _check_bill_due),
    HealthCheck("meter_appointment_pending", "No pending meter appointments", "operational", "blocker", 15, _check_meter_appointment),
    HealthCheck("active_contract_journey", "No active contract journey", "operational", "blocker", 20, _check_active_journey),
    HealthCheck("ongoing_provider_switch", "No ongoing provider switch", "operational", "blocker", 20, _check_provider_switch),
    HealthCheck("leave_supplier_in_progress", "No leave-supplier in progress", "operational", "blocker", 20, _check_leave_supplier),
    HealthCheck("contract_expired", "Contract not expired", "operational", "warning", 10, _check_contract_expired),
    HealthCheck("contract_terminated", "Contract not terminated", "operational", "warning", 10, _check_contract_terminated),
    HealthCheck("overdue_balance_blocker", "No overdue balance", "operational", "blocker", 15, _check_overdue_balance),
]

CHECKS_BY_ID: dict[str, HealthCheck] = {c.id: c for c in DEFAULT_HEALTH_CHECKS}
