"""Mapping approval workflow — Phase 4."""

from enum import StrEnum


class MappingWorkflowState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SIGNED_OFF = "signed_off"


class MappingRole(StrEnum):
    MAPPING_LEAD = "mapping_lead"
    BUSINESS_ANALYST = "business_analyst"
    PRODUCT_OWNER = "product_owner"


class MappingEntityType(StrEnum):
    RULE_SET = "rule_set"
    TARIFF_SET = "tariff_set"
