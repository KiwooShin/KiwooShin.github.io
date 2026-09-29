"""Publish selected measured multi-space media, retaining incomplete and failed cases."""

import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media/roomgraph-spaces"
CASE_FIELDS = (
    "id",
    "title",
    "description",
    "visual_audit",
    "split",
    "status",
    "stage",
    "evaluated",
    "available_artifacts",
    "media_sha256",
    "receipt_sha256",
    "full_pipeline_wall_seconds",
    "experiment_status",
    "reference_edge_length_m",
    "reference_portal_count",
    "unentered_reference_rooms",
    "predicted_edge_voxels",
    "metrics",
    "frames",
    "stations",
    "path_length_m",
    "action_seconds",
    "wall_seconds",
    "stop_reason",
    "visits",
    "all_reference_rooms_entered",
    "path_audit",
    "timings",
    "per_region",
    "provenance",
)
METRICS = (
    "visible_edge_coverage",
    "edge_precision_10cm",
    "edge_completeness_10cm",
    "typed_edge_precision_10cm",
    "typed_edge_completeness_10cm",
)


def percent(value):
    return "—" if value is None else f"{value:.1%}"


def compact_summary(source):
    if source.get("status") != "complete":
        raise ValueError(
            "Publish only a terminal suite with every declared case retained"
        )
    if source["aggregate"]["declared_buildings"] != len(source["cases"]):
        raise ValueError("Suite declaration and report rows disagree")
    result = {
        key: source[key]
        for key in (
            "schema_version",
            "name",
            "status",
            "suite_sha256",
            "frozen_suite_sha256",
            "shared_budget",
            "aggregate",
            "limitations",
        )
    }
    result["cases"] = [
        {key: case[key] for key in CASE_FIELDS if key in case}
        for case in source["cases"]
    ]
    return result


def copy_artifact(source, destination, hashes):
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    hashes[str(destination.relative_to(MEDIA))] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()


def case_card(case):
    title, description = html.escape(case["title"]), html.escape(case["description"])
    if not case["evaluated"]:
        return f'<article class="case"><h3>{title}</h3><p>{description}</p><p>Case status: {html.escape(case["status"])}. No completed evaluation is available; this case remains in the declared suite.</p></article>'
    metrics, visits = case["metrics"], case["visits"]
    missing_rooms = visits["reference_room_count"] - visits["rooms_entered"]
    outcome = (
        f"{missing_rooms} reference rooms remained unentered when this run stopped. Doorway sightlines can still reveal some edges there; high visibility does not imply full exploration."
        if missing_rooms
        else "Every reference room was entered; geometric reconstruction still remains partial."
    )
    prefix = f"../media/roomgraph-spaces/{case['id']}"
    audit = case["path_audit"]
    entry = " → ".join(
        html.escape(item.replace("_", " ")) for item in visits["region_entry_order"]
    )
    safe = (
        "All audited moves remained in observed safe cells."
        if audit["all_motions_in_observed_safe_map"]
        else "Some audited moves left observed safe cells."
    )
    audit_findings = (case.get("visual_audit") or {}).get("findings", [])
    scene_note = (
        '<p class="caption"><strong>Scene quality:</strong> '
        + " ".join(html.escape(item) for item in audit_findings)
        + "</p>"
        if audit_findings
        else ""
    )
    full_seconds = case.get("full_pipeline_wall_seconds")
    full_timing = (
        f"Full pipeline including renderer startup, evaluation and media export: {full_seconds:.1f} s."
        if full_seconds is not None
        else "Full pipeline timing is unavailable."
    )
    artifacts = case.get("available_artifacts", [])
    replay = (
        f'<video controls playsinline muted loop preload="metadata" poster="{prefix}/poster.jpg" aria-label="{title} acquired camera and observed map replay"><source src="{prefix}/replay.mp4" type="video/mp4"><a href="{prefix}/replay.mp4">Download replay</a></video>'
        if "replay.mp4" in artifacts and "poster.jpg" in artifacts
        else '<p class="caption">A completed replay is unavailable for this case.</p>'
    )
    links = []
    if "overview.jpg" in artifacts:
        links.append(f'<a href="{prefix}/overview.jpg">Room-by-room overlays ↗</a>')
    if "cloud.json" in artifacts:
        links.extend(
            [
                f'<a href="{prefix}/cloud.json">Observed point data ↗</a>',
                f'<button class="map-link" data-case="{case["id"]}" type="button">Inspect this 3D map ↓</button>',
            ]
        )
    return f'''<article class="case" id="{case["id"]}"><p class="eyebrow">{html.escape(case["split"].upper())} CASE</p><h3>{title}</h3><p>{description}</p>
{replay}
<div class="case-stats"><span><strong>{visits["rooms_entered"]}/{visits["reference_room_count"]}</strong> rooms entered</span><span><strong>{percent(metrics["visible_edge_coverage"])}</strong> edges seen</span><span><strong>{percent(metrics["edge_completeness_10cm"])}</strong> 3D completeness</span></div><p class="case-outcome">{outcome}</p>
<p>{case["frames"]} acquired frames · {case["stations"]} survey stations · {case["path_length_m"]:.1f} m traveled. {visits["unique_portals_crossed"]}/{case["reference_portal_count"]} reference passages crossed. Stop reason: <code>{html.escape(case["stop_reason"])}</code>. Pipeline status: {html.escape(case["status"])} / {html.escape(str(case["stage"]))}.</p><p class="caption">First entries: {entry}. These names belong to the evaluator and are hidden from the policy.</p>
<details><summary>Timing and path audit</summary><p>{case["action_seconds"]:.1f} simulated action seconds; {case["wall_seconds"]:.1f} measured acquisition/processing seconds, excluding renderer startup and reporting. {full_timing}</p><p>{safe} Continuous architecture intersections: {audit["architecture"]["intersecting_path_segments"]}. Furniture recipe-box intersections: {audit["furniture_recipe_aabb_proxy"]["intersecting_path_segments"]}. Footprint radius: {audit["footprint_radius_m"]:.2f} m.</p><p>Checks use a horizontal disk and approximate furniture boxes, without whole-body dynamics or physical contact.</p></details>
{scene_note}<p>{" · ".join(links)}</p></article>'''


def build_page(summary):
    rows = []
    for case in summary["cases"]:
        title = html.escape(case["title"])
        if not case["evaluated"]:
            rows.append(
                f'<tr><th>{title}</th><td colspan="7">{html.escape(case["status"])}: no completed evaluation</td></tr>'
            )
            continue
        rows.append(
            f'<tr><th><a href="#{case["id"]}">{title}</a></th><td>{case["visits"]["rooms_entered"]}/{case["visits"]["reference_room_count"]}</td>'
            + "".join(f"<td>{percent(case['metrics'][key])}</td>" for key in METRICS)
            + f"<td>{case['frames']}</td></tr>"
        )
    aggregate = summary["aggregate"]
    findings = []
    for case in summary["cases"]:
        if not case["evaluated"] or not case.get("unentered_reference_rooms"):
            continue
        names = ", ".join(
            html.escape(name.replace("_", " "))
            for name in case["unentered_reference_rooms"]
        )
        visits = case["visits"]
        findings.append(
            f"<p><strong>{html.escape(case['id'].replace('_', ' ').title())}: {visits['rooms_entered']}/{visits['reference_room_count']} rooms entered.</strong> "
            f"Unentered rooms: {names}. Reference edge visibility reached {percent(case['metrics']['visible_edge_coverage'])}, including edges visible through openings; "
            "this does not establish whole-building exploration. This partial outcome remains included in every aggregate.</p>"
        )
    aggregate_rows = []
    labels = (
        "Edge visibility",
        "3D precision @ 10 cm",
        "3D completeness @ 10 cm",
        "Typed precision @ 10 cm",
        "Typed completeness @ 10 cm",
    )
    for metric, label in zip(METRICS, labels, strict=True):
        macro, weighted = aggregate["macro"][metric], aggregate["weighted"][metric]
        unit = "predicted voxels" if "precision" in metric else "m of reference edges"
        aggregate_rows.append(
            f"<tr><th>{label}</th><td>{percent(macro['value'])}</td><td>{macro['denominator_buildings']} buildings</td><td>{percent(weighted['value'])}</td><td>{weighted['denominator_value']:,.1f} {unit}</td></tr>"
        )
    options = "".join(
        f'<option value="{case["id"]}">{html.escape(case["title"])}</option>'
        for case in summary["cases"]
        if case["evaluated"] and "cloud.json" in case.get("available_artifacts", [])
    )
    values = {
        "__CASE_ROWS__": "".join(rows),
        "__FINDINGS__": '<div class="callout">' + "".join(findings) + "</div>"
        if findings
        else "",
        "__CASE_CARDS__": "".join(case_card(case) for case in summary["cases"]),
        "__AGGREGATE_ROWS__": "".join(aggregate_rows),
        "__OPTIONS__": options,
        "__BUILDINGS__": f"{aggregate['evaluated_buildings']}/{aggregate['declared_buildings']}",
        "__FRAMES__": f"{aggregate['total_frames']:,}",
        "__VISIBILITY__": percent(aggregate["macro"]["visible_edge_coverage"]["value"]),
        "__COMPLETENESS__": percent(
            aggregate["macro"]["edge_completeness_10cm"]["value"]
        ),
        "__FRAME_BUDGET__": str(summary["shared_budget"]["max_frames"]),
        "__STATION_BUDGET__": str(summary["shared_budget"]["max_stations"]),
    }
    page = (ROOT / "roomgraph-spaces/template.html").read_text()
    for key, value in values.items():
        page = page.replace(key, value)
    (ROOT / "roomgraph-spaces/index.html").write_text(page)


def verify_case_media(case, directory):
    """Verify the frozen receipt and the aggregate's selected media hashes before copying."""
    if not case["evaluated"]:
        return []
    receipt_path = directory / "receipt.json"
    if case.get("receipt_sha256") is not None:
        if (
            hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            != case["receipt_sha256"]
        ):
            raise ValueError(f"Case receipt changed: {case['id']}")
        receipt = json.loads(receipt_path.read_text())
        for name, digest in receipt["output_sha256"].items():
            artifact = (directory / name).resolve()
            if (
                not artifact.is_relative_to(directory.resolve())
                or hashlib.sha256(artifact.read_bytes()).hexdigest() != digest
            ):
                raise ValueError(
                    f"Case artifact differs from its receipt: {case['id']}/{name}"
                )
    elif case["status"] == "complete":
        raise ValueError("Completed case is missing its receipt")
    report_summary = directory / "report/summary.json"
    measured = (
        json.loads(report_summary.read_text()) if report_summary.exists() else None
    )
    if (
        measured is not None
        and measured["experiment_sha256"] != case["provenance"]["experiment_sha256"]
    ):
        raise ValueError(f"Suite and case media refer to different runs: {case['id']}")
    selected = []
    for name in ("replay.mp4", "poster.jpg", "overview.jpg", "cloud.json"):
        if name not in case.get("available_artifacts", []):
            continue
        if measured is None:
            raise ValueError("Available media lacks its completed report provenance")
        artifact = directory / "report" / name
        if (
            hashlib.sha256(artifact.read_bytes()).hexdigest()
            != case["media_sha256"][name]
        ):
            raise ValueError(
                f"Selected case media changed after aggregation: {case['id']}/{name}"
            )
        selected.append(artifact)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    args = parser.parse_args()
    summary = compact_summary(json.loads((args.report / "summary.json").read_text()))
    selected = {
        case["id"]: verify_case_media(case, args.cases / case["id"])
        for case in summary["cases"]
    }
    hashes = {}
    for name in ("overview.jpg", "coverage.png", "comparison.png"):
        copy_artifact(args.report / name, MEDIA / name, hashes)
    for case_id, artifacts in selected.items():
        for artifact in artifacts:
            copy_artifact(artifact, MEDIA / case_id / artifact.name, hashes)
    summary["public_artifacts_sha256"] = hashes
    (MEDIA / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    build_page(summary)
    print(
        f"Built {summary['aggregate']['declared_buildings']}-case development suite page."
    )


if __name__ == "__main__":
    main()
