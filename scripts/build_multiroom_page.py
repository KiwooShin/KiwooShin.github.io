"""Publish selected multi-room artifacts and an explicitly scoped measured page."""

import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FIELDS = (
    "status",
    "sensor_assumptions",
    "stop_reason",
    "frames",
    "stations",
    "path_length_m",
    "action_seconds",
    "wall_seconds",
    "surface_voxels",
    "edge_voxels",
    "experiment_sha256",
)


def percent(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def compact_summary(summary):
    """Allowlist final metrics; exclude local paths and per-frame evaluation traces."""
    if summary.get("status") != "complete":
        raise ValueError("A completed experiment is required")
    evaluation = summary.get("evaluation")
    if not evaluation or evaluation.get("status") != "complete":
        raise ValueError("A completed, independently evaluated experiment is required")
    if (
        evaluation.get("provenance", {}).get("experiment_sha256")
        != summary["experiment_sha256"]
    ):
        raise ValueError("Evaluation and report refer to different frozen experiments")
    if (
        evaluation["frames"] != summary["frames"]
        or evaluation["stations"] != summary["stations"]
    ):
        raise ValueError("Evaluation and report acquisition counts differ")
    audit = evaluation["path_audit"]
    visits = evaluation["visits"]
    public = {key: summary[key] for key in SUMMARY_FIELDS}
    public["evaluation"] = {
        "protocol": evaluation["protocol"],
        "provenance": evaluation["provenance"],
        "final": evaluation["final"],
        "visits": {
            key: visits[key]
            for key in (
                "region_entry_order",
                "region_transition_sequence",
                "rooms_entered",
                "reference_room_count",
                "unique_portals_crossed",
            )
        },
        "path_audit": {
            key: audit[key]
            for key in (
                "footprint_radius_m",
                "architecture",
                "furniture_recipe_aabb_proxy",
                "all_motions_in_observed_safe_map",
                "limitations",
            )
        },
        "timings": evaluation["timings"],
        "definitions": evaluation["definitions"],
    }
    if "observed_wall_patches" in summary:
        public["observed_wall_patches"] = summary["observed_wall_patches"]
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    summary = compact_summary(json.loads((args.results / "summary.json").read_text()))
    evaluation = summary["evaluation"]
    final, visits, audit = (
        evaluation["final"],
        evaluation["visits"],
        evaluation["path_audit"],
    )
    destination = ROOT / "media/roomgraph-multiroom"
    destination.mkdir(parents=True, exist_ok=True)
    summary["public_artifacts_sha256"] = {}
    selected = ["multiroom.mp4", "poster.jpg", "overview.jpg", "cloud.json"]
    wall_files = ("observed_walls.obj", "observed_walls.json")
    has_walls = all((args.results / name).is_file() for name in wall_files)
    if has_walls:
        selected.extend(wall_files)
    topology_files = ("topology.png", "topology.json")
    has_topology = all((args.results / name).is_file() for name in topology_files)
    topology = {}
    if has_topology:
        selected.extend(topology_files)
        topology = json.loads((args.results / "topology.json").read_text())
    for name in selected:
        source = args.results / name
        if not source.is_file():
            raise FileNotFoundError(source)
        summary["public_artifacts_sha256"][name] = hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        shutil.copy2(source, destination / name)
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    rows = []
    for name, metrics in final["per_region"].items():
        rows.append(
            f"<tr><td>{html.escape(name.replace('_', ' ').title())}</td>"
            f"<td>{percent(metrics['visible_edge_coverage'])}</td>"
            f"<td>{percent(metrics['edge_completeness_10cm'])}</td>"
            f"<td>{percent(metrics['observed_edge_completeness_10cm'])}</td></tr>"
        )
    timing_descriptions = []
    for name, timing in evaluation["timings"].items():
        if timing and timing.get("median_ms") is not None:
            timing_descriptions.append(
                f"{html.escape(name)} {timing['median_ms']:.1f} ms"
            )
        elif timing and timing.get("median_seconds") is not None:
            timing_descriptions.append(
                f"{html.escape(name)} {timing['median_seconds'] * 1000:.1f} ms"
            )
    architecture = audit["architecture"]
    furniture = audit["furniture_recipe_aabb_proxy"]
    safe = (
        "Every audited motion stayed"
        if audit["all_motions_in_observed_safe_map"]
        else "Some audited motions fell outside"
    )
    audit_text = (
        f"{safe} within the map's observed free space after footprint inflation. "
        if audit["all_motions_in_observed_safe_map"]
        else f"{safe} the map's observed free space after footprint inflation. "
    )
    audit_text += (
        f"With a {audit['footprint_radius_m']:.2f} m footprint radius, the reference audit found "
        f"{architecture['intersecting_path_segments']} architecture-intersecting path segments and "
        f"{furniture['intersecting_path_segments']} intersections with approximate furniture boxes. "
    )
    clearance = architecture.get("minimum_continuous_footprint_clearance_m")
    if clearance is not None:
        audit_text += (
            f"Minimum continuous architectural clearance: {clearance * 100:.1f} cm."
        )
    run_description = (
        f"The run acquired {summary['frames']} images at {summary['stations']} local survey stations "
        f"and traveled {summary['path_length_m']:.1f} m. "
        f"It accumulated {summary['surface_voxels']:,} observed surface voxels and "
        f"{summary['edge_voxels']:,} learned edge voxels. "
        f"Stopping condition: {html.escape(summary['stop_reason'].replace('_', ' '))}."
    )
    time_description = (
        f"Simulated action time: {summary['action_seconds']:.1f} s. "
        f"Measured experiment wall time: {summary['wall_seconds']:.1f} s. "
    )
    if timing_descriptions:
        time_description += (
            "Median processing times: " + "; ".join(timing_descriptions) + "."
        )
    substitutions = {
        "__TOPOLOGY_SECTION__": (
            '<section id="topology"><p class="eyebrow">OBSERVED CONNECTIVITY</p>'
            "<h2>From free-space observations to candidate regions.</h2>"
            '<figure><a href="../media/roomgraph-multiroom/topology.png"><img '
            'src="../media/roomgraph-multiroom/topology.png" loading="lazy" '
            'alt="Candidate regions and narrow connections extracted from the observed free-space map"></a>'
            "<figcaption>Grouping uses observed free space only, with no reference room labels or floor plan. "
            f"This run contains {topology['substantial_region_count']} substantial candidate regions, "
            f"{topology['neck_connection_count']} narrow connections and {topology['small_fragment_count']} small fragments. "
            "These candidates are not verified rooms or semantic doorway detections.</figcaption></figure>"
            '<p><a href="../media/roomgraph-multiroom/topology.json">Candidate region graph (JSON) ↗</a></p></section>'
            if has_topology
            else ""
        ),
        "__TYPED_SCORES__": (
            f"When the predicted edge type must also match, precision is {percent(final['typed_edge_precision_10cm'])} "
            f"and completeness is {percent(final['typed_edge_completeness_10cm'])}."
        ),
        "__WALL_PATCH_DOWNLOAD__": (
            '<p><a href="../media/roomgraph-multiroom/observed_walls.obj">Download observed wall patches (OBJ) ↗</a>'
            ' · <a href="../media/roomgraph-multiroom/observed_walls.json">Patch metadata (JSON)</a></p>'
            '<p class="caption">Axis-aligned tall plane candidates produce 15 cm patches only where acquired surfaces provide evidence. '
            "Unobserved cells remain empty; tall furniture may also produce candidates. This is not a complete, watertight, or semantically verified building mesh.</p>"
            if has_walls
            else ""
        ),
        "__ROOMS__": f"{visits['rooms_entered']} / {visits['reference_room_count']}",
        "__COVERAGE__": percent(final["visible_edge_coverage"]),
        "__COMPLETENESS__": percent(final["edge_completeness_10cm"]),
        "__PRECISION__": percent(final["edge_precision_10cm"]),
        "__RUN_DESCRIPTION__": run_description,
        "__ENTRY_ORDER__": " → ".join(
            html.escape(item.replace("_", " ").title())
            for item in visits["region_entry_order"]
        ),
        "__REGION_ROWS__": "\n".join(rows),
        "__TIMING_DESCRIPTION__": time_description,
        "__AUDIT_DESCRIPTION__": audit_text,
    }
    page = (ROOT / "roomgraph-multiroom/template.html").read_text()
    for token, value in substitutions.items():
        page = page.replace(token, value)
    (ROOT / "roomgraph-multiroom/index.html").write_text(page)
    print("Built connected-room page from completed measured artifacts.")


if __name__ == "__main__":
    main()
