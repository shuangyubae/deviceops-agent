from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceBreakdown:
    base: float
    device_context: float = 0.0
    metric_trend: float = 0.0
    historical_incidents: float = 0.0
    recent_changes: float = 0.0
    runbook_evidence: float = 0.0
    tool_penalty: float = 0.0

    @property
    def total(self) -> float:
        score = (
            self.base
            + self.device_context
            + self.metric_trend
            + self.historical_incidents
            + self.recent_changes
            + self.runbook_evidence
            - self.tool_penalty
        )
        return round(max(0.0, min(score, 0.95)), 2)

    def as_evidence(self) -> str:
        return (
            "Confidence breakdown: "
            f"base={self.base}, device={self.device_context}, metrics={self.metric_trend}, "
            f"history={self.historical_incidents}, changes={self.recent_changes}, "
            f"runbook={self.runbook_evidence}, penalty={self.tool_penalty}."
        )


def calculate_confidence(
    *,
    has_device_context: bool,
    has_metric_trend: bool,
    has_historical_incidents: bool,
    has_recent_changes: bool,
    has_runbook_evidence: bool,
    failed_tool_count: int = 0,
) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        base=0.35,
        device_context=0.1 if has_device_context else 0.0,
        metric_trend=0.2 if has_metric_trend else 0.0,
        historical_incidents=0.15 if has_historical_incidents else 0.0,
        recent_changes=0.1 if has_recent_changes else 0.0,
        runbook_evidence=0.2 if has_runbook_evidence else 0.0,
        tool_penalty=0.05 * failed_tool_count,
    )
