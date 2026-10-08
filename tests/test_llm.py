from __future__ import annotations

import unittest

from deviceops_agent.llm import build_plan_prompt, build_report_prompt, validate_llm_plan, validate_llm_report


class LLMValidationTest(unittest.TestCase):
    def test_plan_prompt_contains_allowed_tools(self) -> None:
        prompt = build_plan_prompt(
            {"alert_type": "CPU_HIGH"},
            [{"step": "inspect", "tool": "query_metric_window", "purpose": "Inspect metrics."}],
            ["query_device_status", "query_metric_window", "search_runbook"],
        )

        self.assertIn("allowed_tools", prompt)
        self.assertIn("query_metric_window", prompt)

    def test_rejects_plan_with_unapproved_tool(self) -> None:
        candidate = [
            {"step": "shell", "tool": "run_shell_command", "purpose": "Inspect host."},
            {"step": "metric", "tool": "query_metric_window", "purpose": "Inspect metrics."},
            {"step": "runbook", "tool": "search_runbook", "purpose": "Find runbook."},
            {"step": "device", "tool": "query_device_status", "purpose": "Find device."},
        ]

        self.assertIsNone(
            validate_llm_plan(
                candidate,
                ["query_device_status", "query_metric_window", "search_runbook"],
            )
        )

    def test_accepts_grounded_plan(self) -> None:
        candidate = [
            {"step": "device", "tool": "query_device_status", "purpose": "Find device."},
            {"step": "metric", "tool": "query_metric_window", "purpose": "Inspect metrics."},
            {"step": "runbook", "tool": "search_runbook", "purpose": "Find runbook."},
        ]

        validated = validate_llm_plan(
            candidate,
            ["query_device_status", "query_metric_window", "search_runbook"],
        )

        self.assertEqual(candidate, validated)

    def test_prompt_contains_grounding_constraints(self) -> None:
        prompt = build_report_prompt({"alert": {"alert_type": "CPU_HIGH"}}, {"citations": ["cpu_high.md"]})

        self.assertIn("Use only the provided evidence", prompt)
        self.assertIn("cpu_high.md", prompt)

    def test_rejects_citation_not_present_in_draft(self) -> None:
        draft = {
            "diagnosis_plan": [],
            "root_cause": "draft",
            "confidence": 0.8,
            "risk_level": "medium",
            "evidence": ["evidence"],
            "suggested_actions": ["action"],
            "citations": ["cpu_high.md"],
            "refusal_reason": None,
        }
        candidate = {
            "root_cause": "refined",
            "risk_level": "medium",
            "evidence": ["refined evidence"],
            "suggested_actions": ["refined action"],
            "citations": ["unknown.md"],
            "refusal_reason": None,
        }

        self.assertIsNone(validate_llm_report(candidate, draft))

    def test_accepts_grounded_structured_report(self) -> None:
        draft = {
            "diagnosis_plan": [],
            "root_cause": "draft",
            "confidence": 0.8,
            "risk_level": "medium",
            "evidence": ["evidence"],
            "suggested_actions": ["action"],
            "citations": ["cpu_high.md"],
            "refusal_reason": None,
        }
        candidate = {
            "root_cause": "refined",
            "risk_level": "medium",
            "evidence": ["refined evidence"],
            "suggested_actions": ["refined action"],
            "citations": ["cpu_high.md"],
            "refusal_reason": None,
        }

        validated = validate_llm_report(candidate, draft)

        self.assertIsNotNone(validated)
        self.assertEqual("refined", validated["root_cause"])
        self.assertEqual(["cpu_high.md"], validated["citations"])


if __name__ == "__main__":
    unittest.main()
