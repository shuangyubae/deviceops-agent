# DeviceOps Agent Architecture

## Architecture

```text
Device metrics
    |
    v
Metric ingestion API
    |
    v
Rule-based alert detection
    |
    v
IncidentAgentOrchestrator
    |
    +--> optional LLM plan refinement
    |
    +--> query_device_status
    +--> query_metric_window
    +--> query_similar_alerts
    +--> query_recent_deployments
    +--> search_runbook
    |
    v
Evidence chain + confidence scoring
    |
    v
Optional LLM report refinement
    |
    v
DiagnosisReport
    |
    +--> JSON trace
    +--> SQLite persistence
    +--> HTTP API
    +--> Evaluation suite
```

## Design Choices

### Rule Engine Triggers Alerts

The project keeps alert triggering deterministic. CPU, memory, disk, and heartbeat thresholds are handled by code rather than by an LLM.

The rule engine is isolated in `deviceops_agent/rules.py`, while repositories only handle persistence and retrieval.

### Agent Diagnoses Alerts

The Agent starts after an alert exists. It plans which tools to call, collects evidence, retrieves runbooks, calculates confidence, and produces a report.

### RAG Controls Hallucination

Runbooks are treated as approved operational knowledge. If no reliable runbook is retrieved, the Agent refuses to produce a confident diagnosis.

### SQLite Is the Local Delivery Store

The project uses SQLite for a runnable local version. The schema maps directly to MySQL tables for a Spring Boot backend.

### LLM Integration Point

The project uses deterministic planning and report generation for stable local evaluation and CI. A real LLM can be enabled as an optional OpenAI-compatible provider in two places:

```text
alert context + allowed tools + draft plan -> LLM -> validated plan -> fallback if invalid
evidence + citations + draft report -> LLM -> validated structured report -> fallback if invalid
```

The rule engine, tool whitelist, evidence chain, confidence scoring, citations, refusal logic, trace, and evaluation remain active even when a real LLM is enabled.
