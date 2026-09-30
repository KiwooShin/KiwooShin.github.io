"""Publish selected artifacts from a completed and replay-verified real RGB-D pilot."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("overview.jpg", "poster.jpg", "replay.mp4", "sensitivity.png")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(run):
    summary = json.loads((run / "summary.json").read_text())
    replay = json.loads((run / "replay_check.json").read_text())
    if summary["status"] != "complete" or replay["status"] != "pass":
        raise ValueError("Completed experiment and successful replay required")
    if summary["manifest_sha256"] != digest(run / "manifest.json"):
        raise ValueError("Changed experiment manifest")
    if replay["summary_sha256"] != digest(run / "summary.json"):
        raise ValueError("Replay does not match measurements")
    if replay["manifest_sha256"] != summary["manifest_sha256"]:
        raise ValueError("Replay does not match inputs")
    page = (run / "report/report.html").read_text()
    if "not architectural-edge accuracy" not in page:
        raise ValueError("Surface-metric scope must remain explicit")
    groups = {}
    for result in summary["results"]:
        groups.setdefault((result["variant"], result["fusion"]), []).append(result)
    for values in groups.values():
        for key in ("precision_10cm", "recall_10cm", "f1_10cm"):
            mean = sum(r["surface_metrics"][key] for r in values) / len(values)
            if f"{mean * 100:.2f}%" not in page:
                raise ValueError("Report lacks measured surface scores")
    return summary, page


def build(run, output, license_path):
    summary, page = validate(run)
    source_hashes = {name: digest(run / "report" / name) for name in ASSETS}
    source_hashes["report.html"] = digest(run / "report/report.html")
    output.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copy2(run / "report" / name, output / name)
    (output / "dataset-license.txt").write_text(license_path.read_text().rstrip() + "\n")
    page = page.replace(
        "<main>",
        '<main><nav><a href="../">Kiwoo Shin</a> · <a href="../roomgraph-spaces/">Synthetic experiments</a></nav>',
        1,
    )
    page = page.replace(
        "</main>",
        '<p><a href="measurements.json">Measurements and publication provenance</a> · <a href="dataset-license.txt">Retained dataset license</a></p></main>',
        1,
    )
    (output / "index.html").write_text(page)
    public = {
        **summary,
        "publication": {
            "summary_sha256": digest(run / "summary.json"),
            "replay_check_sha256": digest(run / "replay_check.json"),
            "selected_source_sha256": source_hashes,
        },
    }
    (output / "measurements.json").write_text(json.dumps(public, indent=2) + "\n")
    print(f"Published selected real-data pilot to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", type=Path, default=ROOT.parent / "roomgraph/vis/arkitscenes/pilot_v2"
    )
    parser.add_argument(
        "--license",
        type=Path,
        default=ROOT.parent
        / "roomgraph/artifacts/real/arkitscenes/Validation/42445021/LICENSE",
    )
    args = parser.parse_args()
    build(args.run, ROOT / "roomgraph-real", args.license)


if __name__ == "__main__":
    main()
