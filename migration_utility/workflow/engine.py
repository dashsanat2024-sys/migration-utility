from __future__ import annotations

from migration_utility.workflow import MappingRole, MappingWorkflowState


class WorkflowEngine:
    """Role-gated mapping agreement workflow."""

    _TRANSITIONS: dict[MappingWorkflowState, dict[MappingWorkflowState, set[MappingRole]]] = {
        MappingWorkflowState.DRAFT: {
            MappingWorkflowState.IN_REVIEW: {MappingRole.MAPPING_LEAD, MappingRole.BUSINESS_ANALYST},
        },
        MappingWorkflowState.IN_REVIEW: {
            MappingWorkflowState.DRAFT: {MappingRole.MAPPING_LEAD, MappingRole.BUSINESS_ANALYST},
            MappingWorkflowState.APPROVED: {MappingRole.BUSINESS_ANALYST, MappingRole.PRODUCT_OWNER},
        },
        MappingWorkflowState.APPROVED: {
            MappingWorkflowState.SIGNED_OFF: {MappingRole.PRODUCT_OWNER},
            MappingWorkflowState.IN_REVIEW: {MappingRole.PRODUCT_OWNER},
        },
        MappingWorkflowState.SIGNED_OFF: {},
    }

    def validate(
        self,
        current: MappingWorkflowState,
        target: MappingWorkflowState,
        role: MappingRole,
    ) -> None:
        allowed = self._TRANSITIONS.get(current, {})
        roles = allowed.get(target)
        if roles is None:
            raise ValueError(f"Cannot transition from {current.value!r} to {target.value!r}")
        if role not in roles:
            raise ValueError(
                f"Role {role.value!r} cannot transition from {current.value!r} to {target.value!r}"
            )

    def next_states(self, current: MappingWorkflowState, role: MappingRole) -> list[str]:
        allowed = self._TRANSITIONS.get(current, {})
        return sorted(s.value for s, roles in allowed.items() if role in roles)
