"""Conversational mapping assistant — Q&A over schema, errors, transforms."""

from __future__ import annotations

from typing import Any

from migration_utility.ai.models import AssistantReply
from migration_utility.ai.provider import get_chat_model, provider_mode
from migration_utility.ai.retrieval import lookup_kraken_error, search_kraken_errors


class AiAssistantService:
    def answer(
        self,
        question: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AssistantReply:
        ctx = context or {}
        if provider_mode() == "langchain":
            llm_reply = self._llm_answer(question, ctx)
            if llm_reply:
                return llm_reply
        return self._heuristic_answer(question, ctx)

    def _heuristic_answer(self, question: str, ctx: dict[str, Any]) -> AssistantReply:
        q = question.lower()
        references: list[str] = []
        actions: list[str] = []

        if "kt-" in q or "error" in q or "kraken" in q:
            import re

            m = re.search(r"KT-(CT|GB)-\d+", question.upper())
            if m:
                code = m.group(0)
                detail = lookup_kraken_error(code)
                references.append(code)
                return AssistantReply(
                    answer=f"{code}: {detail.get('message') or detail.get('trigger') or 'See Kraken error catalog'}. "
                    f"Owner: {detail.get('owner_role', 'migration_engineer')}.",
                    references=references,
                    suggested_actions=[
                        "Check field mappings related to this error category",
                        "Review exception queue for affected records",
                    ],
                )
            hits = search_kraken_errors(question, limit=3)
            if hits:
                references.extend(h.get("code", "") for h in hits)
                return AssistantReply(
                    answer="; ".join(f"{h.get('code')}: {h.get('message') or h.get('trigger', '')}" for h in hits),
                    references=references,
                    suggested_actions=["Open Errors & Exceptions tab for batch triage"],
                )

        if "unmapped" in q or "mapping" in q:
            unmapped = ctx.get("unmapped_fields") or []
            if unmapped:
                return AssistantReply(
                    answer=f"Unmapped destination fields: {', '.join(unmapped[:10])}. "
                    "Use AI suggest or manual mapping; enum fields may need lookup transforms.",
                    suggested_actions=["Run AI suggest mappings", "Generate lookup tables for enum gaps"],
                )
            return AssistantReply(
                answer="Upload a source extract, then use Auto-suggest or AI suggest to map fields. "
                "AI proposes mappings — you approve before they enter the signed-off rule set.",
                suggested_actions=["Upload source CSV", "Click AI suggest mappings"],
            )

        if "transform" in q or "date" in q:
            return AssistantReply(
                answer="Common transforms: copy, lookup (for enums), pad_left (account numbers), "
                "date_format, STW-specific rules for utility migrations. "
                "Configure per-field in the mapping matrix; transforms run in the deterministic engine only.",
                suggested_actions=["Open Rules & Transforms tab", "Use STW Transforms for utility zone/property rules"],
            )

        return AssistantReply(
            answer="I can help with field mapping, Kraken error codes (e.g. KT-CT-10006), "
            "lookup tables, and transform rules. AI suggestions require human approval before migration runs.",
            suggested_actions=["Ask about a specific Kraken error code", "Ask why a field is unmapped"],
        )

    def _llm_answer(self, question: str, ctx: dict[str, Any]) -> AssistantReply | None:
        llm = get_chat_model()
        if llm is None:
            return None
        prompt = f"""You are a migration mapping assistant inside a schema-driven migration tool.
Policy: AI never writes to Kraken; only suggests mappings humans approve.

Context: {ctx}

Question: {question}
"""
        try:
            structured = llm.with_structured_output(AssistantReply)
            return structured.invoke(prompt)
        except Exception:
            return None
