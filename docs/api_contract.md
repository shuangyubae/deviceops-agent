# API Contract

Base URL:

```text
http://127.0.0.1:8000
```

Start service:

```powershell
python -m deviceops_agent.api
```

## GET /health

Returns service health.

Response includes the active repository kind and LLM provider:

```json
{
  "status": "ok",
  "service": "deviceops-agent",
  "llm_provider": "deterministic",
  "repository": "sqlite"
}
```

Diagnosis reports include:

- `planning_provider`: which provider produced the executable diagnosis plan
- `generation_provider`: which provider produced the final diagnosis report

## GET /devices

Returns all known devices.

## POST /devices

Registers or updates a device:

```json
{
  "device_id": "device-05",
  "name": "Edge Gateway E",
  "device_type": "edge_gateway",
  "location": "factory-c",
  "status": "online"
}
```

## POST /metric-points

Ingests one metric point. The service stores the metric and returns the active alert for that device if the latest point crosses a rule threshold.

```json
{
  "device_id": "device-05",
  "cpu_percent": 95,
  "memory_percent": 45,
  "disk_percent": 50,
  "heartbeat_ok": true
}
```

## GET /alerts

Runs rule-based alert detection and returns active alerts.

## GET /diagnose?alert_id=alert-device-01-cpu

Diagnoses one alert. If `alert_id` is omitted, the first active alert is diagnosed.

## POST /diagnose

Diagnoses one alert by JSON body:

```json
{
  "alert_id": "alert-device-04-disk"
}
```

## GET /reports

Returns diagnosis reports persisted in SQLite.

## GET /evaluate

Runs the automated evaluation suite.

## GET /metrics

Returns lightweight service metrics:

- persisted report count
- latest agent run summaries
- step latency summaries
