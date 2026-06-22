import pytest

from migration_utility.workflow import MappingRole, MappingWorkflowState
from migration_utility.workflow.engine import WorkflowEngine


def test_mapping_lead_submits_for_review():
    WorkflowEngine().validate(
        MappingWorkflowState.DRAFT,
        MappingWorkflowState.IN_REVIEW,
        MappingRole.MAPPING_LEAD,
    )


def test_product_owner_cannot_approve_from_draft():
    with pytest.raises(ValueError, match="Cannot transition"):
        WorkflowEngine().validate(
            MappingWorkflowState.DRAFT,
            MappingWorkflowState.APPROVED,
            MappingRole.PRODUCT_OWNER,
        )


def test_business_analyst_approves_from_review():
    WorkflowEngine().validate(
        MappingWorkflowState.IN_REVIEW,
        MappingWorkflowState.APPROVED,
        MappingRole.BUSINESS_ANALYST,
    )


def test_product_owner_signs_off():
    WorkflowEngine().validate(
        MappingWorkflowState.APPROVED,
        MappingWorkflowState.SIGNED_OFF,
        MappingRole.PRODUCT_OWNER,
    )


def test_next_states_for_ba():
    states = WorkflowEngine().next_states(MappingWorkflowState.IN_REVIEW, MappingRole.BUSINESS_ANALYST)
    assert "approved" in states
    assert "draft" in states
