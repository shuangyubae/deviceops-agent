# DeviceOps Agent

This is a dependency-free local project for an observability-driven device operations diagnosis agent.

It demonstrates a production-oriented incident diagnosis loop:

1. Simulate device metrics and alert events.
2. Trigger rule-based alerts.
3. Let an incident agent plan diagnosis steps.
4. Call tools to collect evidence from metrics, device status, historical alerts, and runbooks.
5. Retrieve metadata-aware runbook evidence and cite the source.
6. Generate a diagnosis report with confidence, evidence, and suggested actions.
7. Refuse unknown diagnoses when no reliable runbook evidence is found.
8. Save a trace for each agent run.
9. Persist diagnosis reports in SQLite.
10. Expose a local HTTP API for integration.
11. Optionally use an OpenAI-compatible LLM provider for diagnosis plan refinement and report refinement, with deterministic fallback.

## Run

```powershell
python -m deviceops_agent.demo
```

Run the evaluation suite:

```powershell
python -m deviceops_agent.evaluation
```

Run the SQLite smoke test:

```powershell
python -m deviceops_agent.smoke
```

Start the local API:

```powershell
python -m deviceops_agent.api
```

Then open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/devices
http://127.0.0.1:8000/alerts
http://127.0.0.1:8000/diagnose
http://127.0.0.1:8000/evaluate
```

Run with Docker:

```powershell
docker compose up --build
```

## Why This Project Exists

The project focuses on a reliable incident diagnosis loop:

```text
alert -> plan -> tool calls -> evidence -> diagnosis -> trace -> evaluation
```

The current RAG path stays dependency-free on purpose:

```text
alert query -> metadata-aware runbook search -> citations -> diagnosis or refusal
```

The current implementation is dependency-free so it can run in constrained environments. It is designed so the adapters can later be replaced by:

- Spring Boot backend: devices, metrics, alerts, APIs
- Python / LangGraph agent service: planning, tool calling, RAG, diagnosis
- Prometheus / Grafana / OpenTelemetry: observability

## Docs

- `docs/architecture.md`
- `docs/api_contract.md`
- `docs/schema.sql`
- `docs/operations.md`

## Development

Run unit tests:

```powershell
python -m unittest discover -s tests
```

Package metadata is defined in `pyproject.toml`.

CI is defined in `.github/workflows/ci.yml`.

## Optional LLM Planning And Report Generation

By default, the project uses deterministic report generation. This keeps tests and CI independent of external services.

To enable an OpenAI-compatible LLM endpoint, set:

```text
DEVICEOPS_LLM_PROVIDER=openai-compatible
DEVICEOPS_LLM_BASE_URL=https://api.openai.com/v1
DEVICEOPS_LLM_API_KEY=<your-api-key>
DEVICEOPS_LLM_MODEL=<model-name>
```

When enabled, the LLM participates in two controlled steps:

1. Plan refinement: the LLM may adjust the diagnosis plan, but only with approved tools.
2. Report refinement: the LLM may rewrite the final report, but only with existing evidence and citations.

Invalid plans, unknown tools, failed requests, malformed JSON, or invalid citations fall back to the deterministic path.
