# Operations

## Runtime Configuration

The service reads configuration from environment variables:

```text
DEVICEOPS_REPOSITORY=sqlite
DEVICEOPS_SQLITE_PATH=data/deviceops.sqlite
DEVICEOPS_RUNBOOK_DIR=data/runbooks
DEVICEOPS_TRACE_DIR=data/traces
DEVICEOPS_API_HOST=127.0.0.1
DEVICEOPS_API_PORT=8000
DEVICEOPS_LLM_PROVIDER=deterministic
DEVICEOPS_LLM_BASE_URL=https://api.openai.com/v1
DEVICEOPS_LLM_API_KEY=
DEVICEOPS_LLM_MODEL=gpt-4o-mini
DEVICEOPS_LLM_TIMEOUT_SECONDS=15
```

## Local Runbook Store

Runbooks are Markdown files under `data/runbooks`. Each file should include metadata:

```text
---
alert_type: DISK_HIGH
severity: warning
tags: disk, logs, cache, retention, storage
---
```

The retriever uses alert type, severity, tags, title, and body text to rank results.

## Data Persistence

SQLite is used for local persistence:

- device inventory
- metric points
- historical alerts
- recent deployments
- diagnosis reports
- trace summaries

Generated runtime files are intentionally ignored by Git:

- `data/*.sqlite`
- `data/traces/*.json`

## Health Checks

Start the API:

```powershell
python -m deviceops_agent.api
```

Run with Docker Compose:

```powershell
docker compose up --build
```

Check:

```text
GET /health
GET /metrics
GET /evaluate
```

## Ingesting Telemetry

Register a device:

```text
POST /devices
```

Send a metric point:

```text
POST /metric-points
```

If the latest metric crosses a rule threshold, the response includes the active alert for that device.

## Safety Model

The current agent is diagnostic-only. It does not restart services, delete files, roll back deployments, or execute remediation actions. Suggested actions are recommendations that require human approval.

## Optional LLM Provider

The default provider is deterministic, so the service, tests, CI, and local demos do not require external network access or API keys.

To enable an OpenAI-compatible chat completion endpoint:

```text
DEVICEOPS_LLM_PROVIDER=openai-compatible
DEVICEOPS_LLM_BASE_URL=https://api.openai.com/v1
DEVICEOPS_LLM_API_KEY=<your-api-key>
DEVICEOPS_LLM_MODEL=<model-name>
```

The LLM is used in two controlled places:

- plan refinement: it can propose a diagnosis plan, but only using approved tools
- report refinement: it can generate the final report, but only using existing evidence and citations

If the LLM call fails, uses an unapproved tool, returns malformed JSON, or cites a source that was not retrieved, the system falls back to the deterministic path.
