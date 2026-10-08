from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent import IncidentAgentOrchestrator
from .config import AppConfig, load_config
from .llm import LLMProvider, build_llm_provider
from .repository import InMemoryRepository
from .sqlite_repository import SQLiteRepository
from .tools import DeviceOpsTools
from .trace import TraceRecorder


@dataclass
class AgentRuntime:
    config: AppConfig
    project_root: Path
    repository: object
    tools: DeviceOpsTools
    traces: TraceRecorder
    llm_provider: LLMProvider
    agent: IncidentAgentOrchestrator


def build_runtime(repository_kind: str = "sqlite") -> AgentRuntime:
    config = load_config(repository_kind)
    if config.repository_kind == "memory":
        repository = InMemoryRepository()
    else:
        repository = SQLiteRepository(config.sqlite_path)

    tools = DeviceOpsTools(repository, config.runbook_dir)
    traces = TraceRecorder(config.trace_dir)
    llm_provider = build_llm_provider(config)
    agent = IncidentAgentOrchestrator(tools, traces, llm_provider)
    return AgentRuntime(config, config.project_root, repository, tools, traces, llm_provider, agent)
