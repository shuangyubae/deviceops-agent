FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY deviceops_agent ./deviceops_agent
COPY data/runbooks ./data/runbooks
COPY docs ./docs

RUN pip install --no-cache-dir .

ENV DEVICEOPS_API_HOST=0.0.0.0
ENV DEVICEOPS_API_PORT=8000
ENV DEVICEOPS_REPOSITORY=sqlite
ENV DEVICEOPS_SQLITE_PATH=/app/data/deviceops.sqlite
ENV DEVICEOPS_RUNBOOK_DIR=/app/data/runbooks
ENV DEVICEOPS_TRACE_DIR=/app/data/traces
ENV DEVICEOPS_LLM_PROVIDER=deterministic

EXPOSE 8000

CMD ["deviceops-agent-api"]
