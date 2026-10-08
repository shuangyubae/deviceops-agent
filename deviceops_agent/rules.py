from __future__ import annotations

from .models import Alert, MetricPoint


class AlertRuleEngine:
    """Deterministic alert rules for metric snapshots."""

    def evaluate_latest(self, latest_by_device: dict[str, MetricPoint]) -> list[Alert]:
        alerts: list[Alert] = []
        for device_id, point in latest_by_device.items():
            alert = self.evaluate_point(point)
            if alert:
                alerts.append(alert)
        return alerts

    def evaluate_point(self, point: MetricPoint) -> Alert | None:
        if not point.heartbeat_ok:
            return Alert(
                f"alert-{point.device_id}-offline",
                point.device_id,
                "DEVICE_OFFLINE",
                "critical",
                "Device heartbeat is missing.",
                point.timestamp,
                point,
            )
        if point.cpu_percent >= 90:
            return Alert(
                f"alert-{point.device_id}-cpu",
                point.device_id,
                "CPU_HIGH",
                "warning",
                "CPU usage is above threshold.",
                point.timestamp,
                point,
            )
        if point.memory_percent >= 90:
            return Alert(
                f"alert-{point.device_id}-memory",
                point.device_id,
                "MEMORY_HIGH",
                "warning",
                "Memory usage is above threshold.",
                point.timestamp,
                point,
            )
        if point.disk_percent >= 90:
            return Alert(
                f"alert-{point.device_id}-disk",
                point.device_id,
                "DISK_HIGH",
                "warning",
                "Disk usage is above threshold.",
                point.timestamp,
                point,
            )
        return None
