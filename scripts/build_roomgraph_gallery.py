"""Regenerate RoomGraph's static homepage rows and detailed camera gallery."""

# HTML fragments intentionally keep complete tags together.
# ruff: noqa: E501

import html
import json
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
start = content.index('    <article class="project" id="roomgraph">')
end = content.index('    <article class="project" id="calibration-recovery">', start)
content = (
    content[:start]
    + f"""    <article class="project" id="roomgraph">
      <h3><a href="roomgraph/">RoomGraph — Synthetic Indoor Structure</a></h3>
      <p>Recover the shape of an indoor space from its images. RoomGraph uses Isaac Sim on NVIDIA DGX Spark to generate furnished interiors with calibrated cameras, depth, and architectural edge ground truth.</p>
      <div class="tags"><span>3D vision</span><span>synthetic data</span><span>Isaac Sim</span><span>DGX Spark</span></div>
      <p class="rg-legend"><span>Mint: visible structure</span> · <span>Coral: hidden structure</span>. Labels come from scene geometry.</p>
      {"".join(rows)}
      <p class="rg-scroll-hint">On small screens, swipe each row to see all four overlays.</p>
      <figure class="featured"><a href="roomgraph/#living"><picture><source media="(prefers-reduced-motion: reduce)" srcset="media/roomgraph/furnished/living/walkthrough-poster.webp"><img src="media/roomgraph/furnished/living/walkthrough.gif" width="768" height="384" loading="lazy" alt="Moving camera in a furnished living room, with a continuous structural-edge overlay and synchronized top-down camera marker"></picture></a><figcaption>Continuous moving-camera walkthrough. Explore four rooms, 32 detailed views, and camera-path videos on the project page.</figcaption></figure>
      <p class="links"><a href="roomgraph/"><strong>Detailed project page &amp; interactive gallery →</strong></a> · <a href="https://github.com/KiwooShin/roomgraph">Source code ↗</a></p>
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
print("Updated four homepage rows and four detailed scene sections.")
