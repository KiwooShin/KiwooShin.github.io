'use strict';
(async () => {
  const canvas = document.getElementById('cloud');
  const context = canvas.getContext('2d');
  const status = document.getElementById('cloud-status');
  const controls = Object.fromEntries(['surfaces', 'edges', 'path', 'ceiling'].map(id => [id, document.getElementById(id)]));
  const selector = document.getElementById('case-select');
  let data = {surface: [], edges: [], path: []}, points = [], center = [0, 0, 1], span = 12;
  let generation = 0;
  async function loadCase() {
    const current = ++generation;
    status.textContent = 'Loading observed point data…';
    try {
      const response = await fetch(`../media/roomgraph-spaces/${encodeURIComponent(selector.value)}/cloud.json`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const incoming = await response.json();
      if (current !== generation) return;
      if (!Array.isArray(incoming.surface) || !Array.isArray(incoming.edges) || !Array.isArray(incoming.path)) throw new Error('Invalid point data');
      data = incoming; points = data.surface;
      const source = points.length ? points : data.edges;
      const low = [Infinity, Infinity], high = [-Infinity, -Infinity];
      for (const point of source) for (let axis = 0; axis < 2; axis++) {
        low[axis] = Math.min(low[axis], point[axis]); high[axis] = Math.max(high[axis], point[axis]);
      }
      center = source.length ? [(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, 1.1] : [0, 0, 1];
      span = source.length ? Math.max(5, high[0] - low[0], high[1] - low[1]) : 12;
      reset();
    } catch (error) {
      if (current !== generation) return;
      data = {surface: [], edges: [], path: []}; points = [];
      status.textContent = 'This map could not be loaded. The recorded replay and data download remain available.';
      context.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
  let yaw = -.6, pitch = .9, zoom = 1, drag = null, scheduled = false;
  const requestDraw = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(draw); } };
  function draw() {
    scheduled = false;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    const width = Math.round(canvas.clientWidth * ratio), height = Math.round(canvas.clientHeight * ratio);
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    context.fillStyle = '#142131'; context.fillRect(0, 0, width, height);
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const scale = Math.min(width, height * 1.6) * .76 / span * zoom;
    const project = point => {
      const x = point[0] - center[0], y = point[1] - center[1], z = (point[2] || 0) - center[2];
      const a = x * cy - y * sy, b = x * sy + y * cy;
      return [width / 2 + a * scale, height / 2 - (z * cp + b * sp) * scale, b * cp - z * sp];
    };
    const items = [];
    if (controls.surfaces.checked) for (const point of points) {
      if (!controls.ceiling.checked && point[2] >= 2.75) continue;
      items.push([project(point), `rgb(${point[3] | 0},${point[4] | 0},${point[5] | 0})`, 2]);
    }
    if (controls.edges.checked) for (const point of data.edges) {
      if (!controls.ceiling.checked && point[2] >= 2.75) continue;
      items.push([project(point), '#62edc1', 2.3]);
    }
    items.sort((a, b) => a[0][2] - b[0][2]);
    for (const [point, color, size] of items) {
      context.fillStyle = color; context.fillRect(point[0], point[1], size * ratio, size * ratio);
    }
    if (controls.path.checked && data.path.length) {
      context.strokeStyle = '#ffbd66'; context.lineWidth = 2 * ratio; context.beginPath();
      data.path.forEach((point, index) => { const p = project([point[0], point[1], .08]); if (index) context.lineTo(p[0], p[1]); else context.moveTo(p[0], p[1]); });
      context.stroke();
      const start = project([...data.path[0].slice(0, 2), .08]);
      context.fillStyle = '#fff'; context.beginPath(); context.arc(start[0], start[1], 4 * ratio, 0, Math.PI * 2); context.fill();
    }
    status.textContent = `${points.length.toLocaleString()} selected surface points · ${data.edges.length.toLocaleString()} selected learned edge points. Ceiling ${controls.ceiling.checked ? 'shown' : 'hidden'} for inspection.`;
  }
  function reset() { yaw = -.6; pitch = .9; zoom = 1; requestDraw(); }
  canvas.addEventListener('pointerdown', event => { drag = [event.clientX, event.clientY]; canvas.setPointerCapture(event.pointerId); });
  canvas.addEventListener('pointermove', event => {
    if (!drag) return;
    yaw += (event.clientX - drag[0]) * .008;
    pitch = Math.max(-1.55, Math.min(1.55, pitch + (event.clientY - drag[1]) * .008));
    drag = [event.clientX, event.clientY]; requestDraw();
  });
  canvas.addEventListener('pointerup', () => { drag = null; });
  canvas.addEventListener('pointercancel', () => { drag = null; });
  canvas.addEventListener('wheel', event => { event.preventDefault(); zoom = Math.max(.3, Math.min(4, zoom * Math.exp(-event.deltaY * .001))); requestDraw(); }, {passive:false});
  canvas.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') yaw -= .1;
    else if (event.key === 'ArrowRight') yaw += .1;
    else if (event.key === 'ArrowUp') pitch = Math.min(1.55, pitch + .1);
    else if (event.key === 'ArrowDown') pitch = Math.max(-1.55, pitch - .1);
    else if (event.key === '+' || event.key === '=') zoom = Math.min(4, zoom * 1.12);
    else if (event.key === '-') zoom = Math.max(.3, zoom / 1.12);
    else if (event.key === 'Home') reset();
    else return;
    event.preventDefault(); requestDraw();
  });
  for (const control of Object.values(controls)) control.addEventListener('change', requestDraw);
  document.getElementById('reset').addEventListener('click', reset);
  document.getElementById('top').addEventListener('click', () => { yaw = 0; pitch = Math.PI / 2; zoom = 1; requestDraw(); });
  new ResizeObserver(requestDraw).observe(canvas);
  selector.addEventListener('change', loadCase);
  for (const button of document.querySelectorAll('.map-link')) button.addEventListener('click', () => {
    selector.value = button.dataset.case; loadCase(); document.getElementById('map').scrollIntoView({behavior:'smooth'});
  });
  if (selector.options.length) await loadCase();
  else status.textContent = 'No completed observed point maps are available for the declared cases.';
})();
