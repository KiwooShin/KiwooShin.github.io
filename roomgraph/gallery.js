'use strict';
let stopActiveTour = null;
for (const room of document.querySelectorAll('.room')) {
  const cards = [...room.querySelectorAll('.camera-card button')];
  const image = room.querySelector('.main-image');
  const full = room.querySelector('.full-image');
  const play = room.querySelector('.play');
  const modes = [...room.querySelectorAll('[data-mode]')];
  let index = 0, mode = 'overlay', timer = null;
  function show(next) {
    index = (next + cards.length) % cards.length;
    const card = cards[index];
    image.src = card.dataset[mode];
    image.alt = `${room.dataset.title}, ${card.dataset.camera}, ${mode === 'overlay' ? 'architectural edge overlay' : 'rendered RGB'}`;
    full.href = image.src;
    room.querySelector('.camera-name').textContent = `${card.dataset.camera} / ${cards.length} views`;
    room.querySelector('.camera-position').textContent = card.dataset.position;
    cards.forEach((button, i) => button.setAttribute('aria-pressed', i === index));
    room.querySelectorAll('.map-frame g').forEach((marker, i) => marker.classList.toggle('active', i === index));
  }
  function stop() {
    clearInterval(timer); timer = null;
    play.textContent = '▶ Play camera sequence';
    play.setAttribute('aria-pressed', 'false');
  }
  cards.forEach((button, i) => button.addEventListener('click', () => { stop(); show(i); }));
  modes.forEach(button => button.addEventListener('click', () => {
    mode = button.dataset.mode;
    modes.forEach(b => b.setAttribute('aria-pressed', b === button));
    show(index);
  }));
  play.addEventListener('click', () => {
    if (timer) { stop(); return; }
    if (stopActiveTour) stopActiveTour();
    stopActiveTour = stop;
    timer = setInterval(() => show(index + 1), 1800);
    play.textContent = 'Ⅱ Pause sequence';
    play.setAttribute('aria-pressed', 'true');
  });
  room.querySelector('.previous').addEventListener('click', () => { stop(); show(index - 1); });
  room.querySelector('.next').addEventListener('click', () => { stop(); show(index + 1); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
}

// Keep one walkthrough playing at a time.
const videos = [...document.querySelectorAll('.walkthrough video')];
videos.forEach(video => video.addEventListener('play', () => {
  videos.forEach(other => { if (other !== video) other.pause(); });
}));
