# Personal homepage

Static homepage (`index.html`) with standalone project pages — no framework, no build step.

## Edit

Everything lives in `index.html`: styles in the `<style>` block, content in the
`<main>` sections. Each project card has a commented-out snippet showing how to
swap the "coming soon" placeholder for a YouTube embed or a small local clip.
Put local media (small GIFs/MP4s, < ~10 MB each) in a `media/` folder; host
full-length demo videos on YouTube (unlisted is fine) and embed them.

## Deploy (GitHub Pages, free)

```bash
cd ~/work/homepage
git init && git add . && git commit -m "Initial homepage"
gh repo create KiwooShin.github.io --public --source=. --push
```

Then on GitHub: repo **Settings → Pages → Source: Deploy from a branch →
`main` / root**. The site appears at <https://kiwooshin.github.io> within a
minute or two. Any later `git push` updates it automatically.

(Naming the repo `KiwooShin.github.io` gives you the root URL; any other repo
name would serve at `kiwooshin.github.io/<repo>`.)

## RoomGraph project page

`roomgraph/index.html` presents four furnished rooms, 32 calibrated camera views,
continuous moving-camera walkthroughs, and architectural edge overlays. The homepage
shows four rows of top-down + four overlay images and links to the detailed page.
The original empty-room calibration demo remains at `roomgraph/empty-room.html`.

Selected public previews live in `media/roomgraph/furnished/`. Static captures use
1152 × 768 / 128 samples per pixel; motion captures use 768 × 512 / 32 samples,
96 camera poses, and 12 fps. MP4 and GIF include a synchronized top-down marker.
Full datasets and downloaded rendering assets remain local in the RoomGraph repo.
These are scene-derived labels, not learned model predictions. Rendering and
export scripts: [RoomGraph commit 0972b10](https://github.com/KiwooShin/roomgraph/commit/0972b10).

After exporting previews with RoomGraph's `export_web_gallery.py` and
`make_walkthrough_media.py`, regenerate static markup with:

```bash
python3 scripts/build_roomgraph_gallery.py
```

The detail gallery has RGB/overlay toggles, camera thumbnails, synchronized map
markers, and optional viewpoint-sequence playback. Continuous camera motion is in
the separate videos. No frameworks or third-party JavaScript are used.

The structural graph uses a local canvas script with pointer and keyboard
controls. No third-party scripts or image hosts are needed. To preview:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
# Open http://127.0.0.1:8765/roomgraph/
```

## RoomGraph Perception project

`roomgraph-perception/index.html` is a separate trained-perception project, linked
from the homepage above the original RoomGraph dataset project. It reports the
held-out head-camera experiment, with measured training curves, learned edge
overlays, a mirror self-reflection example, and an interactive 3D room-shell
comparison. Camera poses and Manhattan axes are known in this synthetic pilot.

Selected previews and the measured summary live in `media/roomgraph-perception/`.
Generate the page from local experiment outputs with:

```bash
python scripts/build_perception_page.py --results /path/to/roomgraph/vis/perception
```

To include a measured training-efficiency follow-up on the same page:

```bash
python scripts/build_perception_page.py \
  --results /path/to/roomgraph/vis/perception \
  --efficiency /path/to/roomgraph/vis/training_efficiency
```

Generate that comparison with RoomGraph's `scripts/compare_training.py`. The page
copies its speed/memory and loss charts, publishes a JSON whitelist of timing,
validation metrics and reproducibility fields, and excludes local filesystem
paths. This validation-only experiment is separate from the original test result.
Later builds without `--efficiency` reuse the already published
`media/roomgraph-perception/efficiency.json`; they do not guess a local experiment
directory or silently remove the section. Wall time includes startup and cold
compilation when the source records initially empty compiler caches. Full local
overlays and training artifacts remain in the RoomGraph workspace.

To publish the active head-camera follow-up while retaining the original test
benchmark and training-efficiency measurements:

```bash
python scripts/build_perception_page.py \
  --results /path/to/roomgraph/vis/perception \
  --active-head /path/to/roomgraph/vis/active_head/report
```

The active-head input contains a completed validation-room `summary.json`,
`active_head.mp4`, `poster.jpg`, `comparison.png`, and `reconstruction.png`.
The builder publishes a compact whitelist in `media/roomgraph-perception/active-head.json`
and selected media under `media/roomgraph-perception/active-head/`. Raw experiment
traces, dense captures, checkpoints and absolute local paths are excluded.
Omitting `--active-head` on later builds preserves the published section and media.

This follow-up compares a hand-designed planner, fixed raster scan and five random
seeds under the same 12-second simulated motion budget, in one furnished validation
office with known metric camera poses and three translated bootstrap images.
The continuous video uses actual intermediate Isaac Sim renders of the frozen
trajectory. Extra animation frames do not enter policy selection or benchmark
metrics. Coverage and 3D accuracy are reported separately: the active policy covers
more structure than raster in this pilot, but its dimension error is larger.
It is a stationary-body head-motion experiment, not autonomous navigation or a
real-robot demonstration.

The model checkpoints, raw dataset, and TensorBoard logs remain in the local
RoomGraph workspace. The public page links back to reproducible source code and
explicitly separates the held-out perception benchmark, validation-only active-head
follow-up, and the separate depth-assisted connected-room pilot.

Implementation for the reported experiment:
[RoomGraph 38a4400](https://github.com/KiwooShin/roomgraph/commit/38a4400).
Validation included local-link checks, all image loads, 3D keyboard/orbit controls,
room/reference selection, and desktop/mobile layouts.

## Connected-room exploration

`roomgraph-multiroom/index.html` presents a separate development experiment in a
furnished office, corridor, living room and bedroom. The camera explores using
acquired RGB-D observations, a reused RGB edge model and known metric poses. The
page includes a 52.5-second replay, four rows of top-down + four learned overlays,
an interactive observed point cloud, candidate connectivity, and optional observed
wall-patch downloads. Visibility, geometric completeness and typed edge accuracy
are reported separately; the result is a partial reconstruction.

With RoomGraph checked out beside this repository, build from its completed report:

```bash
python scripts/build_multiroom_page.py --results ../roomgraph/vis/multiroom/report
```

The builder checks completed evaluation and matching experiment hashes. It copies
selected artifacts into `media/roomgraph-multiroom/`, recording their hashes in a
compact summary without per-frame traces or local paths. The full local report,
captures and predictions remain in RoomGraph's ignored `vis/` directory. Rebuilding
`build_perception_page.py` preserves links from the homepage and perception page.

The pilot entered all three rooms through their open doorways; it does not
establish complete surfaces, verified room semantics, SLAM robustness, or humanoid
walking control. Implementation:
[RoomGraph 7d4dad3](https://github.com/KiwooShin/roomgraph/commit/7d4dad3).

## Multiple connected-space cases

`roomgraph-spaces/index.html` adds a four-building development suite: branching
rooms, loop-connected spaces, an open office with side rooms, and a compact
apartment. It reuses the frozen perception model and exploration policy with
equal acquisition budgets. Ideal depth and known poses remain explicit.

Build only after RoomGraph has generated the aggregate report and per-case media:

```bash
python scripts/build_space_suite_page.py \
  --report ../roomgraph/vis/space_suite/report \
  --cases ../roomgraph/vis/space_suite/v1
```

The builder verifies terminal suite status and matching per-case experiment hashes,
then copies selected replays, overlays and observed point data to
`media/roomgraph-spaces/`. The page shows all declared cases, including incomplete
coverage or unavailable evaluations. Macro averages weight evaluated buildings
equally; pooled visibility/completeness weight reference edge length, and pooled
precision weights predicted voxels. Every denominator is recorded. This is a
development suite, not evidence of held-out robustness. Full captures and traces
remain in RoomGraph's ignored `vis/` tree. Earlier project pages retain their
original measured results.

Implementation and measured protocol:
[RoomGraph e470dd3](https://github.com/KiwooShin/roomgraph/commit/e470dd3).
Publication validation covers media receipts and hashes, all four videos and
interactive maps, local links, and desktop/mobile layouts. Run publisher tests
with `python -m unittest discover -s tests -v`.

The same page now includes a paired development comparison of the original
greedy frontier policy and bounded goal commitment. V2 still enters 13 of 16
rooms, but macro 3D completeness falls from 43.98% to 42.42% at 10 cm. The page
keeps v1 as the default and presents the candidate's regressions, observed maps,
four additional camera replays and repeated-observation diagnostics.

Build this section from the completed, replay-verified comparison:

```bash
python scripts/build_space_suite_page.py \
  --report ../roomgraph/vis/space_suite/report \
  --cases ../roomgraph/vis/space_suite/v1 \
  --policy-comparison ../roomgraph/vis/space_suite/policy_comparison \
  --candidate-cases ../roomgraph/vis/space_suite/v2
```

Omitting the comparison options on a later build preserves the published
comparison. Candidate assets are isolated under `media/roomgraph-spaces/policy-v2/`;
all 20 original selected baseline files remain byte-identical. Publication checks
cover all eight videos and selectable maps, candidate map buttons, asset links,
JavaScript errors, and desktop/mobile layouts. There are 13 publisher unit tests.
The complete captures, traces, local reports and QA evidence remain in RoomGraph's
ignored `vis/` tree. Implementation and measured protocol:
[RoomGraph 857e828](https://github.com/KiwooShin/roomgraph/commit/857e828).

## Real RGB-D and calibration sensitivity

`roomgraph-real/` presents the first ARKitScenes pilot: 240 selected views, a
frozen synthetic model and 24 measured fusion variants. The page distinguishes
surface agreement to an incomplete reference subset from architectural-edge
accuracy, which is not measured. It includes a 48-second camera replay, the
requested four-row overlay layout, and four interactive maps.

Build selected media and a public measurement summary with
`python scripts/build_arkitscenes_page.py`. The publisher requires completed
measurements, matching manifest/replay hashes and the surface-metric qualification.
It copies only four selected media files and the self-contained report, retaining
the dataset license. Raw captures and predictions remain local in RoomGraph.

Implementation and experiment:
[RoomGraph 3e08239](https://github.com/KiwooShin/roomgraph/commit/3e08239).

## Unified RoomGraph project

The homepage now presents synthetic data, head-camera perception, and connected-space
exploration as one RoomGraph entry. `roomgraph/` is the shared overview and retains
its furnished camera gallery. The detailed `roomgraph-perception/` and
`roomgraph-spaces/` pages remain accessible from the overview. `roomgraph-real/`
remains a separate real-data project.

`python scripts/build_roomgraph_gallery.py` maintains the unified homepage entry
and synthetic gallery. The perception publisher updates its detailed page only,
so regenerating results does not recreate a separate homepage card.
