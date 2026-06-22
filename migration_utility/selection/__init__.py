"""Candidate selection — switchable criteria framework."""

__all__ = [
    "CandidateService",
    "SelectionEngine",
    "SelectionLoader",
    "SelectionProfileService",
]


def __getattr__(name: str):
    if name == "CandidateService":
        from migration_utility.selection.service import CandidateService
        return CandidateService
    if name == "SelectionEngine":
        from migration_utility.selection.engine import SelectionEngine
        return SelectionEngine
    if name == "SelectionLoader":
        from migration_utility.selection.loader import SelectionLoader
        return SelectionLoader
    if name == "SelectionProfileService":
        from migration_utility.selection.service import SelectionProfileService
        return SelectionProfileService
    raise AttributeError(name)
