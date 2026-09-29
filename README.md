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

The model checkpoints, raw dataset, and TensorBoard logs remain in the local
RoomGraph workspace. The public page links back to reproducible source code and
explicitly separates this result from future active mapping and robot navigation.

Implementation for the reported experiment:
[RoomGraph 38a4400](https://github.com/KiwooShin/roomgraph/commit/38a4400).
Validation included local-link checks, all image loads, 3D keyboard/orbit controls,
room/reference selection, and desktop/mobile layouts.
