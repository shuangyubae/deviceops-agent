from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class LLMProvider(Protocol):
    name: str

    def refine_plan(
        self,
        alert_context: dict[str, Any],
        draft_plan: list[dict[str, str]],
        allowed_tools: list[str],
    ) -> list[dict[str, str]] | None:
        """Return a refined diagnosis plan or None when no refinement is available."""

    def refine_report(self, context: dict[str, Any], draft_report: dict[str, Any]) -> dict[str, Any] | None:
        """Return a structured report or None when no refinement is available."""


@dataclass(frozen=True)
class DeterministicLLMProvider:
    name: str = "deterministic"

    def refine_plan(
        self,
        alert_context: dict[str, Any],
        draft_plan: list[dict[str, str]],
        allowed_tools: list[str],
    ) -> list[dict[str, str]] | None:
        return None

    def refine_report(self, context: dict[str, Any], draft_report: dict[str, Any]) -> dict[str, Any] | None:
        return None


@dataclass(frozen=True)
class OpenAICompatibleLLMProvider:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 15.0
    name: str = "openai-compatible"

    def refine_plan(
        self,
        alert_context: dict[str, Any],
        draft_plan: list[dict[str, str]],
        allowed_tools: list[str],
    ) -> list[dict[str, str]] | None:
        prompt = build_plan_prompt(alert_context, draft_plan, allowed_tools)
        candidate = self._chat_json(
            system_content=(
                "You are an incident diagnosis planner. Return strict JSON with key diagnosis_plan. "
                "Every plan item must contain step, tool, and purpose. Use only allowed tools."
            ),
            user_content=prompt,
        )
        if not candidate:
            return None
        return validate_llm_plan(candidate.get("diagnosis_plan"), allowed_tools)

    def refine_report(self, context: dict[str, Any], draft_report: dict[str, Any]) -> dict[str, Any] | None:
        prompt = build_report_prompt(context, draft_report)
        return self._chat_json(
            system_content=(
                "You are an incident diagnosis assistant. Use only the supplied evidence and citations. "
                "Return strict JSON with keys: root_cause, risk_level, evidence, suggested_actions, citations, refusal_reason. "
                "Do not invent facts, tools, metrics, sources, or remediation actions."
            ),
            user_content=prompt,
        )

    def _chat_json(self, system_content: str, user_content: str) -> dict[str, Any] | None:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError):
            return None

        try:
            response_payload = json.loads(raw)
            content = response_payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None


def build_plan_prompt(
    alert_context: dict[str, Any],
    draft_plan: list[dict[str, str]],
    allowed_tools: list[str],
) -> str:
    return json.dumps(
        {
            "task": "Refine the diagnosis plan for this alert.",
            "constraints": [
                "Use only tools from allowed_tools.",
                "Keep the plan concise and evidence-oriented.",
                "Do not add remediation actions; planning is only for diagnosis evidence collection.",
                "Return JSON: {\"diagnosis_plan\": [{\"step\": \"...\", \"tool\": \"...\", \"purpose\": \"...\"}]}",
            ],
            "allowed_tools": allowed_tools,
            "alert_context": alert_context,
            "draft_plan": draft_plan,
        },
        ensure_ascii=False,
        default=str,
    )


def build_report_prompt(context: dict[str, Any], draft_report: dict[str, Any]) -> str:
    return json.dumps(
        {
            "task": "Refine the draft diagnosis report while preserving evidence grounding.",
            "constraints": [
                "Use only the provided evidence, runbook citations, and tool outputs.",
                "If citations are empty or evidence is insufficient, keep refusal_reason non-null.",
                "Do not suggest destructive remediation such as deletion, restart, or rollback without human approval wording.",
                "Keep citations as filenames from the supplied citation list only.",
            ],
            "context": context,
            "draft_report": draft_report,
        },
        ensure_ascii=False,
        default=str,
    )


def validate_llm_plan(candidate: Any, allowed_tools: list[str]) -> list[dict[str, str]] | None:
    if not isinstance(candidate, list) or not candidate:
        return None
    allowed = set(allowed_tools)
    validated: list[dict[str, str]] = []
    seen_tools: set[str] = set()
    for item in candidate:
        if not isinstance(item, dict):
            return None
        if not {"step", "tool", "purpose"}.issubset(item):
            return None
        tool = str(item["tool"])
        if tool not in allowed:
            return None
        if tool in seen_tools:
            continue
        seen_tools.add(tool)
        validated.append(
            {
                "step": str(item["step"]),
                "tool": tool,
                "purpose": str(item["purpose"]),
            }
        )
    required_tools = {"query_device_status", "query_metric_window", "search_runbook"}
    if not required_tools.issubset({item["tool"] for item in validated}):
        return None
    return validated


def validate_llm_report(candidate: dict[str, Any], draft_report: dict[str, Any]) -> dict[str, Any] | None:
    required = {"root_cause", "risk_level", "evidence", "suggested_actions", "citations", "refusal_reason"}
    if not required.issubset(candidate):
        return None
    if not isinstance(candidate["evidence"], list) or not isinstance(candidate["suggested_actions"], list):
        return None
    if not isinstance(candidate["citations"], list):
        return None

    allowed_citations = set(draft_report.get("citations") or [])
    candidate_citations = set(candidate["citations"])
    if not candidate_citations.issubset(allowed_citations):
        return None
    if allowed_citations and not candidate_citations:
        return None
    if not allowed_citations and candidate.get("refusal_reason") is None:
        return None

    return {
        **draft_report,
        "root_cause": str(candidate["root_cause"]),
        "risk_level": str(candidate["risk_level"]),
        "evidence": [str(item) for item in candidate["evidence"]],
        "suggested_actions": [str(item) for item in candidate["suggested_actions"]],
        "citations": list(candidate["citations"]),
        "refusal_reason": candidate["refusal_reason"],
    }


def build_llm_provider(config) -> LLMProvider:
    if config.llm_provider == "openai-compatible" and config.llm_api_key:
        return OpenAICompatibleLLMProvider(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            timeout_seconds=config.llm_timeout_seconds,
        )
    return DeterministicLLMProvider()
