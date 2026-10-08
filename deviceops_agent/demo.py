from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .agent import IncidentAgentOrchestrator
from .repository import InMemoryRepository
from .tools import DeviceOpsTools
from .trace import TraceRecorder


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    repository = InMemoryRepository()
    tools = DeviceOpsTools(repository, project_root / "data" / "runbooks")
    traces = TraceRecorder(project_root / "data" / "traces")
    agent = IncidentAgentOrchestrator(tools, traces)

    alerts = repository.detect_alerts()
    print(f"Detected {len(alerts)} alert(s).")
    for alert in alerts:
        report = agent.diagnose(alert)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

