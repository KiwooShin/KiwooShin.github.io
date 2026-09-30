"""Publish selected qualitative preprocessing comparisons, without private review labels."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(run):
    summary = json.loads((run / "summary.json").read_text())
    if summary["status"] != "complete" or summary["threshold"] != 0.7:
        raise ValueError("Expected completed frozen-threshold diagnostic")
    if (
        summary["metrics_status"]
        != "No verified real edge labels. Coverage is NOT accuracy."
    ):
        raise ValueError("Missing accuracy qualification")
    destination = ROOT / "roomgraph-real/preprocessing"
    destination.mkdir(parents=True, exist_ok=True)
    images = sorted(run.glob("comparison_*.jpg"))
    if len(images) != 8:
        raise ValueError("Expected eight preselected comparisons")
    hashes = {}
    for path in images:
        shutil.copyfile(path, destination / path.name)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary.pop("records")
    summary["source_sha256"] = {
        Path(k).name: v for k, v in summary["source_sha256"].items()
    }
    summary["publication"] = {
        "summary_sha256": hashlib.sha256(
            (run / "summary.json").read_bytes()
        ).hexdigest(),
        "image_sha256": hashes,
    }
    (destination / "measurements.json").write_text(json.dumps(summary, indent=2) + "\n")
    rows = "".join(
        f'<img src="{p.name}" alt="Original and five edge preprocessing alternatives">'
        for p in images
    )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>RoomGraph · Real edge preprocessing</title><style>"
        "body{background:#101820;color:#edf2f7;font:17px system-ui;margin:24px;line-height:1.6}"
        "main{max-width:1200px;margin:auto}img{width:100%;display:block;margin:24px 0}"
        "a{color:#67e8c3}p{max-width:900px}</style><main>"
        '<nav><a href="../../">Kiwoo Shin</a> · '
        '<a href="../">Real RGB-D reconstruction project</a></nav>'
        "<h1>Can better camera preprocessing recover real structural edges?</h1>"
        "<p>We kept the synthetic-trained model and threshold fixed, and compared five "
        "input strategies on 240 ARKitScenes views. The 640 × 480 wide-camera stream "
        "provided 121 exact timestamp matches. All overlays use the same upright "
        "192 × 256 image coordinates.</p>"
        "<p>Columns: original RGB, stretched input, letterboxed input, native portrait, "
        "larger portrait from low-resolution RGB, and larger portrait from VGA RGB. "
        "Green marks predicted visible structural edges. All eight illustrated views "
        "are evenly spaced among the matched frames.</p>"
        "<p><strong>Result: mixed, still incomplete.</strong> Preserving aspect ratio "
        "changes which edges are recovered, but substantial wall and opening boundaries "
        "remain missing. Higher resolution does not consistently fix this. No default "
        "was changed. These comparisons do not establish improved accuracy.</p>"
        + rows
        + "<h2>Efficiency and evaluation limits</h2>"
        f"<p>The complete cached comparison took {summary['wall_seconds']:.2f} seconds "
        f"with {summary['peak_tensor_memory_mib']:.2f} MiB peak allocated tensor memory. "
        "Download time is excluded. Individual timings are fixed-order diagnostics, "
        "not an isolated speedup benchmark.</p>"
        "<p>Eight local review frames have provisional AI-drafted region annotations. "
        "Independent human review remains pending; no real structural-edge F1 is "
        "reported and no real-data fine-tuning has been performed. All views belong "
        "to one development visit, not a held-out generalization test. "
        "Surface reconstruction F1 from the earlier experiment is a different metric.</p>"
        '<p><a href="measurements.json">Measurements and artifact hashes</a> · '
        '<a href="../dataset-license.txt">Dataset license</a></p></main></html>'
    )
    (destination / "index.html").write_text(page)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        default=ROOT.parent / "roomgraph/vis/arkitscenes/preprocessing_v2",
    )
    build(parser.parse_args().run)
