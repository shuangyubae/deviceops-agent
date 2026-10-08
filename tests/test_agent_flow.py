from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from deviceops_agent.agent import IncidentAgentOrchestrator
from deviceops_agent.evaluation import run_evaluation
from deviceops_agent.models import Device, MetricPoint
from deviceops_agent.repository import InMemoryRepository
from deviceops_agent.tools import DeviceOpsTools
from deviceops_agent.trace import TraceRecorder


class AgentFlowTest(unittest.TestCase):
    def test_detects_expected_alerts(self) -> None:
        repository = InMemoryRepository()
        alert_types = {alert.alert_type for alert in repository.detect_alerts()}

        self.assertEqual({"CPU_HIGH", "MEMORY_HIGH", "DEVICE_OFFLINE", "DISK_HIGH"}, alert_types)

    def test_diagnosis_contains_citation_and_confidence_breakdown(self) -> None:
        repository = InMemoryRepository()
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            tools = DeviceOpsTools(repository, project_root / "data" / "runbooks")
            agent = IncidentAgentOrchestrator(tools, TraceRecorder(Path(tmpdir)))
            report = agent.diagnose(repository.detect_alerts()[0])

        self.assertTrue(report.citations)
        self.assertLessEqual(report.confidence, 0.95)
        self.assertTrue(any("Confidence breakdown" in item for item in report.evidence))

    def test_evaluation_suite_passes(self) -> None:
        result = run_evaluation(repository_kind="memory", verbose=False)

        self.assertEqual(result["passed"], result["total"])
        self.assertGreaterEqual(result["total"], 10)

    def test_ingested_metric_can_create_alert(self) -> None:
        repository = InMemoryRepository()
        repository.upsert_device(Device("device-new", "New Gateway", "edge_gateway", "factory-c", "online"))
        repository.add_metric_point(
            MetricPoint(
                "device-new",
                datetime.now().replace(microsecond=0),
                cpu_percent=95,
                memory_percent=40,
                heartbeat_ok=True,
                disk_percent=30,
            )
        )

        alerts = repository.detect_alerts()

        self.assertTrue(any(alert.device_id == "device-new" and alert.alert_type == "CPU_HIGH" for alert in alerts))


if __name__ == "__main__":
    unittest.main()
