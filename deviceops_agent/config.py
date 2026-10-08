from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    repository_kind: str
    sqlite_path: Path
    runbook_dir: Path
    trace_dir: Path
    api_host: str
    api_port: int
    llm_provider: str
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    llm_timeout_seconds: float


def load_config(repository_kind: str | None = None) -> AppConfig:
    project_root = Path(__file__).resolve().parents[1]
    selected_repository = repository_kind or os.getenv("DEVICEOPS_REPOSITORY", "sqlite")
    sqlite_path = Path(os.getenv("DEVICEOPS_SQLITE_PATH", project_root / "data" / "deviceops.sqlite"))
    runbook_dir = Path(os.getenv("DEVICEOPS_RUNBOOK_DIR", project_root / "data" / "runbooks"))
    trace_dir = Path(os.getenv("DEVICEOPS_TRACE_DIR", project_root / "data" / "traces"))
    api_host = os.getenv("DEVICEOPS_API_HOST", "127.0.0.1")
    api_port = int(os.getenv("DEVICEOPS_API_PORT", "8000"))
    llm_provider = os.getenv("DEVICEOPS_LLM_PROVIDER", "deterministic")
    llm_base_url = os.getenv("DEVICEOPS_LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key = os.getenv("DEVICEOPS_LLM_API_KEY")
    llm_model = os.getenv("DEVICEOPS_LLM_MODEL", "gpt-4o-mini")
    llm_timeout_seconds = float(os.getenv("DEVICEOPS_LLM_TIMEOUT_SECONDS", "15"))
    return AppConfig(
        project_root=project_root,
        repository_kind=selected_repository,
        sqlite_path=sqlite_path,
        runbook_dir=runbook_dir,
        trace_dir=trace_dir,
        api_host=api_host,
        api_port=api_port,
        llm_provider=llm_provider,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )
