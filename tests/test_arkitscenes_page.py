"""Publication refuses stale or unqualified real-pilot measurements."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "real_publisher",
    Path(__file__).resolve().parents[1] / "scripts/build_arkitscenes_page.py",
)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class RealPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"
        (self.run / "report").mkdir(parents=True)
        (self.run / "manifest.json").write_text("{}")
        summary = {
            "status": "complete",
            "manifest_sha256": publisher.digest(self.run / "manifest.json"),
            "results": [
                {
                    "variant": "nominal",
                    "fusion": "all_valid",
                    "surface_metrics": {
                        "precision_10cm": 0.8,
                        "recall_10cm": 0.8,
                        "f1_10cm": 0.8,
                    },
                }
            ],
        }
        (self.run / "summary.json").write_text(json.dumps(summary))
        (self.run / "replay_check.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "manifest_sha256": summary["manifest_sha256"],
                    "summary_sha256": publisher.digest(self.run / "summary.json"),
                }
            )
        )
        (self.run / "report/report.html").write_text(
            "<main>80.00% not architectural-edge accuracy</main>"
        )

    def test_success_and_explicit_scope(self):
        self.assertEqual(publisher.validate(self.run)[0]["status"], "complete")
        (self.run / "report/report.html").write_text("80.00%")
        with self.assertRaisesRegex(ValueError, "scope"):
            publisher.validate(self.run)

    def test_changed_manifest_and_measurements_are_rejected(self):
        (self.run / "manifest.json").write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError, "manifest"):
            publisher.validate(self.run)
        (self.run / "manifest.json").write_text("{}")
        summary = json.loads((self.run / "summary.json").read_text())
        summary["extra"] = True
        (self.run / "summary.json").write_text(json.dumps(summary))
        with self.assertRaisesRegex(ValueError, "measurements"):
            publisher.validate(self.run)

    def test_stale_report_scores_rejected(self):
        (self.run / "report/report.html").write_text(
            "70.00% not architectural-edge accuracy"
        )
        with self.assertRaisesRegex(ValueError, "scores"):
            publisher.validate(self.run)

    def test_publication_copies_only_selected_assets(self):
        for name in publisher.ASSETS:
            (self.run / "report" / name).write_bytes(b"fixture")
        (self.run / "report/private.npz").write_bytes(b"private")
        license_path = self.root / "LICENSE"
        license_path.write_text("dataset attribution")
        destination = self.root / "published"
        publisher.build(self.run, destination, license_path)
        self.assertFalse((destination / "private.npz").exists())
        self.assertEqual(
            (destination / "dataset-license.txt").read_text().strip(), "dataset attribution"
        )
        self.assertIn("../roomgraph-spaces/", (destination / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
