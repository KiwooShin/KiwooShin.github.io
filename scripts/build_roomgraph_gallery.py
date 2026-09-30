"""Regenerate RoomGraph's static homepage rows and detailed camera gallery."""

# HTML fragments intentionally keep complete tags together.
# ruff: noqa: E501

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = "media/roomgraph/furnished"
scenes = json.loads((ROOT / MEDIA / "gallery.json").read_text())
rows, sections = [], []
for number, scene in enumerate(scenes, 1):
    name, title = scene["name"], html.escape(scene["title"])
    base = f"{MEDIA}/{name}"
    cells = [
        f'<figure><a href="roomgraph/#{name}"><img src="{base}/top_down_four.webp" width="420" height="280" loading="lazy" alt="{title}: top-down with camera positions C1 to C4"><figcaption>Top-down</figcaption></a></figure>'
    ]
    for view in scene["views"][:4]:
        camera = view["id"]
        cells.append(
            f'<figure><a href="roomgraph/#{name}"><img src="{base}/{camera}_thumb.webp" width="420" height="280" loading="lazy" alt="{title}, {camera}: structural-edge overlay"><figcaption>Overlay {camera[1:]}</figcaption></a></figure>'
        )
    rows.append(
        f'<div class="rg-scene-row"><h4>{title}</h4><div class="rg-scroll" role="region" aria-label="{title} camera previews" tabindex="0"><div class="rg-five">{"".join(cells)}</div></div></div>'
    )
    base = "../" + base
    markers, cards = [], []
    for i, view in enumerate(scene["views"]):
        camera = view["id"]
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in view["triangle"])
        x, y = view["triangle"][0]
        markers.append(
            f'<g class="{"active" if i == 0 else ""}"><polygon points="{points}"/><text x="{x + 15:.2f}" y="{y - 12:.2f}">{camera}</text></g>'
        )
        position = ", ".join(f"{v:g}" for v in view["position"]) + " m"
        cards.append(
            f'''<figure class="camera-card"><button type="button" data-camera="{camera}" data-overlay="{base}/{camera}_overlay.webp" data-rgb="{base}/{camera}_rgb.webp" data-position="{position}" aria-label="Select {title}, camera {camera}" aria-pressed="{"true" if i == 0 else "false"}"><img src="{base}/{camera}_thumb.webp" width="420" height="280" loading="lazy" alt="Structural edges, {title}, {camera}"><span>{camera}</span></button><figcaption>{position}</figcaption></figure>'''
        )
    first = scene["views"][0]
    position = ", ".join(f"{v:g}" for v in first["position"]) + " m"
    sections.append(f'''<section class="room" id="{name}" data-title="{title}">
<div class="room-head"><h2><span class="number">0{number}</span>{title}</h2><a href="{base}/scene.json">Scene JSON ↗</a></div>
<p class="room-description">{html.escape(scene["description"])} {scene["object_count"]} furnishing assemblies.</p>
<div class="walkthrough"><video controls loop muted playsinline preload="none" width="1152" height="576" poster="{base}/walkthrough-poster.webp" aria-label="Continuous moving-camera walkthrough of {title} with structural-edge overlay and camera map"><source src="{base}/walkthrough.mp4" type="video/mp4"></video><p>Continuous camera path · 96 rendered poses · 8-second loop · <a href="{base}/walkthrough.gif">GIF version ↗</a></p></div>
<h3 class="views-heading">Inspect the calibrated views</h3>
<div class="viewer"><figure class="map-panel"><span class="map-label">Top-down / camera direction</span><div class="map-frame"><img src="{base}/top_down.webp" width="1152" height="768" loading="lazy" alt="Top-down furniture layout, {title}"><svg viewBox="0 0 1152 768" role="img" aria-label="Camera positions C1 through C8; highlighted triangle is the selected camera">{"".join(markers)}</svg></div></figure><figure class="image-panel"><a class="full-image" href="{base}/C1_overlay.webp"><img class="main-image" src="{base}/C1_overlay.webp" width="1152" height="768" loading="lazy" alt="{title}, C1, architectural edge overlay"></a><figcaption><span class="camera-name">C1 / 8 views</span><span class="camera-position">{position}</span></figcaption></figure></div>
<div class="controls"><div class="modes" role="group" aria-label="Image display mode"><button type="button" data-mode="overlay" aria-pressed="true">Edge overlay</button><button type="button" data-mode="rgb" aria-pressed="false">RGB</button></div><div class="transport"><button class="previous" type="button" aria-label="Previous camera">←</button><button class="play" type="button" aria-pressed="false">▶ Play camera sequence</button><button class="next" type="button" aria-label="Next camera">→</button></div></div>
<div class="camera-grid">{"".join(cards)}</div>
</section>''')

homepage = ROOT / "index.html"
content = homepage.read_text()
# The detailed experiments now share one homepage project.
for identifier in ("roomgraph-spaces", "roomgraph-perception"):
    content = re.sub(
        rf'^[ \t]*<article class="project" id="{identifier}">.*?</article>[ \t]*\n*',
        "", content, flags=re.DOTALL | re.MULTILINE,
    )
start = content.index('    <article class="project" id="roomgraph">')
end = content.index('    <article class="project" id="calibration-recovery">', start)
content = (
    content[:start]
    + f"""    <article class="project" id="roomgraph">
      <h3><a href="roomgraph/">RoomGraph — Indoor Perception &amp; 3D Exploration</a></h3>
      <p>From furnished simulation to learned structural edges and observed 3D maps. RoomGraph connects synthetic dataset generation in Isaac Sim, humanoid head-camera perception, and active exploration across connected indoor spaces.</p>
      <div class="tags"><span>Isaac Sim</span><span>Synthetic data</span><span>PyTorch</span><span>Active perception</span><span>3D reconstruction</span></div>
      <p class="links"><a href="roomgraph/#bedroom">01 · Synthetic indoor data</a> · <a href="roomgraph-perception/">02 · Head-camera perception</a> · <a href="roomgraph-spaces/">03 · Connected-space exploration</a></p>
      <figure class="featured"><a href="roomgraph-spaces/#gallery"><img src="media/roomgraph-spaces/overview.jpg" width="1800" height="1540" loading="lazy" alt="Four furnished buildings, each with a top-down camera map and four learned structural-edge overlays"></a><figcaption>Four furnished development buildings: top-down camera directions and acquired learned predictions. Exploration uses ideal RGB-D and known poses; maps remain partial.</figcaption></figure>
      <details><summary>Explore synthetic camera samples: four rooms, four overlays each</summary>
      <p class="rg-legend"><span>Mint: visible structure</span> · <span>Coral: hidden structure</span>. These synthetic labels come from scene geometry, not model predictions.</p>
      {"".join(rows)}
      <p class="rg-scroll-hint">On small screens, swipe each row to see all four overlays.</p>
      </details>
      <p>Learned perception includes visible robot arms and mirror reflections. The initial RGB-only reconstruction fits rectangular room shells using known poses and Manhattan axes; later RGB-D experiments map multiple connected spaces.</p>
      <p class="links"><a href="roomgraph/"><strong>Explore the complete RoomGraph project →</strong></a> · <a href="https://github.com/KiwooShin/roomgraph">Source code ↗</a></p>
    </article>

"""
    + content[end:]
)
homepage.write_text(content)
page = ROOT / "roomgraph/index.html"
content = page.read_text()
start, end = content.index("<!-- GALLERY START -->"), content.index("<!-- GALLERY END -->")
page.write_text(
    content[:start] + "<!-- GALLERY START -->\n" + "\n".join(sections) + "\n" + content[end:]
)
print("Updated the unified RoomGraph homepage entry and four detailed scene sections.")
