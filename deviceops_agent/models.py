from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Device:
    device_id: str
    name: str
    device_type: str
    location: str
    status: str


@dataclass(frozen=True)
class MetricPoint:
    device_id: str
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    heartbeat_ok: bool
    disk_percent: float = 0.0


@dataclass(frozen=True)
class Alert:
    alert_id: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    triggered_at: datetime
    metric_snapshot: MetricPoint


@dataclass(frozen=True)
class RunbookHit:
    source: str
    score: float
    snippet: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    data: Any
    error: str | None = None


@dataclass
class AgentStep:
    step_id: str
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    started_at: str
    ended_at: str
    latency_ms: float


@dataclass
class DiagnosisReport:
    run_id: str
    alert_id: str
    diagnosis_plan: list[dict[str, str]]
    root_cause: str
    confidence: float
    risk_level: str
    evidence: list[str]
    suggested_actions: list[str]
    citations: list[str]
    refusal_reason: str | None = None
    trace_path: str | None = None
    planning_provider: str = "deterministic"
    generation_provider: str = "deterministic"


@dataclass
class AgentTrace:
    run_id: str = field(default_factory=lambda: f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}")
    steps: list[AgentStep] = field(default_factory=list)
