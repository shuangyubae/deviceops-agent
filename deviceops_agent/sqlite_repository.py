from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Alert, Device, DiagnosisReport, MetricPoint
from .repository import InMemoryRepository
from .rules import AlertRuleEngine


class SQLiteRepository:
    """SQLite-backed repository for the complete local project delivery."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        if self._is_empty():
            self.seed_from_memory()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS metric_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    disk_percent REAL NOT NULL,
                    heartbeat_ok INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS historical_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    resolution TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS recent_deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    risk_hint TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS diagnosis_reports (
                    run_id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _is_empty(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM devices").fetchone()
            return int(row["count"]) == 0

    def seed_from_memory(self) -> None:
        seed = InMemoryRepository()
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO devices VALUES (?, ?, ?, ?, ?)",
                [
                    (device.device_id, device.name, device.device_type, device.location, device.status)
                    for device in seed.devices.values()
                ],
            )
            conn.executemany(
                """
                INSERT INTO metric_points
                (device_id, timestamp, cpu_percent, memory_percent, disk_percent, heartbeat_ok)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        point.device_id,
                        point.timestamp.isoformat(),
                        point.cpu_percent,
                        point.memory_percent,
                        point.disk_percent,
                        int(point.heartbeat_ok),
                    )
                    for point in seed.metrics
                ],
            )
            conn.executemany(
                """
                INSERT INTO historical_alerts
                (device_id, alert_type, root_cause, resolution)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        alert["device_id"],
                        alert["alert_type"],
                        alert["root_cause"],
                        alert["resolution"],
                    )
                    for alert in seed.historical_alerts
                ],
            )
            conn.executemany(
                """
                INSERT INTO recent_deployments
                (device_id, changed_at, change_type, summary, risk_hint)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        change["device_id"],
                        change["changed_at"],
                        change["change_type"],
                        change["summary"],
                        change["risk_hint"],
                    )
                    for change in seed.recent_deployments
                ],
            )

    def list_devices(self) -> list[Device]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
        return [Device(**dict(row)) for row in rows]

    def get_device(self, device_id: str) -> Device | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        return Device(**dict(row)) if row else None

    def upsert_device(self, device: Device) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO devices
                (device_id, name, device_type, location, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (device.device_id, device.name, device.device_type, device.location, device.status),
            )

    def add_metric_point(self, point: MetricPoint) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metric_points
                (device_id, timestamp, cpu_percent, memory_percent, disk_percent, heartbeat_ok)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    point.device_id,
                    point.timestamp.isoformat(),
                    point.cpu_percent,
                    point.memory_percent,
                    point.disk_percent,
                    int(point.heartbeat_ok),
                ),
            )

    def get_metric_window(self, device_id: str, minutes: int = 10) -> list[MetricPoint]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM metric_points
                WHERE device_id = ?
                ORDER BY timestamp
                """,
                (device_id,),
            ).fetchall()
        return [
            MetricPoint(
                row["device_id"],
                datetime.fromisoformat(row["timestamp"]),
                row["cpu_percent"],
                row["memory_percent"],
                bool(row["heartbeat_ok"]),
                row["disk_percent"],
            )
            for row in rows[-max(minutes, 1) :]
        ]

    def find_similar_alerts(self, device_id: str, alert_type: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT device_id, alert_type, root_cause, resolution
                FROM historical_alerts
                WHERE device_id = ? OR alert_type = ?
                ORDER BY id DESC
                """,
                (device_id, alert_type),
            ).fetchall()
        return [dict(row) for row in rows]

    def find_recent_deployments(self, device_id: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT device_id, changed_at, change_type, summary, risk_hint
                FROM recent_deployments
                WHERE device_id = ?
                ORDER BY changed_at DESC
                """,
                (device_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def detect_alerts(self) -> list[Alert]:
        latest_by_device: dict[str, MetricPoint] = {}
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM metric_points ORDER BY timestamp").fetchall()
        for row in rows:
            latest_by_device[row["device_id"]] = MetricPoint(
                row["device_id"],
                datetime.fromisoformat(row["timestamp"]),
                row["cpu_percent"],
                row["memory_percent"],
                bool(row["heartbeat_ok"]),
                row["disk_percent"],
            )

        return AlertRuleEngine().evaluate_latest(latest_by_device)

    def save_diagnosis_report(
        self,
        report: DiagnosisReport,
        trace: dict[str, Any],
        summary: dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO diagnosis_reports
                (run_id, alert_id, report_json, trace_json, summary_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.alert_id,
                    json.dumps(asdict(report), ensure_ascii=False, default=str),
                    json.dumps(trace, ensure_ascii=False, default=str),
                    json.dumps(summary, ensure_ascii=False, default=str),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def list_diagnosis_reports(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, alert_id, report_json, summary_json, created_at
                FROM diagnosis_reports
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "alert_id": row["alert_id"],
                "report": json.loads(row["report_json"]),
                "summary": json.loads(row["summary_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
