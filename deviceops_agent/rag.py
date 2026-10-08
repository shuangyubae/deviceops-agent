from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import RunbookHit


@dataclass(frozen=True)
class RunbookDocument:
    source: str
    title: str
    metadata: dict[str, str | list[str]]
    body: str


class RunbookRetriever:
    """Small metadata-aware keyword retriever for runbooks.

    This intentionally avoids vector database dependencies in the MVP. Later, it can
    be replaced with hybrid retrieval: BM25 + embedding search + rerank.
    """

    def __init__(self, runbook_dir: Path) -> None:
        self.runbook_dir = runbook_dir

    def search(self, query: str, top_k: int = 3) -> list[RunbookHit]:
        query_terms = {
            term.lower()
            for term in query.replace("_", " ").split()
            if len(term) > 2 and term.lower() not in self._stop_words()
        }
        hits: list[RunbookHit] = []
        for path in self.runbook_dir.glob("*.md"):
            document = self._load_document(path)
            score = self._score_document(document, query, query_terms)
            if score < 2:
                continue
            snippet = self._make_snippet(document.body, query_terms)
            hits.append(RunbookHit(path.name, float(score), snippet, document.metadata))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]

    @staticmethod
    def _stop_words() -> set[str]:
        return {
            "alert",
            "approved",
            "device",
            "has",
            "high",
            "missing",
            "runbook",
            "threshold",
            "usage",
            "warning",
        }

    @staticmethod
    def _load_document(path: Path) -> RunbookDocument:
        text = path.read_text(encoding="utf-8")
        metadata: dict[str, str | list[str]] = {}
        body = text

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                metadata = RunbookRetriever._parse_front_matter(parts[1])
                body = parts[2].strip()

        title = path.stem
        for line in body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return RunbookDocument(path.name, title, metadata, body)

    @staticmethod
    def _parse_front_matter(raw_metadata: str) -> dict[str, str | list[str]]:
        metadata: dict[str, str | list[str]] = {}
        for line in raw_metadata.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            cleaned_key = key.strip()
            cleaned_value = value.strip()
            if cleaned_key == "tags":
                metadata[cleaned_key] = [item.strip() for item in cleaned_value.split(",") if item.strip()]
            else:
                metadata[cleaned_key] = cleaned_value
        return metadata

    @staticmethod
    def _score_document(document: RunbookDocument, query: str, query_terms: set[str]) -> float:
        score = 0.0
        lower_query = query.lower()
        title = document.title.lower()
        body = document.body.lower()
        alert_type = str(document.metadata.get("alert_type", "")).lower()
        severity = str(document.metadata.get("severity", "")).lower()
        tags = [tag.lower() for tag in document.metadata.get("tags", [])]

        if alert_type and alert_type in lower_query:
            score += 8.0
        if severity and severity in lower_query:
            score += 1.0

        for term in query_terms:
            if term in title:
                score += 3.0
            if term in tags:
                score += 2.0
            if term in body:
                score += min(body.count(term), 3) * 0.5

        return score

    @staticmethod
    def _make_snippet(text: str, query_terms: set[str]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content_lines = [line for line in lines if not line.startswith("#")]
        for line in content_lines:
            if any(term in line.lower() for term in query_terms):
                return line[:240]
        return " ".join(content_lines or lines)[:240]
