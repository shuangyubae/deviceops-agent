from __future__ import annotations

import json
from dataclasses import asdict

from .runtime import build_runtime


def main() -> None:
    runtime = build_runtime("sqlite")
    alerts = runtime.repository.detect_alerts()
    reports = [runtime.agent.diagnose(alert) for alert in alerts]
    saved_reports = []
    if hasattr(runtime.repository, "list_diagnosis_reports"):
        saved_reports = runtime.repository.list_diagnosis_reports()

    print(
        json.dumps(
            {
                "devices": len(runtime.repository.list_devices()),
                "alerts": len(alerts),
                "diagnosed": len(reports),
                "saved_reports": len(saved_reports),
                "sample_report": asdict(reports[0]) if reports else None,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
