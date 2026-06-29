"""LangGraph / heuristic error triage for migration batches."""

from __future__ import annotations

from typing import Any, TypedDict

from migration_utility.ai.heuristic import triage_errors_heuristic
from migration_utility.ai.models import ErrorCluster, ErrorTriageReport
from migration_utility.ai.provider import get_chat_model, provider_mode
from migration_utility.ai.retrieval import lookup_kraken_error


class TriageState(TypedDict, total=False):
    errors: list[dict[str, Any]]
    clusters: list[dict[str, Any]]
    cluster_index: int
    report: ErrorTriageReport


class AiErrorTriageService:
    def triage(self, errors: list[dict[str, Any]]) -> ErrorTriageReport:
        if not errors:
            return ErrorTriageReport(total_errors=0, executive_summary="No errors to triage.")

        if provider_mode() == "langchain":
            try:
                return self._triage_langgraph(errors)
            except Exception:
                pass
        return triage_errors_heuristic(errors)

    def _triage_langgraph(self, errors: list[dict[str, Any]]) -> ErrorTriageReport:
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return triage_errors_heuristic(errors)

        def fetch_errors(state: TriageState) -> TriageState:
            return {**state, "errors": errors}

        def cluster_by_code(state: TriageState) -> TriageState:
            buckets: dict[str, list[dict]] = {}
            for err in state["errors"]:
                code = err.get("kraken_error_code") or "unknown"
                buckets.setdefault(code, []).append(err)
            clusters = [
                {"code": code, "items": items, "count": len(items)}
                for code, items in sorted(buckets.items(), key=lambda x: -len(x[1]))
            ]
            return {**state, "clusters": clusters, "cluster_index": 0}

        def lookup_and_summarize(state: TriageState) -> TriageState:
            idx = state.get("cluster_index", 0)
            clusters_raw = state.get("clusters") or []
            if idx >= len(clusters_raw):
                return state

            raw = clusters_raw[idx]
            code = raw["code"]
            detail = lookup_kraken_error(code) if code.startswith("KT-") else {}
            items = raw["items"]
            cluster = ErrorCluster(
                kraken_error_code=code if code.startswith("KT-") else None,
                error_class=code,
                count=raw["count"],
                sample_messages=[str(i.get("error_reason", ""))[:200] for i in items[:3]],
                likely_root_cause=detail.get("message") or detail.get("trigger") or items[0].get("error_reason", "")[:300],
                suggested_mapping_check=items[0].get("remediation_hint") or "Review mappings for this error class",
                owner_role=detail.get("owner_role") or items[0].get("owner_role"),
            )

            report = state.get("report") or ErrorTriageReport(total_errors=len(errors), provider="langchain")
            report.clusters = [*report.clusters, cluster]
            return {**state, "report": report, "cluster_index": idx + 1}

        def draft_summary(state: TriageState) -> TriageState:
            report = state.get("report") or ErrorTriageReport(total_errors=len(errors), provider="langchain")
            if not report.executive_summary and report.clusters:
                top = report.clusters[0]
                report.executive_summary = (
                    f"{report.total_errors} error(s) in {len(report.clusters)} cluster(s). "
                    f"Largest: {top.count}× {top.kraken_error_code or top.error_class}."
                )
            return {**state, "report": report}

        graph = StateGraph(TriageState)
        graph.add_node("fetch", fetch_errors)
        graph.add_node("cluster", cluster_by_code)
        graph.add_node("lookup", lookup_and_summarize)
        graph.add_node("summarize", draft_summary)
        graph.set_entry_point("fetch")
        graph.add_edge("fetch", "cluster")
        graph.add_edge("cluster", "lookup")

        def maybe_continue(state: TriageState) -> str:
            idx = state.get("cluster_index", 0)
            total = len(state.get("clusters") or [])
            return "lookup" if idx < total else "summarize"

        graph.add_conditional_edges("lookup", maybe_continue, {"lookup": "lookup", "summarize": "summarize"})
        graph.add_edge("summarize", END)

        final = graph.compile().invoke({"errors": errors})
        report = final.get("report")
        if report:
            return report
        return triage_errors_heuristic(errors)
