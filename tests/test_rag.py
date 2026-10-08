from __future__ import annotations

import unittest
from pathlib import Path

from deviceops_agent.rag import RunbookRetriever


class RunbookRetrieverTest(unittest.TestCase):
    def setUp(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.retriever = RunbookRetriever(project_root / "data" / "runbooks")

    def test_alert_type_metadata_boosts_expected_runbook(self) -> None:
        hits = self.retriever.search("DISK_HIGH Disk usage is above threshold.")

        self.assertGreater(len(hits), 0)
        self.assertEqual("disk_high.md", hits[0].source)

    def test_unknown_query_does_not_match_weak_generic_terms(self) -> None:
        hits = self.retriever.search("UNKNOWN_SENSOR_DRIFT Unknown sensor drift alert has no approved runbook.")

        self.assertEqual([], hits)


if __name__ == "__main__":
    unittest.main()
