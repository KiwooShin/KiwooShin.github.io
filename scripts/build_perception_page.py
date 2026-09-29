"""Publish selected measured perception results into the static project site."""

# HTML templates intentionally retain complete tags.

import argparse
import html
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
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
