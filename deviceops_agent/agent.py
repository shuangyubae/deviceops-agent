from __future__ import annotations

from dataclasses import asdict

from .confidence import calculate_confidence
from .llm import DeterministicLLMProvider, LLMProvider, validate_llm_report
from .models import AgentTrace, Alert, DiagnosisReport
from .tools import DeviceOpsTools
from .trace import TraceRecorder


class IncidentAgentOrchestrator:
    def __init__(
        self,
        tools: DeviceOpsTools,
        trace_recorder: TraceRecorder,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.tools = tools
        self.trace_recorder = trace_recorder
        self.llm_provider = llm_provider or DeterministicLLMProvider()

    def diagnose(self, alert: Alert) -> DiagnosisReport:
        trace = AgentTrace()

        draft_plan_output = self.trace_recorder.record_step(
            trace,
            "draft_plan_diagnosis",
            {"alert_type": alert.alert_type},
            lambda: {"diagnosis_plan": self._build_plan(alert.alert_type)},
        )
        draft_plan = draft_plan_output["diagnosis_plan"]
        plan = self.trace_recorder.record_step(
            trace,
            "refine_plan_with_llm",
            {
                "provider": self.llm_provider.name,
                "enabled": self.llm_provider.name != "deterministic",
                "draft_plan": draft_plan,
                "allowed_tools": self._allowed_tools(),
            },
            lambda: self._refine_plan_with_llm(alert, draft_plan),
        )
        diagnosis_plan = plan["diagnosis_plan"]

        tool_outputs = self._execute_plan(trace, alert, diagnosis_plan)
        device_status = tool_outputs.get("query_device_status", self._empty_tool_result("query_device_status"))
        metric_window = tool_outputs.get("query_metric_window", self._empty_tool_result("query_metric_window", []))
        similar_alerts = tool_outputs.get("query_similar_alerts", self._empty_tool_result("query_similar_alerts", []))
        recent_deployments = tool_outputs.get(
            "query_recent_deployments",
            self._empty_tool_result("query_recent_deployments", []),
        )
        runbook_hits = tool_outputs.get("search_runbook", self._empty_tool_result("search_runbook", []))

        report_data = self.trace_recorder.record_step(
            trace,
            "generate_draft_diagnosis",
            {
                "alert": alert.__dict__ | {"triggered_at": alert.triggered_at.isoformat()},
                "plan": plan,
                "device_status": device_status,
                "metric_window": metric_window,
                "similar_alerts": similar_alerts,
                "recent_deployments": recent_deployments,
                "runbook_hits": runbook_hits,
            },
            lambda: self._generate_report(
                alert,
                diagnosis_plan,
                device_status,
                metric_window,
                similar_alerts,
                recent_deployments,
                runbook_hits,
            ),
        )
        report_data = {**report_data, "planning_provider": plan.get("planning_provider", "deterministic")}
        report_data = self.trace_recorder.record_step(
            trace,
            "refine_with_llm",
            {
                "provider": self.llm_provider.name,
                "enabled": self.llm_provider.name != "deterministic",
                "draft_report": report_data,
            },
            lambda: self._refine_with_llm(
                {
                    "alert": alert.__dict__ | {"triggered_at": alert.triggered_at.isoformat()},
                    "diagnosis_plan": diagnosis_plan,
                    "tool_outputs": tool_outputs,
                },
                report_data,
            ),
        )
        trace_path = self.trace_recorder.save(trace)
        report = DiagnosisReport(run_id=trace.run_id, alert_id=alert.alert_id, trace_path=str(trace_path), **report_data)
        if hasattr(self.tools.repository, "save_diagnosis_report"):
            self.tools.repository.save_diagnosis_report(report, asdict(trace), self.trace_recorder.summarize(trace))
        return report

    def _call_tool(self, trace: AgentTrace, name: str, fn, input_data: dict) -> dict:
        return self.trace_recorder.record_step(trace, f"tool_{name}", input_data, fn)

    def _refine_plan_with_llm(self, alert: Alert, draft_plan: list[dict[str, str]]) -> dict:
        refined = self.llm_provider.refine_plan(
            {
                "alert_id": alert.alert_id,
                "device_id": alert.device_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
            },
            draft_plan,
            self._allowed_tools(),
        )
        if refined is None:
            return {
                "diagnosis_plan": draft_plan,
                "planning_provider": "deterministic",
            }
        return {
            "diagnosis_plan": refined,
            "planning_provider": self.llm_provider.name,
        }

    def _refine_with_llm(self, context: dict, draft_report: dict) -> dict:
        candidate = self.llm_provider.refine_report(context, draft_report)
        if candidate is None:
            return {**draft_report, "generation_provider": "deterministic"}
        validated = validate_llm_report(candidate, draft_report)
        if validated is None:
            return {**draft_report, "generation_provider": "deterministic_fallback"}
        return {**validated, "generation_provider": self.llm_provider.name}

    def _execute_plan(self, trace: AgentTrace, alert: Alert, diagnosis_plan: list[dict[str, str]]) -> dict[str, dict]:
        outputs: dict[str, dict] = {}
        for plan_step in diagnosis_plan:
            tool_name = plan_step["tool"]
            if tool_name in outputs:
                continue
            input_data, fn = self._build_tool_invocation(tool_name, alert)
            outputs[tool_name] = self._call_tool(trace, tool_name, fn, input_data)
        return outputs

    def _build_tool_invocation(self, tool_name: str, alert: Alert):
        if tool_name == "query_device_status":
            input_data = {"device_id": alert.device_id}
            return input_data, lambda: self.tools.query_device_status(alert.device_id).__dict__
        if tool_name == "query_metric_window":
            input_data = {"device_id": alert.device_id, "minutes": 10}
            return input_data, lambda: self.tools.query_metric_window(alert.device_id).__dict__
        if tool_name == "query_similar_alerts":
            input_data = {"device_id": alert.device_id, "alert_type": alert.alert_type}
            return input_data, lambda: self.tools.query_similar_alerts(alert.device_id, alert.alert_type).__dict__
        if tool_name == "query_recent_deployments":
            input_data = {"device_id": alert.device_id}
            return input_data, lambda: self.tools.query_recent_deployments(alert.device_id).__dict__
        if tool_name == "search_runbook":
            query = f"{alert.alert_type} {alert.message}"
            input_data = {"query": query}
            return input_data, lambda: self.tools.search_runbook(query).__dict__
        input_data = {"tool": tool_name}
        return input_data, lambda: self._empty_tool_result(tool_name, error=f"unsupported tool: {tool_name}")

    @staticmethod
    def _empty_tool_result(tool_name: str, data=None, error: str | None = None) -> dict:
        return {"tool_name": tool_name, "ok": error is None, "data": data, "error": error}

    @staticmethod
    def _allowed_tools() -> list[str]:
        return [
            "query_device_status",
            "query_metric_window",
            "query_similar_alerts",
            "query_recent_deployments",
            "search_runbook",
        ]

    @staticmethod
    def _build_plan(alert_type: str) -> list[dict[str, str]]:
        plans: dict[str, list[dict[str, str]]] = {
            "CPU_HIGH": [
                {
                    "step": "confirm_device_context",
                    "tool": "query_device_status",
                    "purpose": "Confirm the affected device, location, and online status.",
                },
                {
                    "step": "inspect_cpu_trend",
                    "tool": "query_metric_window",
                    "purpose": "Check whether CPU saturation is sustained rather than a short spike.",
                },
                {
                    "step": "compare_historical_incidents",
                    "tool": "query_similar_alerts",
                    "purpose": "Look for repeated CPU incidents and previous resolutions.",
                },
                {
                    "step": "check_recent_changes",
                    "tool": "query_recent_deployments",
                    "purpose": "Check whether recent scheduler or deployment changes may explain CPU growth.",
                },
                {
                    "step": "retrieve_cpu_runbook",
                    "tool": "search_runbook",
                    "purpose": "Find CPU_HIGH operational guidance and safe next actions.",
                },
            ],
            "MEMORY_HIGH": [
                {
                    "step": "confirm_device_context",
                    "tool": "query_device_status",
                    "purpose": "Confirm the affected device, location, and online status.",
                },
                {
                    "step": "inspect_memory_trend",
                    "tool": "query_metric_window",
                    "purpose": "Check whether memory pressure keeps growing over the time window.",
                },
                {
                    "step": "compare_historical_incidents",
                    "tool": "query_similar_alerts",
                    "purpose": "Look for previous memory pressure incidents and fixes.",
                },
                {
                    "step": "check_recent_changes",
                    "tool": "query_recent_deployments",
                    "purpose": "Check whether a recent service deployment may explain memory growth.",
                },
                {
                    "step": "retrieve_memory_runbook",
                    "tool": "search_runbook",
                    "purpose": "Find MEMORY_HIGH runbook evidence and safe handling steps.",
                },
            ],
            "DEVICE_OFFLINE": [
                {
                    "step": "confirm_device_context",
                    "tool": "query_device_status",
                    "purpose": "Confirm whether the device is marked offline and where it is located.",
                },
                {
                    "step": "inspect_heartbeat_trend",
                    "tool": "query_metric_window",
                    "purpose": "Check when heartbeat stopped and whether metrics became stale.",
                },
                {
                    "step": "compare_historical_incidents",
                    "tool": "query_similar_alerts",
                    "purpose": "Look for repeated offline incidents on the same device type.",
                },
                {
                    "step": "retrieve_offline_runbook",
                    "tool": "search_runbook",
                    "purpose": "Find DEVICE_OFFLINE runbook guidance for connectivity and power checks.",
                },
            ],
            "DISK_HIGH": [
                {
                    "step": "confirm_device_context",
                    "tool": "query_device_status",
                    "purpose": "Confirm the affected storage node, location, and online status.",
                },
                {
                    "step": "inspect_disk_trend",
                    "tool": "query_metric_window",
                    "purpose": "Check whether disk usage is steadily increasing and close to saturation.",
                },
                {
                    "step": "compare_historical_incidents",
                    "tool": "query_similar_alerts",
                    "purpose": "Look for past disk incidents such as log accumulation or cache growth.",
                },
                {
                    "step": "check_recent_changes",
                    "tool": "query_recent_deployments",
                    "purpose": "Check whether logging or storage changes may explain disk growth.",
                },
                {
                    "step": "retrieve_disk_runbook",
                    "tool": "search_runbook",
                    "purpose": "Find DISK_HIGH runbook guidance before suggesting any cleanup action.",
                },
            ],
        }
        return plans.get(
            alert_type,
            [
                {
                    "step": "confirm_device_context",
                    "tool": "query_device_status",
                    "purpose": "Confirm the affected device before making a diagnosis.",
                },
                {
                    "step": "inspect_metric_window",
                    "tool": "query_metric_window",
                    "purpose": "Collect recent metric evidence for the unknown alert type.",
                },
                {
                    "step": "retrieve_generic_runbook",
                    "tool": "search_runbook",
                    "purpose": "Search operational knowledge before giving a conclusion.",
                },
            ],
        )

    @staticmethod
    def _generate_report(
        alert: Alert,
        diagnosis_plan: list[dict[str, str]],
        device_status: dict,
        metric_window: dict,
        similar_alerts: dict,
        recent_deployments: dict,
        runbook_hits: dict,
    ) -> dict:
        evidence: list[str] = [f"Alert {alert.alert_id}: {alert.message}"]
        citations: list[str] = []
        suggested_actions: list[str] = []
        failed_tool_count = 0

        if device_status.get("ok"):
            data = device_status["data"]
            evidence.append(f"Device {data['device_id']} is {data['status']} at {data['location']}.")
        else:
            failed_tool_count += 1

        metrics = metric_window.get("data") or []
        if metrics:
            first = metrics[0]
            latest = metrics[-1]
            evidence.append(
                f"Metric trend: CPU {first['cpu_percent']}% -> {latest['cpu_percent']}%, "
                f"memory {first['memory_percent']}% -> {latest['memory_percent']}%, "
                f"disk {first.get('disk_percent', 0)}% -> {latest.get('disk_percent', 0)}%, "
                f"heartbeat latest={latest['heartbeat_ok']}."
            )
        elif not metric_window.get("ok", True):
            failed_tool_count += 1

        historical = similar_alerts.get("data") or []
        if historical:
            evidence.append(f"Found {len(historical)} similar historical alert(s).")
            suggested_actions.append(f"Review previous resolution: {historical[0]['resolution']}.")

        deployments = recent_deployments.get("data") or []
        if deployments:
            latest_change = deployments[0]
            evidence.append(
                f"Recent change {latest_change['change_type']} at {latest_change['changed_at']}: "
                f"{latest_change['summary']} Risk hint: {latest_change['risk_hint']}"
            )
            suggested_actions.append("Review the recent change and correlate it with the alert time window.")

        runbooks = runbook_hits.get("data") or []
        if runbooks:
            top = runbooks[0]
            evidence.append(f"Matched runbook {top['source']}: {top['snippet']}")
            citations.append(top["source"])

        confidence_breakdown = calculate_confidence(
            has_device_context=bool(device_status.get("ok")),
            has_metric_trend=bool(metrics),
            has_historical_incidents=bool(historical),
            has_recent_changes=bool(deployments),
            has_runbook_evidence=bool(runbooks),
            failed_tool_count=failed_tool_count,
        )
        confidence = confidence_breakdown.total
        evidence.append(confidence_breakdown.as_evidence())

        if not runbooks and confidence < 0.65:
            return {
                "diagnosis_plan": diagnosis_plan,
                "root_cause": "Evidence is insufficient for a confident root-cause diagnosis.",
                "confidence": confidence,
                "risk_level": "unknown",
                "evidence": evidence,
                "suggested_actions": [
                    "Collect more logs or runbook evidence before making a firm conclusion.",
                    "Escalate to human review.",
                ],
                "citations": citations,
                "refusal_reason": "No reliable runbook evidence was retrieved.",
            }

        if alert.alert_type == "CPU_HIGH":
            root_cause = "Sustained CPU saturation, likely caused by a repeated task or abnormal workload."
            suggested_actions += ["Check top CPU processes.", "Verify recent scheduler or deployment changes."]
            risk_level = "medium"
        elif alert.alert_type == "MEMORY_HIGH":
            root_cause = "Memory pressure is increasing, possibly due to buffer retention or leak-like behavior."
            suggested_actions += ["Check memory growth trend.", "Inspect recent process or inference workload changes."]
            risk_level = "medium"
        elif alert.alert_type == "DEVICE_OFFLINE":
            root_cause = "Device heartbeat is missing, likely caused by device offline state or network interruption."
            suggested_actions += ["Check network connectivity.", "Verify last heartbeat and power state."]
            risk_level = "high"
        elif alert.alert_type == "DISK_HIGH":
            root_cause = "Disk usage is high, likely caused by log accumulation, cache growth, or large temporary files."
            suggested_actions += [
                "Check disk usage by directory.",
                "Inspect log rotation and recent error log growth.",
                "Clean confirmed temporary files after preserving diagnostic evidence.",
            ]
            risk_level = "medium"
        else:
            root_cause = "The alert pattern is not mapped to a known diagnosis path."
            suggested_actions += ["Escalate to human review."]
            risk_level = "unknown"

        return {
            "diagnosis_plan": diagnosis_plan,
            "root_cause": root_cause,
            "confidence": confidence,
            "risk_level": risk_level,
            "evidence": evidence,
            "suggested_actions": suggested_actions,
            "citations": citations,
            "refusal_reason": None,
        }
