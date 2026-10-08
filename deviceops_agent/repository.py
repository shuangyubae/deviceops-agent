from __future__ import annotations

from datetime import datetime, timedelta

from .models import Alert, Device, MetricPoint
from .rules import AlertRuleEngine


class InMemoryRepository:
    """Small repository used to keep the MVP runnable without external services."""

    def __init__(self) -> None:
        now = datetime.now().replace(microsecond=0)
        self.devices = {
            "device-01": Device("device-01", "Edge Gateway A", "edge_gateway", "factory-a", "online"),
            "device-02": Device("device-02", "Vision Box B", "vision_box", "factory-a", "online"),
            "device-03": Device("device-03", "PLC Adapter C", "plc_adapter", "factory-b", "offline"),
            "device-04": Device("device-04", "Storage Node D", "storage_node", "factory-b", "online"),
        }
        self.metrics = [
            MetricPoint("device-01", now - timedelta(minutes=10), 42, 51, True, 48),
            MetricPoint("device-01", now - timedelta(minutes=8), 57, 53, True, 49),
            MetricPoint("device-01", now - timedelta(minutes=6), 76, 55, True, 50),
            MetricPoint("device-01", now - timedelta(minutes=4), 91, 57, True, 51),
            MetricPoint("device-01", now - timedelta(minutes=2), 96, 59, True, 52),
            MetricPoint("device-02", now - timedelta(minutes=10), 33, 62, True, 61),
            MetricPoint("device-02", now - timedelta(minutes=8), 38, 72, True, 62),
            MetricPoint("device-02", now - timedelta(minutes=6), 45, 83, True, 63),
            MetricPoint("device-02", now - timedelta(minutes=4), 46, 89, True, 64),
            MetricPoint("device-02", now - timedelta(minutes=2), 47, 93, True, 65),
            MetricPoint("device-03", now - timedelta(minutes=10), 12, 31, True, 40),
            MetricPoint("device-03", now - timedelta(minutes=8), 12, 31, True, 40),
            MetricPoint("device-03", now - timedelta(minutes=6), 0, 0, False, 0),
            MetricPoint("device-03", now - timedelta(minutes=4), 0, 0, False, 0),
            MetricPoint("device-03", now - timedelta(minutes=2), 0, 0, False, 0),
            MetricPoint("device-04", now - timedelta(minutes=10), 24, 45, True, 72),
            MetricPoint("device-04", now - timedelta(minutes=8), 26, 46, True, 79),
            MetricPoint("device-04", now - timedelta(minutes=6), 27, 48, True, 86),
            MetricPoint("device-04", now - timedelta(minutes=4), 29, 49, True, 91),
            MetricPoint("device-04", now - timedelta(minutes=2), 31, 50, True, 94),
        ]
        self.historical_alerts = [
            {
                "device_id": "device-01",
                "alert_type": "CPU_HIGH",
                "root_cause": "batch job duplicated after scheduler retry",
                "resolution": "disabled duplicate scheduler task and restarted worker",
            },
            {
                "device_id": "device-02",
                "alert_type": "MEMORY_HIGH",
                "root_cause": "image buffer not released after inference timeout",
                "resolution": "patched buffer cleanup and added memory guardrail",
            },
            {
                "device_id": "device-04",
                "alert_type": "DISK_HIGH",
                "root_cause": "application logs accumulated without rotation",
                "resolution": "enabled log rotation and cleaned confirmed temporary files",
            },
        ]
        self.recent_deployments = [
            {
                "device_id": "device-01",
                "changed_at": (now - timedelta(minutes=18)).isoformat(),
                "change_type": "scheduler_config",
                "summary": "Batch image aggregation job retry interval changed from 10 minutes to 1 minute.",
                "risk_hint": "May increase CPU load if the previous run has not finished.",
            },
            {
                "device_id": "device-02",
                "changed_at": (now - timedelta(minutes=25)).isoformat(),
                "change_type": "service_deploy",
                "summary": "Vision inference worker upgraded to v2.4.1.",
                "risk_hint": "May affect memory retention if image buffers are not released correctly.",
            },
            {
                "device_id": "device-04",
                "changed_at": (now - timedelta(minutes=30)).isoformat(),
                "change_type": "logging_config",
                "summary": "Debug logging enabled for storage sync worker.",
                "risk_hint": "May accelerate disk usage growth when sync errors repeat.",
            },
        ]

    def get_device(self, device_id: str) -> Device | None:
        return self.devices.get(device_id)

    def list_devices(self) -> list[Device]:
        return list(self.devices.values())

    def upsert_device(self, device: Device) -> None:
        self.devices[device.device_id] = device

    def add_metric_point(self, point: MetricPoint) -> None:
        self.metrics.append(point)

    def get_metric_window(self, device_id: str, minutes: int = 10) -> list[MetricPoint]:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [point for point in self.metrics if point.device_id == device_id and point.timestamp >= cutoff]

    def find_similar_alerts(self, device_id: str, alert_type: str) -> list[dict[str, str]]:
        return [
            alert
            for alert in self.historical_alerts
            if alert["device_id"] == device_id or alert["alert_type"] == alert_type
        ]

    def find_recent_deployments(self, device_id: str) -> list[dict[str, str]]:
        return [change for change in self.recent_deployments if change["device_id"] == device_id]

    def detect_alerts(self) -> list[Alert]:
        latest_by_device: dict[str, MetricPoint] = {}
        for point in self.metrics:
            latest_by_device[point.device_id] = point
        return AlertRuleEngine().evaluate_latest(latest_by_device)
