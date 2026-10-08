from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .evaluation import run_evaluation
from .models import Device, MetricPoint
from .runtime import build_runtime


class DeviceOpsAPI(BaseHTTPRequestHandler):
    runtime = build_runtime("sqlite")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "deviceops-agent",
                    "llm_provider": self.runtime.llm_provider.name,
                    "repository": self.runtime.config.repository_kind,
                }
            )
        elif parsed.path == "/devices":
            devices = [asdict(device) for device in self.runtime.repository.list_devices()]
            self._send_json({"devices": devices})
        elif parsed.path == "/alerts":
            alerts = [self._serialize_alert(alert) for alert in self.runtime.repository.detect_alerts()]
            self._send_json({"alerts": alerts})
        elif parsed.path == "/diagnose":
            alert_id = query.get("alert_id", [None])[0]
            self._diagnose(alert_id)
        elif parsed.path == "/reports":
            reports = []
            if hasattr(self.runtime.repository, "list_diagnosis_reports"):
                reports = self.runtime.repository.list_diagnosis_reports()
            self._send_json({"reports": reports})
        elif parsed.path == "/evaluate":
            self._send_json(run_evaluation(repository_kind="sqlite", verbose=False))
        elif parsed.path == "/metrics":
            reports = []
            if hasattr(self.runtime.repository, "list_diagnosis_reports"):
                reports = self.runtime.repository.list_diagnosis_reports()
            self._send_json(
                {
                    "diagnosis_report_count": len(reports),
                    "latest_runs": [
                        {
                            "run_id": item["run_id"],
                            "alert_id": item["alert_id"],
                            "summary": item["summary"],
                        }
                        for item in reports[:5]
                    ],
                }
            )
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/diagnose":
            payload = self._read_json()
            self._diagnose(payload.get("alert_id"))
        elif parsed.path == "/devices":
            self._create_device(self._read_json())
        elif parsed.path == "/metric-points":
            self._create_metric_point(self._read_json())
        else:
            self._send_json({"error": "not found"}, status=404)

    def _diagnose(self, alert_id: str | None) -> None:
        alerts = self.runtime.repository.detect_alerts()
        alert = next((item for item in alerts if item.alert_id == alert_id), None) if alert_id else (alerts[0] if alerts else None)
        if not alert:
            self._send_json({"error": "alert not found"}, status=404)
            return
        report = self.runtime.agent.diagnose(alert)
        self._send_json({"report": asdict(report)})

    def _create_device(self, payload: dict[str, Any]) -> None:
        required = {"device_id", "name", "device_type", "location", "status"}
        missing = sorted(required - payload.keys())
        if missing:
            self._send_json({"error": "missing required fields", "fields": missing}, status=400)
            return
        device = Device(
            str(payload["device_id"]),
            str(payload["name"]),
            str(payload["device_type"]),
            str(payload["location"]),
            str(payload["status"]),
        )
        self.runtime.repository.upsert_device(device)
        self._send_json({"device": asdict(device)}, status=201)

    def _create_metric_point(self, payload: dict[str, Any]) -> None:
        required = {"device_id", "cpu_percent", "memory_percent", "disk_percent", "heartbeat_ok"}
        missing = sorted(required - payload.keys())
        if missing:
            self._send_json({"error": "missing required fields", "fields": missing}, status=400)
            return
        device_id = str(payload["device_id"])
        if not self.runtime.repository.get_device(device_id):
            self._send_json({"error": "device not found", "device_id": device_id}, status=404)
            return

        timestamp = payload.get("timestamp")
        point = MetricPoint(
            device_id=device_id,
            timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now().replace(microsecond=0),
            cpu_percent=float(payload["cpu_percent"]),
            memory_percent=float(payload["memory_percent"]),
            disk_percent=float(payload["disk_percent"]),
            heartbeat_ok=self._parse_bool(payload["heartbeat_ok"]),
        )
        self.runtime.repository.add_metric_point(point)
        alert = self.runtime.agent.tools.repository.detect_alerts()
        created_alert = next((item for item in alert if item.device_id == device_id), None)
        self._send_json(
            {
                "metric_point": {
                    "device_id": point.device_id,
                    "timestamp": point.timestamp.isoformat(),
                    "cpu_percent": point.cpu_percent,
                    "memory_percent": point.memory_percent,
                    "disk_percent": point.disk_percent,
                    "heartbeat_ok": point.heartbeat_ok,
                },
                "active_alert": self._serialize_alert(created_alert) if created_alert else None,
            },
            status=201,
        )

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    @staticmethod
    def _serialize_alert(alert) -> dict[str, Any]:
        data = asdict(alert)
        data["triggered_at"] = alert.triggered_at.isoformat()
        data["metric_snapshot"]["timestamp"] = alert.metric_snapshot.timestamp.isoformat()
        return data

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    config = DeviceOpsAPI.runtime.config
    server = ThreadingHTTPServer((config.api_host, config.api_port), DeviceOpsAPI)
    print(f"DeviceOps Agent API listening on http://{config.api_host}:{config.api_port}")
    print("Try /health, /devices, /alerts, /diagnose, /reports, /evaluate, /metrics")
    print("POST /devices and /metric-points to ingest new inventory and telemetry")
    server.serve_forever()


if __name__ == "__main__":
    main()
