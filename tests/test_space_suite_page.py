"""Publication boundaries: declared cases, local-only data and frozen media."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "space_page", ROOT / "scripts/build_space_suite_page.py"
)
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpaceSuitePageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        report = self.directory / "report"
        report.mkdir()
        (report / "summary.json").write_text('{"experiment_sha256": "frozen"}')
        self.media = report / "cloud.json"
        self.media.write_text('{"surface": [], "edges": [], "path": []}')
        self.receipt = self.directory / "receipt.json"
        self.receipt.write_text(
            json.dumps(
                {
                    "output_sha256": {
                        "report/summary.json": sha256(report / "summary.json")
                    }
                }
            )
        )
        self.case = {
            "id": "test_case",
            "status": "complete",
            "evaluated": True,
            "receipt_sha256": sha256(self.receipt),
            "available_artifacts": ["cloud.json"],
            "media_sha256": {"cloud.json": sha256(self.media)},
            "provenance": {"experiment_sha256": "frozen"},
        }

    def test_unchanged_media_verifies(self):
        self.assertEqual(
            page.verify_case_media(self.case, self.directory), [self.media]
        )

    def test_stale_receipt_rejected(self):
        self.receipt.write_text('{"output_sha256": {}}')
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            page.verify_case_media(self.case, self.directory)

    def test_changed_receipted_artifact_rejected(self):
        (self.directory / "report/summary.json").write_text(
            '{"experiment_sha256": "new"}'
        )
        with self.assertRaisesRegex(ValueError, "differs from its receipt"):
            page.verify_case_media(self.case, self.directory)

    def test_media_not_in_runner_receipt_still_checked(self):
        self.media.write_text('{"surface": [[1, 2, 3]]}')
        with self.assertRaisesRegex(ValueError, "media changed after aggregation"):
            page.verify_case_media(self.case, self.directory)

    def test_public_whitelist_omits_local_paths_and_frame_traces(self):
        source = {
            "schema_version": 1,
            "name": "suite",
            "status": "complete",
            "suite_sha256": "suite",
            "frozen_suite_sha256": "frozen",
            "shared_budget": {},
            "aggregate": {"declared_buildings": 1},
            "limitations": [],
            "local_root": "/private/workspace",
            "cases": [
                {
                    **self.case,
                    "directory": "/private/workspace/case",
                    "trace": ["large raw data"],
                    "visibility_curve": [1, 2, 3],
                }
            ],
        }
        public = page.compact_summary(source)
        self.assertNotIn("local_root", public)
        self.assertNotIn("directory", public["cases"][0])
        self.assertNotIn("trace", public["cases"][0])
        self.assertNotIn("visibility_curve", public["cases"][0])
        self.assertEqual(public["cases"][0]["provenance"], self.case["provenance"])

    def test_partial_suite_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, "terminal suite"):
            page.compact_summary({"status": "partial"})


if __name__ == "__main__":
    unittest.main()
