"""Publish selected measured perception results into the static project site."""

# HTML templates intentionally retain complete tags.

import argparse
import html
import json
import shutil
import statistics
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def public_active_head_report(report):
    """Whitelist compact development metrics; never publish raw traces or local paths."""
    if report.get("status") != "complete" or report.get("split") != "val":
        raise ValueError("Active-head publication requires a completed validation-room experiment")
    if "config" in report:
        config = report["config"]
        report = {
            "schema_version": report["schema_version"],
            "status": report["status"],
            "room": report["room"],
            "split": report["split"],
            "action_budget_s": config["action_budget_s"],
            "planning_horizon_s": config["planning_horizon_s"],
            "bootstrap_views": len(report["bootstrap_camera_ids"]),
            "seed_count": len(config["random_seeds"]),
            "inference_median_ms_excluding_first": report["inference"]["median_ms_excluding_first"],
            "policies": [
                {
                    "name": policy["name"],
                    "acquired_views": policy["head_captures"],
                    "simulated_seconds": policy["simulated_seconds"],
                    "coverage_auc": policy["coverage_auc"],
                    "visible_edge_coverage": policy["visible_edge_coverage"],
                    "multi_view_edge_coverage": policy["multi_view_edge_coverage"],
                    "dimension_mae_m": policy["final_metrics"]["dimension_mae_m"],
                    "decision_median_ms": policy["median_decision_ms"],
                }
                for policy in report["policies"]
            ],
            "provenance": {
                key: report[key]
                for key in ("checkpoint_sha256", "capture_manifest_sha256",
                            "bootstrap_manifest_sha256", "experiment_sha256")
            },
        }
    fields = {
        "schema_version", "status", "room", "split", "action_budget_s", "planning_horizon_s",
        "bootstrap_views", "seed_count", "inference_median_ms_excluding_first",
    }
    result = {key: value for key, value in report.items() if key in fields}
    policy_fields = {
        "name", "acquired_views", "simulated_seconds", "coverage_auc", "visible_edge_coverage",
        "multi_view_edge_coverage", "dimension_mae_m", "decision_median_ms",
    }
    result["policies"] = [
        {key: value for key, value in policy.items() if key in policy_fields}
        for policy in report["policies"]
    ]
    names = [policy["name"] for policy in result["policies"]]
    if names.count("active") != 1 or names.count("raster") != 1:
        raise ValueError("Active-head publication requires one active and one raster result")
    result["provenance"] = {
        key: value for key, value in report.get("provenance", {}).items()
        if key in {"checkpoint_sha256", "capture_manifest_sha256", "bootstrap_manifest_sha256",
                   "experiment_sha256", "git_commit", "prediction_cache_sha256"}
    }
    return result


def build_active_head_section(source, destination):
    """Publish an explicitly selected report, preserving it on ordinary page rebuilds."""
    report_path = destination / "active-head.json"
    media = destination / "active-head"
    if source is not None:
        report = public_active_head_report(json.loads((source / "summary.json").read_text()))
        media.mkdir(exist_ok=True)
        for name in ["active_head.mp4", "comparison.png", "reconstruction.png"]:
            shutil.copy2(source / name, media / name)
        if (source / "poster.jpg").exists():
            shutil.copy2(source / "poster.jpg", media / "poster.jpg")
        else:
            with Image.open(source / "active_head.gif") as image:
                image.convert("RGB").save(media / "poster.jpg", quality=90)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    elif report_path.exists():
        report = public_active_head_report(json.loads(report_path.read_text()))
    else:
        return "", ""

    active = next(policy for policy in report["policies"] if policy["name"] == "active")
    raster = next(policy for policy in report["policies"] if policy["name"] == "raster")
    random = [policy for policy in report["policies"] if policy["name"].startswith("random_")]
    rows = []
    for name, values in [("Active head", [active]), ("Fixed raster", [raster])]:
        policy = values[0]
        rows.append(
            f'<tr><td>{name}</td><td>{policy["acquired_views"]}</td>'
            f'<td>{policy["visible_edge_coverage"]:.2%}</td>'
            f'<td>{policy["coverage_auc"]:.2%}</td>'
            f'<td>{100 * policy["dimension_mae_m"]:.2f} cm</td></tr>'
        )
    random_note = ""
    if random:
        mean = {key: statistics.mean(row[key] for row in random) for key in [
            "acquired_views", "visible_edge_coverage", "coverage_auc", "dimension_mae_m"
        ]}
        rows.append(
            f'<tr><td>Random (mean, {len(random)} seeds)</td>'
            f'<td>{mean["acquired_views"]:.1f}</td><td>{mean["visible_edge_coverage"]:.2%}</td>'
            f'<td>{mean["coverage_auc"]:.2%}</td>'
            f'<td>{100 * mean["dimension_mae_m"]:.2f} cm</td></tr>'
        )
        random_note = (
            f'Random final coverage ranges from {min(row["visible_edge_coverage"] for row in random):.2%}'
            f' to {max(row["visible_edge_coverage"] for row in random):.2%}. '
        )
    geometry_note = (
        "The active policy sees more edges, but its room-dimension error is larger"
        if active["visible_edge_coverage"] > raster["visible_edge_coverage"]
        and active["dimension_mae_m"] > raster["dimension_mae_m"]
        else "Coverage and geometric accuracy are separate objectives"
    )
    section = f'''<section id="active-head">
<p class="eyebrow">ACTIVE PERCEPTION / ONE DEVELOPMENT ROOM</p>
<h2>Turn the head toward structure still missing.</h2>
<p>The body stays in place while an articulated head changes camera yaw and pitch. A small,
hand-designed planner uses only acquired RGB predictions, known camera calibration, and the
current shell hypothesis to choose where to look over the next {report["planning_horizon_s"]:g}
seconds. It replans after each image; candidate images and renderer truth are hidden from it.</p>
<figure class="active-head-video"><video controls playsinline loop muted preload="metadata"
poster="../media/roomgraph-perception/active-head/poster.jpg"
aria-label="Continuous articulated head-camera replay with top-down direction, predicted edge overlay and evolving shell support">
<source src="../media/roomgraph-perception/active-head/active_head.mp4" type="video/mp4">
<a href="../media/roomgraph-perception/active-head/active_head.mp4">Download the active-head video</a>
</video><figcaption>Actual Isaac Sim renders along the frozen active trajectory, with a synchronized
top-down camera direction, learned overlay, and accumulated support. Acceleration-limited yaw
and pitch include settling holds. Extra intermediate frames illustrate motion only; they are
excluded from policy decisions, reconstruction, and benchmark metrics.</figcaption></figure>
<div class="table-scroll"><table><thead><tr><th>Policy</th><th>Head views</th>
<th>Final edge coverage</th><th>Time-averaged coverage</th><th>Dimension MAE</th>
</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="caption">One furnished validation office; the same three translated bootstrap views,
initial head image, and {report["action_budget_s"]:g}-second simulated head-motion budget for
every policy. Head-view counts include the initial image. Coverage measures the fraction of
reference architectural edge length directly visible in acquired views, scored separately from
selection. The time budget includes motion and settling, and excludes inference, planning,
and reconstruction. {html.escape(random_note)}</p>
<div class="callout"><p>{geometry_note}: active
{100 * active["dimension_mae_m"]:.2f} cm versus raster
{100 * raster["dimension_mae_m"]:.2f} cm. More observed structure does not guarantee a more
accurate fitted room. This pilot does not establish a generally better policy.</p></div>
<p>The map distinguishes unseen structure, inspected structure without visible-edge support,
and predictions supported from one or multiple translated camera centers. Looking in a direction
does not verify the surface behind furniture. Rotating the head cannot replace the translated
viewpoints needed for metric reconstruction.</p>
<p class="caption">Median active decision time: {active["decision_median_ms"]:.2f} ms on CPU.
The existing perception checkpoint is reused; no reinforcement learning or policy training is
required. Support is an uncalibrated reprojection heuristic. Head limits and the humanoid proxy
are illustrative, with known metric poses; this is not official 1X hardware, a learned exploration
policy, autonomous navigation, or a real-robot evaluation.</p>
<details class="active-head-details"><summary>Inspect coverage and 3D reconstruction comparisons</summary>
<figure><img src="../media/roomgraph-perception/active-head/comparison.png" loading="lazy"
alt="Acquired visible structural-edge coverage over simulated time for active, fixed raster and five random head policies">
<figcaption>Coverage curves use only images acquired by each policy. Ground-truth visibility is
available to the evaluator, never to the planner.</figcaption></figure>
<figure><img src="../media/roomgraph-perception/active-head/reconstruction.png" loading="lazy"
alt="Fitted room shells and reference geometry comparing active, raster and random camera policies">
<figcaption>Known camera poses; rectangular shell fitting. Door/window openings, furniture geometry,
and safe navigable space are not reconstructed.</figcaption></figure></details>
<p><a href="../media/roomgraph-perception/active-head.json">Compact measurements and provenance (JSON) ↗</a>
 · <a href="https://github.com/KiwooShin/roomgraph/blob/feat/isaac-dataset/docs/active-head-experiment.md">Protocol and reproducible commands ↗</a></p>
</section>'''
    return '<a href="#active-head">Active head camera</a>', section


def public_efficiency_report(report):
    """Keep reproducibility measurements while excluding local paths and raw predictions."""
    run_fields = {
        "name",
        "dataset_sha256",
        "gpu",
        "torch",
        "parameters",
        "git_commit",
        "git_dirty",
        "sampling",
        "compiler_cache",
        "resumed",
        "resume_epoch",
        "epochs_completed",
        "best_epoch",
        "best_val_loss",
        "time_to_quality",
        "optimizer_steps",
        "optimizer_steps_source",
        "training_images_seen",
        "train_loop_seconds",
        "train_loop_images_per_second",
        "steady_epoch_median_images_per_second",
        "train_session_seconds",
        "process_seconds",
        "launcher_wall_seconds",
        "peak_allocated_mb",
        "validation_images",
        "validation_rooms",
        "checkpoint_sha256",
        "checkpoint_epoch",
        "validation",
    }
    config_fields = {
        "seed",
        "epochs",
        "batch_size",
        "learning_rate",
        "weight_decay",
        "amp",
        "pretrained",
        "patience",
        "eval_every",
        "tolerance_pixels",
        "workers",
        "compile_loss",
        "compile_model",
        "compile_mode",
        "checkpoint_every",
    }
    result = {
        key: report[key]
        for key in (
            "schema_version",
            "threshold",
            "target_val_loss",
            "threshold_selection",
            "split",
            "evaluation_device",
            "comparison",
            "curve_time_scope",
        )
        if key in report
    }
    if result.get("split") != "val":
        raise ValueError("The efficiency section requires a validation-only comparison")
    result["runs"] = []
    for run in report["runs"]:
        public_run = {key: value for key, value in run.items() if key in run_fields}
        public_run["config"] = {
            key: value for key, value in run["config"].items() if key in config_fields
        }
        result["runs"].append(public_run)
    if not result["runs"]:
        raise ValueError("The efficiency report has no measured runs")
    return result


def build_efficiency_section(source, destination):
    """Publish an explicit experiment, or preserve already published measurements on rebuild."""
    report_path = destination / "efficiency.json"
    if source is not None:
        report = public_efficiency_report(
            json.loads((source / "comparison.json").read_text())
        )
        for name in ["speed_memory.png", "loss_curves.png"]:
            shutil.copy2(source / name, destination / name)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    elif report_path.exists():
        report = public_efficiency_report(json.loads(report_path.read_text()))
    else:
        return "", ""

    def number(value, suffix="", precision=1):
        return "Unrecorded" if value is None else f"{value:,.{precision}f}{suffix}"

    rows = []
    for run in report["runs"]:
        metrics = run["validation"]
        cells = [
            html.escape(run["name"]),
            number(run.get("launcher_wall_seconds"), " s"),
            number(run.get("steady_epoch_median_images_per_second")),
            number(run.get("peak_allocated_mb"), " MiB", precision=0),
            number(metrics["visible"]["f1"], precision=4),
            number(metrics["amodal"]["f1"], precision=4),
        ]
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    comparison = report["comparison"]
    issues = (
        comparison["work_mismatches"]
        + comparison["environment_mismatches"]
        + comparison.get("timing_caveats", [])
    )
    if not issues and len(report["runs"]) > 1:
        reference = report["runs"][0]
        experiment = (
            f"Each run uses {reference['epochs_completed']} epochs, "
            f"{reference['optimizer_steps']:,} optimizer updates, batch size "
            f"{reference['config']['batch_size']}, and seed {reference['config']['seed']}. "
            "The dataset, learning-rate schedule, and reported hardware/software match."
        )
    else:
        experiment = "Comparison caveats: " + "; ".join(
            issues or ["one measured run only"]
        )
    cold_cache = all(
        run.get("compiler_cache") == "isolated; initially empty"
        for run in report["runs"]
    )
    compilation_note = (
        "Each run starts with isolated, empty compiler caches, so compiled-run wall time "
        "includes cold compilation."
        if cold_cache
        else "Compiler-cache conditions are recorded in the measurement JSON."
    )
    quality_note = ""
    if "target_val_loss" in report:
        times = []
        for run in report["runs"]:
            quality = run["time_to_quality"]
            duration = (
                number(quality["train_session_elapsed_seconds"], " s")
                if quality["attained"]
                else "not reached"
            )
            times.append(f"{html.escape(run['name'])}: {duration}")
        quality_note = (
            f'<p class="caption">Time to the preselected validation-loss target '
            f"≤ {report['target_val_loss']:g}: {'; '.join(times)}. "
            "First scheduled crossing on the training-session clock, including compilation "
            "but excluding process initialization; no interpolation.</p>"
        )
    section = f"""<section id="efficiency">
<p class="eyebrow">TRAINING EFFICIENCY / VALIDATION-ONLY FOLLOW-UP</p>
<h2>Measure speed alongside prediction quality.</h2>
<p>{html.escape(experiment)} The fixed decision threshold is {report["threshold"]:.2f}.
This separate experiment uses validation rooms only; the held-out test results above remain
the original benchmark.</p>
<div class="table-scroll"><table><thead><tr><th>Training mode</th><th>Wall time</th>
<th>Steady images/s</th><th>Peak CUDA</th><th>Val visible F1</th><th>Val amodal F1</th>
</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
{quality_note}
<p class="caption">Wall time includes interpreter startup, data/model initialization, training,
validation, and checkpointing. {html.escape(compilation_note)} Steady throughput is the median
train-loop images/s after the first epoch. Peak CUDA measures tensor allocation, not total
system memory. These are single-seed measurements, not a statistical reliability claim.</p>
<figure><a href="../media/roomgraph-perception/speed_memory.png"><img
src="../media/roomgraph-perception/speed_memory.png" width="2340" height="720" loading="lazy"
alt="Measured training-session duration, aggregate training throughput, and peak CUDA allocation">
</a><figcaption>Chart throughput averages all training batches, including first-epoch compilation;
the table reports steady throughput after that epoch. Table wall time also includes process
startup.</figcaption></figure>
<details class="efficiency-details"><summary>Inspect loss curves and timing scope</summary>
<figure><img src="../media/roomgraph-perception/loss_curves.png" width="2160" height="720"
loading="lazy" alt="Training and validation loss against measured elapsed training time">
<figcaption>Time axis: {html.escape(report["curve_time_scope"])}. Checkpoints are selected by
validation loss. Training-session time includes validation and checkpointing;
the first compiled epoch includes compilation.</figcaption></figure>
<p class="caption">A matching seed and schedule do not guarantee identical floating-point
results. Validation shares procedural scene families with training; this comparison does not
establish robustness on unseen buildings or real robots.</p></details>
<p><a href="../media/roomgraph-perception/efficiency.json">Efficiency measurements and provenance
(JSON) ↗</a></p></section>"""
    return '<a href="#efficiency">Training efficiency</a>', section


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--efficiency",
        type=Path,
        help="Explicit validation comparison directory; omission preserves published measurements",
    )
    parser.add_argument(
        "--active-head",
        type=Path,
        help="Explicit completed active-head report directory; omission preserves its section",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("/home/kiwoos/work/roomgraph/vis/perception"),
    )
    parser.add_argument(
        "--mirror",
        type=Path,
        default=Path(
            "/home/kiwoos/work/roomgraph/vis/headcam_demo/headcam_mirror_demo/view_000_rgb.png"
        ),
    )
    args = parser.parse_args()
    summary = json.loads((args.results / "summary.json").read_text())
    metrics, run = summary["metrics"], summary["run"]
    destination = ROOT / "media/roomgraph-perception"
    destination.mkdir(parents=True, exist_ok=True)
    efficiency_nav, efficiency_section = build_efficiency_section(
        args.efficiency, destination
    )
    active_head_nav, active_head_section = build_active_head_section(args.active_head, destination)
    for name in [
        "training.png",
        "reconstruction.png",
        "predictions.jpg",
        "summary.json",
    ]:
        shutil.copy2(args.results / name, destination / name)
    with Image.open(args.mirror) as image:
        image.save(destination / "mirror.webp", quality=90)
    rows = []
    options = []
    gallery = []
    for index, room in enumerate(summary["rooms"]):
        name = room["room"]
        folder = destination / name
        folder.mkdir(exist_ok=True)
        for source in (args.results / name).iterdir():
            if source.suffix in {".webp", ".json", ".obj"}:
                shutil.copy2(source, folder / source.name)
        visible = room["metrics"]["visible"]
        amodal = room["metrics"]["amodal"]
        geometry = room["reconstruction"]["metrics"]
        rows.append(
            f"<tr><td>{html.escape(name)}</td><td>{visible['precision']:.3f} / {visible['recall']:.3f} / {visible['f1']:.3f}</td><td>{amodal['f1']:.3f}</td><td>{geometry['dimension_mae_m']:.3f} m</td><td>{geometry['edge_chamfer_m']:.3f} m</td></tr>"
        )
        options.append(f'<option value="{index}">{html.escape(name)}</option>')
        pictures = [
            f'<figure><a href="../media/roomgraph-perception/{picture}"><img src="../media/roomgraph-perception/{picture}" width="1536" height="302" loading="lazy" alt="{name}, fixed camera sample {i * 6}: RGB, reference edges, visible prediction and typed full prediction"></a><figcaption>{name} · camera {i * 6:02d}</figcaption></figure>'
            for i, picture in enumerate(room["images"])
        ]
        gallery.append(
            f'<article class="gallery-room"><h3>{html.escape(name)}</h3>{pictures[0]}<details><summary>Inspect three more camera views</summary>{"".join(pictures[1:])}</details></article>'
        )
    substitutions = {
        "__VISIBLE__": f"{metrics['test']['visible']['f1']:.3f}",
        "__AMODAL__": f"{metrics['test']['amodal']['f1']:.3f}",
        "__DIMENSION__": f"{summary['reconstruction_mean']['dimension_mae_m']:.3f}",
        "__LATENCY__": f"{metrics['inference']['median_ms']:.1f}",
        "__EPOCHS__": str(run["epochs_completed"]),
        "__BEST__": str(run["best_epoch"] + 1),
        "__PARAMS__": f"{run['parameters'] / 1e6:.2f}",
        "__ORACLE__": f"{summary['oracle_mean']['dimension_mae_m']:.3f}",
        "__PRIOR__": f"{summary['prior_mean']['dimension_mae_m']:.3f}",
        "__RESULT_ROWS__": "\n".join(rows),
        "__ROOM_OPTIONS__": "\n".join(options),
        "__PREDICTION_GALLERY__": "\n".join(gallery),
        "__ROOM_DATA__": json.dumps(summary["rooms"]).replace("<", "\\u003c"),
        "__EFFICIENCY_NAV__": efficiency_nav,
        "__EFFICIENCY_SECTION__": efficiency_section,
        "__ACTIVE_HEAD_NAV__": active_head_nav,
        "__ACTIVE_HEAD_SECTION__": active_head_section,
    }
    content = (ROOT / "roomgraph-perception/template.html").read_text()
    for token, value in substitutions.items():
        content = content.replace(token, value)
    (ROOT / "roomgraph-perception/index.html").write_text(content)
    homepage = ROOT / "index.html"
    content = homepage.read_text()
    active_summary = (
        ' A separate <a href="roomgraph-perception/#active-head">active head-camera pilot</a> '
        'uses missing-structure cues to choose the next yaw/pitch target in a furnished office.'
        if active_head_section else ""
    )
    card = f"""    <article class="project" id="roomgraph-perception">
      <h3><a href="roomgraph-perception/">RoomGraph Perception — Head-camera RGB to 3D Room Structure</a></h3>
      <p>A trained structural-edge model and calibrated multi-view reconstruction from furnished humanoid head-camera images, with visible robot arms and mirror reflections. On four held-out synthetic room instances: <strong>{metrics["test"]["visible"]["f1"]:.3f} visible-edge F1</strong>, <strong>{metrics["test"]["amodal"]["f1"]:.3f} amodal-edge F1</strong>, and <strong>{summary["reconstruction_mean"]["dimension_mae_m"]:.3f} m mean dimension error</strong>.</p>
      <p>Known camera poses and Manhattan axes; rectangular room shells only.{active_summary} Autonomous navigation remains future work.</p>
      <div class="tags"><span>3D perception</span><span>PyTorch</span><span>head camera</span><span>multi-view geometry</span></div>
      <figure class="featured"><a href="roomgraph-perception/#predictions"><img src="media/roomgraph-perception/predictions.jpg" width="1536" height="1240" loading="lazy" alt="Four held-out furnished head-camera views comparing RGB, reference edges, learned visible edges and learned amodal structure"></a><figcaption>Fixed camera samples from all four test rooms. These are learned predictions, including errors; blue overlays are evaluation references.</figcaption></figure>
      <div class="gallery"><figure><a href="roomgraph-perception/#reconstruction"><img src="media/roomgraph-perception/reconstruction.png" width="1920" height="1440" loading="lazy" alt="Predicted and reference 3D room shells for four held-out rooms"></a><figcaption>3D shell fitting from eight calibrated views per room.</figcaption></figure><figure><a href="roomgraph-perception/"><img src="media/roomgraph-perception/mirror.webp" width="1152" height="768" loading="lazy" alt="Head-mounted camera seeing the humanoid proxy's body reflected in a mirror"></a><figcaption>Robot body and arms rendered in 3D. Original approximate proxy, not an official 1X model.</figcaption></figure></div>
      <p class="links"><a href="roomgraph-perception/"><strong>Detailed project page &amp; interactive 3D results →</strong></a> · <a href="https://github.com/KiwooShin/roomgraph">Code ↗</a></p>
    </article>

"""
    start_marker = '    <article class="project" id="roomgraph-perception">'
    if start_marker in content:
        start = content.index(start_marker)
        end = content.index('    <article class="project" id="roomgraph">', start)
        content = content[:start] + card + content[end:]
    else:
        content = content.replace(
            '    <article class="project" id="roomgraph">',
            card + '    <article class="project" id="roomgraph">',
            1,
        )
    homepage.write_text(content)
    print("Built new perception project and homepage entry from measured results.")


if __name__ == "__main__":
    main()
