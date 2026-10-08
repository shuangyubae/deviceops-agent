from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ToolResult
from .rag import RunbookRetriever


class DeviceOpsTools:
    def __init__(self, repository: Any, runbook_dir: Path) -> None:
        self.repository = repository
        self.retriever = RunbookRetriever(runbook_dir)

    def query_device_status(self, device_id: str) -> ToolResult:
        device = self.repository.get_device(device_id)
        if not device:
            return ToolResult("query_device_status", False, None, "device not found")
        return ToolResult("query_device_status", True, device.__dict__)

    def query_metric_window(self, device_id: str, minutes: int = 10) -> ToolResult:
        points = self.repository.get_metric_window(device_id, minutes)
        if not points:
            return ToolResult("query_metric_window", False, [], "no metrics found")
        return ToolResult(
            "query_metric_window",
            True,
            [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "cpu_percent": point.cpu_percent,
                    "memory_percent": point.memory_percent,
                    "disk_percent": point.disk_percent,
                    "heartbeat_ok": point.heartbeat_ok,
                }
                for point in points
            ],
        )

    def search_runbook(self, query: str) -> ToolResult:
        hits = self.retriever.search(query)
        return ToolResult("search_runbook", True, [hit.__dict__ for hit in hits])

    def query_similar_alerts(self, device_id: str, alert_type: str) -> ToolResult:
        alerts = self.repository.find_similar_alerts(device_id, alert_type)
        return ToolResult("query_similar_alerts", True, alerts)

    def query_recent_deployments(self, device_id: str) -> ToolResult:
        deployments = self.repository.find_recent_deployments(device_id)
        return ToolResult("query_recent_deployments", True, deployments)
