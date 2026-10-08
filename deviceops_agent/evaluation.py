from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import Alert, MetricPoint
from .runtime import build_runtime


def run_evaluation(repository_kind: str = "memory", verbose: bool = True) -> dict:
    runtime = build_runtime(repository_kind)
    repository = runtime.repository
    agent = runtime.agent

    detected_alerts = repository.detect_alerts()
    reports = {alert.alert_id: agent.diagnose(alert) for alert in detected_alerts}

    unknown_alert = Alert(
        "eval-unknown-device",
        "device-99",
        "UNKNOWN_SENSOR_DRIFT",
        "warning",
        "Unknown sensor drift alert has no approved runbook.",
        datetime.now().replace(microsecond=0),
        MetricPoint("device-99", datetime.now().replace(microsecond=0), 0, 0, False, 0),
    )
    unknown_report = agent.diagnose(unknown_alert)

    cases = []
    expected_keywords = {
        "CPU_HIGH": "cpu",
        "MEMORY_HIGH": "memory",
        "DEVICE_OFFLINE": "heartbeat",
        "DISK_HIGH": "disk",
    }
    expected_citations = {
        "CPU_HIGH": "cpu_high.md",
        "MEMORY_HIGH": "memory_high.md",
        "DEVICE_OFFLINE": "device_offline.md",
        "DISK_HIGH": "disk_high.md",
    }

    for alert in detected_alerts:
        report = reports[alert.alert_id]
        haystack = " ".join([report.root_cause, *report.evidence]).lower()
        plan_tools = {step["tool"] for step in report.diagnosis_plan}
        cases.append(
            _case(
                f"{alert.alert_id}: root cause direction",
                expected_keywords[alert.alert_type] in haystack,
                f"keyword={expected_keywords[alert.alert_type]} confidence={report.confidence}",
            )
        )
        cases.append(
            _case(
                f"{alert.alert_id}: citation",
                expected_citations[alert.alert_type] in report.citations,
                f"citations={report.citations}",
            )
        )
        cases.append(
            _case(
                f"{alert.alert_id}: minimum tool plan",
                {"query_device_status", "query_metric_window", "search_runbook"}.issubset(plan_tools),
                f"tools={sorted(plan_tools)}",
            )
        )

    cases.append(
        _case(
            "unknown alert refuses without citation",
            unknown_report.refusal_reason is not None and not unknown_report.citations,
            f"refusal_reason={unknown_report.refusal_reason!r} citations={unknown_report.citations}",
        )
    )
    cases.append(
        _case(
            "confidence is capped",
            all(report.confidence <= 0.95 for report in reports.values()),
            f"confidences={[report.confidence for report in reports.values()]}",
        )
    )
    cases.append(
        _case(
            "trace files are generated",
            all(report.trace_path and Path(report.trace_path).exists() for report in reports.values()),
            "all detected alert reports include an existing trace_path",
        )
    )

    passed = sum(1 for case in cases if case["passed"])
    result = {
        "passed": passed,
        "total": len(cases),
        "accuracy": passed / len(cases) if cases else 0.0,
        "cases": cases,
    }

    if verbose:
        for case in cases:
            print(f"{case['name']}: {'PASS' if case['passed'] else 'FAIL'} {case['detail']}")
        print(f"Evaluation accuracy: {passed}/{len(cases)} = {result['accuracy']:.2%}")

    return result


def _case(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": passed, "detail": detail}


def main() -> None:
    run_evaluation(repository_kind="memory", verbose=True)


if __name__ == "__main__":
    main()
