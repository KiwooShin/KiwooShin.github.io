"""Publish selected measured multi-space media, retaining incomplete and failed cases."""

import argparse
import hashlib
import html
import json
import math
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


COMPARISON_MEASUREMENT_FIELDS = (
    "source_evaluated",
    "replay_qualified",
    "availability_reason",
    "status",
    "evaluated",
    "stop_reason",
    "unentered_reference_rooms",
    "frames",
    "path_length_m",
    "action_seconds",
    "wall_seconds",
    "full_pipeline_wall_seconds",
    "available_artifacts",
    "media_sha256",
    "receipt_sha256",
    "provenance",
    "visible_edge_coverage",
    "edge_precision_10cm",
    "edge_completeness_10cm",
    "typed_edge_precision_10cm",
    "typed_edge_completeness_10cm",
    "rooms_entered",
    "reference_room_count",
    "diagnostics",
    "policy",
    "policy_diagnostics",
)


def compact_comparison(source):
    """Publish measured comparisons, excluding raw trajectories or local paths."""
    if source.get("status") != "complete":
        raise ValueError("Publish only a completed paired comparison")
    result = {
        key: source[key]
        for key in (
            "schema_version",
            "comparison",
            "status",
            "qualification",
            "provenance",
            "shared_budget",
            "diagnostic_protocol",
            "macro",
            "limitations",
            "media_sha256",
        )
    }
    result["cases"] = []
    for case in source["cases"]:
        result["cases"].append(
            {
                **{key: case[key] for key in ("id", "title", "split", "delta")},
                **{
                    side: {
                        key: case[side][key]
                        for key in COMPARISON_MEASUREMENT_FIELDS
                        if key in case[side]
                    }
                    for side in ("baseline", "candidate")
                },
            }
        )
    return result


def verify_comparison_baseline(comparison, summary):
    cases = {case["id"]: case for case in summary["cases"]}
    paired = {case["id"]: case for case in comparison["cases"]}
    if cases.keys() != paired.keys() or len(paired) != len(comparison["cases"]):
        raise ValueError("Comparison must retain exactly the published baseline cases")
    if comparison["shared_budget"] != summary["shared_budget"]:
        raise ValueError("Comparison and baseline budgets differ")
    for identifier, pair in paired.items():
        baseline = pair["baseline"]
        if (
            baseline.get("source_evaluated", baseline["evaluated"])
            != cases[identifier]["evaluated"]
        ):
            raise ValueError("Comparison baseline evaluation status differs")
        if (
            baseline["evaluated"]
            and baseline["provenance"]["experiment_sha256"]
            != (cases[identifier]["provenance"]["experiment_sha256"])
        ):
            raise ValueError("Comparison refers to another baseline experiment")
        if baseline["evaluated"]:
            measured = cases[identifier]
            expected = {
                **measured["metrics"],
                "rooms_entered": measured["visits"]["rooms_entered"],
                **{
                    key: measured[key]
                    for key in (
                        "frames",
                        "path_length_m",
                        "action_seconds",
                        "wall_seconds",
                    )
                },
            }
            if any(baseline.get(key) != value for key, value in expected.items()):
                raise ValueError("Comparison baseline measurements differ")
        for key, delta in pair["delta"].items():
            b, c = baseline.get(key), pair["candidate"].get(key)
            expected_delta = (
                c - b
                if baseline["evaluated"]
                and pair["candidate"]["evaluated"]
                and b is not None
                and c is not None
                else None
            )
            if delta != expected_delta:
                raise ValueError("Comparison delta differs from paired measurements")

    for key, macro in comparison["macro"].items():
        eligible = [
            pair
            for pair in comparison["cases"]
            if pair["baseline"]["evaluated"]
            and pair["candidate"]["evaluated"]
            and pair["delta"].get(key) is not None
        ]
        if macro["denominator_buildings"] != len(eligible) or macro.get("case_ids") != [
            p["id"] for p in eligible
        ]:
            raise ValueError("Comparison macro denominator differs from measured pairs")
        before = (
            sum(p["baseline"][key] for p in eligible) / len(eligible)
            if eligible
            else None
        )
        after = (
            sum(p["candidate"][key] for p in eligible) / len(eligible)
            if eligible
            else None
        )
        expected = {
            "baseline": before,
            "candidate": after,
            "delta": after - before if eligible else None,
        }
        for name, value in expected.items():
            actual = macro[name]
            valid = (
                actual is None
                if value is None
                else (
                    isinstance(actual, (int, float))
                    and math.isclose(actual, value, abs_tol=1e-12)
                )
            )
            if not valid:
                raise ValueError(
                    "Comparison macro measurement differs from measured pairs"
                )


def prepare_comparison(directory, candidate_root, summary, summary_sha256):
    """Validate all inputs before copying any new public comparison artifact."""
    comparison = compact_comparison(
        json.loads((directory / "comparison.json").read_text())
    )
    if comparison["provenance"]["baseline_summary_sha256"] != summary_sha256:
        raise ValueError("Comparison baseline summary changed")
    verify_comparison_baseline(comparison, summary)
    charts = []
    for name in ("paired_metrics.png", "visibility_curves.png"):
        path = directory / name
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != comparison["media_sha256"][name]
        ):
            raise ValueError(f"Comparison chart changed: {name}")
        charts.append(path)
    selected = {}
    for pair in comparison["cases"]:
        case = {"id": pair["id"], **pair["candidate"]}
        selected[pair["id"]] = verify_case_media(case, candidate_root / pair["id"])
        if case["evaluated"]:
            evaluation = json.loads(
                (candidate_root / pair["id"] / "run/evaluation.json").read_text()
            )
            expected = {
                **{key: evaluation["final"][key] for key in METRICS},
                "rooms_entered": evaluation["visits"]["rooms_entered"],
                **{
                    key: evaluation[key]
                    for key in (
                        "frames",
                        "path_length_m",
                        "action_seconds",
                        "wall_seconds",
                    )
                },
            }
            if any(case.get(key) != value for key, value in expected.items()):
                raise ValueError(
                    "Comparison candidate measurements differ from evaluation"
                )
    return comparison, charts, selected


def comparison_value(value, key, signed=False):
    if value is None:
        return "—"
    if "edge" in key:
        return f"{value * 100:+.1f} pp" if signed else f"{value:.1%}"
    return f"{value:+.1f}" if signed else f"{value:.1f}"


def policy_comparison_section(comparison):
    if comparison is None:
        return ""
    keys = (
        "rooms_entered",
        "visible_edge_coverage",
        "edge_completeness_10cm",
        "edge_precision_10cm",
    )
    rows, timing_rows, diagnostic_rows, cards = [], [], [], []
    for pair in comparison["cases"]:
        title = html.escape(pair["id"].replace("_", " ").title())
        cells = []
        for key in keys:
            before, after, delta = (
                pair["baseline"].get(key),
                pair["candidate"].get(key),
                pair["delta"][key],
            )
            qualifier = "negative" if delta is not None and delta < 0 else ""
            cells.append(
                f"<td>{comparison_value(before, key)} → {comparison_value(after, key)}"
                f'<small class="{qualifier}">{comparison_value(delta, key, True)}</small></td>'
            )
        rows.append(f"<tr><th>{title}</th>" + "".join(cells) + "</tr>")
        cells = []
        for key in ("path_length_m", "action_seconds", "wall_seconds", "frames"):
            cells.append(
                f"<td>{comparison_value(pair['baseline'].get(key), key)} → "
                f"{comparison_value(pair['candidate'].get(key), key)}</td>"
            )
        timing_rows.append(f"<tr><th>{title}</th>" + "".join(cells) + "</tr>")
        cells = []
        for key in (
            "low_surface_gain_frames",
            "revisited_pose_frames",
            "goal_switches_before_proximity",
        ):
            b = (pair["baseline"].get("diagnostics") or {}).get(key)
            c = (pair["candidate"].get("diagnostics") or {}).get(key)
            cells.append(
                f"<td>{b if b is not None else '—'} → {c if c is not None else '—'}</td>"
            )
        diagnostic_rows.append(f"<tr><th>{title}</th>" + "".join(cells) + "</tr>")
        candidate = pair["candidate"]
        if not candidate["evaluated"]:
            cards.append(
                f'<article class="case"><h3>{title}</h3><p>Candidate status: '
                f"{html.escape(candidate['status'])}. No replay-qualified evaluation: "
                f"{html.escape(candidate.get('availability_reason') or 'incomplete evaluation')}.</p></article>"
            )
            continue
        prefix = f"../media/roomgraph-spaces/policy-v2/{pair['id']}"
        missing = ", ".join(candidate.get("unentered_reference_rooms") or []) or "none"
        before_missing = (
            ", ".join(pair["baseline"].get("unentered_reference_rooms") or []) or "none"
        )
        replay = (
            (
                f'<video controls playsinline muted loop preload="metadata" '
                f'poster="{prefix}/poster.jpg" aria-label="{title} goal commitment policy replay">'
                f'<source src="{prefix}/replay.mp4" type="video/mp4"></video>'
            )
            if ("replay.mp4" in (candidate.get("available_artifacts") or []))
            else ("<p>Candidate replay unavailable.</p>")
        )
        policy = candidate.get("policy_diagnostics") or {}
        retained = policy.get("action_counts", {}).get("retained")
        retained_note = (
            f"{retained} frontier decisions retained the active approach. "
            if retained is not None
            else ""
        )
        differed = policy.get("retained_different_from_local_greedy")
        if differed is not None:
            retained_note += (
                f"{differed} retained choices differed from greedy rescoring on those same "
                "candidate observations; this is not a counterfactual replay of v1. "
            )
        links = [f'<a href="#{pair["id"]}">Original v1 replay ↑</a>']
        if "overview.jpg" in (candidate.get("available_artifacts") or []):
            links.append(f'<a href="{prefix}/overview.jpg">v2 room overlays ↗</a>')
        if "cloud.json" in (candidate.get("available_artifacts") or []):
            links.append(f'<a href="{prefix}/cloud.json">v2 observed points ↗</a>')
            links.append(
                f'<button class="map-link" data-case="v2_{pair["id"]}" type="button">Inspect v2 map ↑</button>'
            )
        cards.append(
            f'<article class="case"><p class="eyebrow">V2 / GOAL COMMITMENT</p>'
            f"<h3>{title}</h3>{replay}<p><strong>{candidate['rooms_entered']}/"
            f"{candidate['reference_room_count']} rooms entered</strong> · "
            f"{percent(candidate['edge_completeness_10cm'])} 3D completeness.</p>"
            f'<p class="case-outcome">Unentered rooms: v1 {html.escape(before_missing)}; '
            f"v2 {html.escape(missing)}.</p><p>{retained_note}"
            f"Stopped at <code>{html.escape(candidate['stop_reason'])}</code>; "
            "reconstruction remains partial.</p><p>"
            + " · ".join(links)
            + "</p></article>"
        )
    macro_cells = []
    for key in keys:
        metric = comparison["macro"][key]
        macro_cells.append(
            f"<td>{comparison_value(metric['baseline'], key)} → "
            f"{comparison_value(metric['candidate'], key)}"
            f"<small>{comparison_value(metric['delta'], key, True)} · "
            f"n={metric['denominator_buildings']}</small></td>"
        )
    rows.append("<tr><th>Paired macro</th>" + "".join(macro_cells) + "</tr>")
    timing_macro = []
    for key in ("path_length_m", "action_seconds", "wall_seconds", "frames"):
        metric = comparison["macro"][key]
        timing_macro.append(
            f"<td>{comparison_value(metric['baseline'], key)} → "
            f"{comparison_value(metric['candidate'], key)}"
            f"<small>{comparison_value(metric['delta'], key, True)} · "
            f"n={metric['denominator_buildings']}</small></td>"
        )
    timing_rows.append("<tr><th>Paired macro</th>" + "".join(timing_macro) + "</tr>")
    missed = [
        f"{pair['id'].replace('_', ' ')} ({pair['candidate']['rooms_entered']}/{pair['candidate']['reference_room_count']} rooms)"
        for pair in comparison["cases"]
        if pair["candidate"]["evaluated"]
        and pair["candidate"]["rooms_entered"]
        < pair["candidate"]["reference_room_count"]
    ]
    outcome = (
        "The candidate still missed rooms in " + "; ".join(missed) + ". "
        if missed
        else "Entering rooms does not establish complete reconstruction. "
    )
    outcome += (
        "Macro 3D completeness changed by "
        + comparison_value(
            comparison["macro"]["edge_completeness_10cm"]["delta"],
            "edge_completeness_10cm",
            True,
        )
        + "; macro visibility changed by "
        + comparison_value(
            comparison["macro"]["visible_edge_coverage"]["delta"],
            "visible_edge_coverage",
            True,
        )
        + ". The original v1 policy remains the default; v2 is an experimental candidate."
    )
    return f"""<section id="policy-comparison"><p class="eyebrow">05 / PAIRED POLICY EXPERIMENT</p>
<h2>Testing goal commitment against the original policy.</h2>
<p>After diagnosing repeated detours in v1, we tested a policy that keeps a frontier approach across short body movements. It still checks current observed-free paths and releases a goal on arrival, blockage, loss of frontier association, stalled progress or a bounded step limit. The same furnished layouts, starting poses, model, camera sweeps and image budgets are retained.</p>
<div class="callout"><p><strong>{html.escape(outcome)}</strong></p><p>{html.escape(comparison["qualification"])} The original v1 results above stay unchanged. Negative changes and unentered rooms are retained below; this is one run per policy and layout.</p></div>
<figure><img src="../media/roomgraph-spaces/policy-v2/paired_metrics.png" loading="lazy" alt="Paired baseline and goal commitment measurements for all four spaces"><figcaption>Amber circles: v1 greedy selection. Mint diamonds: v2 goal commitment. Labels show signed changes; geometric scores use 10 cm tolerance.</figcaption></figure>
<div class="table-scroll"><table class="policy-table"><thead><tr><th>Building</th><th>Rooms entered</th><th>Edge visibility</th><th>3D completeness</th><th>3D precision</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="caption">Each cell shows v1 → v2. Changes in percentages are percentage points. Macro averages use matched measured cases with explicit denominators. Visibility, room entry and reconstructed geometry remain separate outcomes.</p>
<h3>Replay the candidate policy.</h3><div class="cases">{"".join(cards)}</div>
<details class="policy-details"><summary>Travel, timing and repeated observation diagnostics</summary>
<div class="table-scroll"><table><thead><tr><th>Building</th><th>Travel (m)</th><th>Simulated action (s)</th><th>Acquisition / processing (s)</th><th>Frames</th></tr></thead><tbody>{"".join(timing_rows)}</tbody></table></div>
<p class="caption">Wall time excludes renderer startup, evaluation and media export; one measured run does not establish a statistically reliable speedup. Fresh renders share the same settings but may have small RGB sampling differences even at matching camera poses.</p>
<div class="table-scroll"><table><thead><tr><th>Building</th><th>Frames at low surface gain stations</th><th>Frames near earlier poses</th><th>Early goal switches</th></tr></thead><tbody>{"".join(diagnostic_rows)}</tbody></table></div>
<p class="caption">Low gain means fewer than 500 new surface voxels per station. A repeated pose is within 0.3 m of a nonadjacent earlier station. Early goal switches change the target by more than 1 m while the old goal remains more than 0.75 m away; some switches are necessary because observations invalidate a path. These are descriptive proxies, not proof that images are redundant.</p></details>
<figure><img src="../media/roomgraph-spaces/policy-v2/visibility_curves.png" loading="lazy" alt="Architectural visibility versus simulated motion and camera action time for each policy"></figure>
<p><a href="../media/roomgraph-spaces/policy-v2/comparison.json">Paired measurements, policy settings and provenance (JSON) ↗</a></p></section>"""


def map_options(summary, comparison=None):
    """Keep baseline option IDs stable and route candidate maps to their own media."""
    baseline = "".join(
        f'<option value="{case["id"]}" data-cloud="../media/roomgraph-spaces/{case["id"]}/cloud.json">'
        f"{html.escape(case['title'])}</option>"
        for case in summary["cases"]
        if case["evaluated"] and "cloud.json" in case.get("available_artifacts", [])
    )
    if comparison is None:
        return baseline
    candidate = "".join(
        f'<option value="v2_{case["id"]}" data-cloud="../media/roomgraph-spaces/policy-v2/{case["id"]}/cloud.json">'
        f"{html.escape(case['title'])}</option>"
        for case in comparison["cases"]
        if case["candidate"]["evaluated"]
        and "cloud.json" in (case["candidate"].get("available_artifacts") or [])
    )
    return f'<optgroup label="v1 · Greedy frontier">{baseline}</optgroup><optgroup label="v2 · Goal commitment">{candidate}</optgroup>'


def build_page(summary, comparison=None):
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
    options = map_options(summary, comparison)
    values = {
        "__POLICY_COMPARISON__": policy_comparison_section(comparison),
        "__POLICY_LINK__": '<a href="#policy-comparison">Policy comparison</a>'
        if comparison
        else "",
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
    parser.add_argument("--policy-comparison", type=Path)
    parser.add_argument("--candidate-cases", type=Path)
    args = parser.parse_args()
    summary = compact_summary(json.loads((args.report / "summary.json").read_text()))
    selected = {
        case["id"]: verify_case_media(case, args.cases / case["id"])
        for case in summary["cases"]
    }
    if bool(args.policy_comparison) != bool(args.candidate_cases):
        parser.error(
            "--policy-comparison and --candidate-cases must be supplied together"
        )
    comparison, comparison_charts, candidate_artifacts = None, [], {}
    if args.policy_comparison:
        comparison, comparison_charts, candidate_artifacts = prepare_comparison(
            args.policy_comparison,
            args.candidate_cases,
            summary,
            hashlib.sha256((args.report / "summary.json").read_bytes()).hexdigest(),
        )
    elif (MEDIA / "policy-v2/comparison.json").is_file():
        comparison = compact_comparison(
            json.loads((MEDIA / "policy-v2/comparison.json").read_text())
        )
        verify_comparison_baseline(comparison, summary)
    hashes = {}
    for name in ("overview.jpg", "coverage.png", "comparison.png"):
        copy_artifact(args.report / name, MEDIA / name, hashes)
    for case_id, artifacts in selected.items():
        for artifact in artifacts:
            copy_artifact(artifact, MEDIA / case_id / artifact.name, hashes)
    if args.policy_comparison:
        comparison_hashes = {}
        for chart in comparison_charts:
            copy_artifact(chart, MEDIA / "policy-v2" / chart.name, comparison_hashes)
        for case_id, artifacts in candidate_artifacts.items():
            for artifact in artifacts:
                copy_artifact(
                    artifact,
                    MEDIA / "policy-v2" / case_id / artifact.name,
                    comparison_hashes,
                )
        comparison["public_artifacts_sha256"] = comparison_hashes
        (MEDIA / "policy-v2/comparison.json").write_text(
            json.dumps(comparison, indent=2, allow_nan=False) + "\n"
        )
    summary["public_artifacts_sha256"] = hashes
    (MEDIA / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    build_page(summary, comparison)
    print(
        f"Built {summary['aggregate']['declared_buildings']}-case development suite page."
    )


if __name__ == "__main__":
    main()
