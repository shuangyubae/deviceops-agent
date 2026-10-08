from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .models import AgentStep, AgentTrace


class TraceRecorder:
    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def record_step(
        self,
        trace: AgentTrace,
        name: str,
        input_data: dict[str, Any],
        fn: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        started = datetime.now().isoformat(timespec="seconds")
        started_perf = perf_counter()
        output = fn()
        latency_ms = round((perf_counter() - started_perf) * 1000, 2)
        ended = datetime.now().isoformat(timespec="seconds")
        trace.steps.append(
            AgentStep(
                step_id=f"step-{len(trace.steps) + 1}",
                name=name,
                input=input_data,
                output=output,
                started_at=started,
                ended_at=ended,
                latency_ms=latency_ms,
            )
        )
        return output

    def save(self, trace: AgentTrace) -> Path:
        path = self.trace_dir / f"{trace.run_id}.json"
        path.write_text(json.dumps(asdict(trace), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    @staticmethod
    def summarize(trace: AgentTrace) -> dict[str, Any]:
        total_latency_ms = round(sum(step.latency_ms for step in trace.steps), 2)
        return {
            "run_id": trace.run_id,
            "step_count": len(trace.steps),
            "total_latency_ms": total_latency_ms,
            "steps": [
                {"step_id": step.step_id, "name": step.name, "latency_ms": step.latency_ms}
                for step in trace.steps
            ],
        }
