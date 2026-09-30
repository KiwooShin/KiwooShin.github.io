"""Publication boundaries: declared cases, local-only data and frozen media."""

import copy
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


class PolicyComparisonPageTests(unittest.TestCase):
    def setUp(self):
        measured = {key: 0.5 for key in page.METRICS}
        baseline = {
            "id": "example",
            "title": "Example",
            "split": "development",
            "status": "complete",
            "evaluated": True,
            "metrics": measured,
            "visits": {"rooms_entered": 4},
            "frames": 300,
            "path_length_m": 24,
            "action_seconds": 900,
            "wall_seconds": 300,
            "provenance": {"experiment_sha256": "frozen"},
        }
        self.summary = {"cases": [baseline], "shared_budget": {"max_frames": 300}}
        readout = {
            **measured,
            "status": "complete",
            "evaluated": True,
            "rooms_entered": 4,
            "reference_room_count": 4,
            "frames": 300,
            "path_length_m": 24,
            "action_seconds": 900,
            "wall_seconds": 300,
            "stop_reason": "frame_budget",
            "provenance": {"experiment_sha256": "frozen"},
            "unentered_reference_rooms": [],
            "available_artifacts": [],
            "diagnostics": {},
        }
        candidate = {
            **readout,
            "rooms_entered": 3,
            "unentered_reference_rooms": ["study"],
        }
        keys = (
            "rooms_entered",
            "visible_edge_coverage",
            "edge_completeness_10cm",
            "edge_precision_10cm",
            "path_length_m",
            "action_seconds",
            "wall_seconds",
            "frames",
        )
        self.comparison = {
            "schema_version": 1,
            "comparison": "v1_vs_v2",
            "status": "complete",
            "qualification": "Tuned development comparison; not held-out generalization.",
            "provenance": {},
            "shared_budget": {"max_frames": 300},
            "diagnostic_protocol": {},
            "limitations": [],
            "media_sha256": {},
            "cases": [
                {
                    "id": "example",
                    "title": "Example",
                    "split": "development",
                    "baseline": readout,
                    "candidate": candidate,
                    "delta": {key: candidate[key] - readout[key] for key in keys},
                }
            ],
            "macro": {
                key: {
                    "baseline": readout[key],
                    "candidate": candidate[key],
                    "delta": candidate[key] - readout[key],
                    "denominator_buildings": 1,
                    "case_ids": ["example"],
                }
                for key in keys
            },
        }

    def test_comparison_preserves_regression_and_missing_room(self):
        section = page.policy_comparison_section(self.comparison)
        self.assertIn("-1.0", section)
        self.assertIn("study", section)
        self.assertIn("not held-out", section)
        self.assertIn('href="#example"', section)
        self.assertIn("policy-v2/paired_metrics.png", section)

    def test_candidate_map_options_preserve_baseline_ids_and_own_media(self):
        self.summary["cases"][0]["available_artifacts"] = ["cloud.json"]
        self.comparison["cases"][0]["candidate"]["available_artifacts"] = ["cloud.json"]
        options = page.map_options(self.summary, self.comparison)
        self.assertIn('value="example"', options)
        self.assertIn('value="v2_example"', options)
        self.assertIn(
            'data-cloud="../media/roomgraph-spaces/example/cloud.json"', options
        )
        self.assertIn(
            'data-cloud="../media/roomgraph-spaces/policy-v2/example/cloud.json"',
            options,
        )
        self.assertIn(
            'data-case="v2_example"', page.policy_comparison_section(self.comparison)
        )

    def test_absent_comparison_adds_no_placeholder_metrics(self):
        self.assertEqual(page.policy_comparison_section(None), "")

    def test_other_baseline_and_changed_delta_are_rejected(self):
        changed = copy.deepcopy(self.comparison)
        changed["cases"][0]["baseline"]["provenance"]["experiment_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "another baseline"):
            page.verify_comparison_baseline(changed, self.summary)
        changed = copy.deepcopy(self.comparison)
        changed["cases"][0]["delta"]["rooms_entered"] = 1
        with self.assertRaisesRegex(ValueError, "delta differs"):
            page.verify_comparison_baseline(changed, self.summary)

    def test_invented_macro_or_denominator_rejected(self):
        page.verify_comparison_baseline(self.comparison, self.summary)
        changed = copy.deepcopy(self.comparison)
        changed["macro"]["rooms_entered"]["candidate"] = 99
        with self.assertRaisesRegex(ValueError, "macro measurement"):
            page.verify_comparison_baseline(changed, self.summary)
        changed = copy.deepcopy(self.comparison)
        changed["macro"]["rooms_entered"]["denominator_buildings"] = 99
        with self.assertRaisesRegex(ValueError, "macro denominator"):
            page.verify_comparison_baseline(changed, self.summary)

    def test_case_dropped_from_comparison_is_rejected(self):
        changed = copy.deepcopy(self.comparison)
        changed["cases"] = []
        with self.assertRaisesRegex(ValueError, "exactly the published"):
            page.verify_comparison_baseline(changed, self.summary)

    def test_raw_data_and_private_paths_are_not_published(self):
        source = copy.deepcopy(self.comparison)
        source["private_root"] = "/private/data"
        source["cases"][0]["candidate"]["trace"] = [{"rgb": "/private/data/rgb.png"}]
        self.assertNotIn("/private", str(page.compact_comparison(source)))
        self.assertNotIn("trace", str(page.compact_comparison(source)))


if __name__ == "__main__":
    unittest.main()
