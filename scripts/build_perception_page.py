"""Publish selected measured perception results into the static project site."""

# HTML templates intentionally retain complete tags.

import argparse
import html
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


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
    }
    content = (ROOT / "roomgraph-perception/template.html").read_text()
    for token, value in substitutions.items():
        content = content.replace(token, value)
    (ROOT / "roomgraph-perception/index.html").write_text(content)
    homepage = ROOT / "index.html"
    content = homepage.read_text()
    card = f"""    <article class="project" id="roomgraph-perception">
      <h3><a href="roomgraph-perception/">RoomGraph Perception — Head-camera RGB to 3D Room Structure</a></h3>
      <p>A trained structural-edge model and calibrated multi-view reconstruction from furnished humanoid head-camera images, with visible robot arms and mirror reflections. On four held-out synthetic room instances: <strong>{metrics["test"]["visible"]["f1"]:.3f} visible-edge F1</strong>, <strong>{metrics["test"]["amodal"]["f1"]:.3f} amodal-edge F1</strong>, and <strong>{summary["reconstruction_mean"]["dimension_mae_m"]:.3f} m mean dimension error</strong>.</p>
      <p>Known camera poses and Manhattan axes; rectangular room shells only. This is a perception experiment, with active mapping and navigation still ahead.</p>
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
