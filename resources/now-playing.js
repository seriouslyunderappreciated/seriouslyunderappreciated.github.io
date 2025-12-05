/* now-playing.js
   Updates:
   - Each game's text is split into per-character spans (.np-char).
   - Per-character animation applied with staggered delays so letters form a traveling wave.
   - Per-item base phase offset is combined with per-letter staggering for variety.
   - Preserves diamond placement, center overlay behavior, and non-interactive settings.
*/

(async function () {
  const stage = document.getElementById('now-playing-stage');
  const itemsContainer = document.getElementById('now-playing-items');
  const label = document.getElementById('now-playing-label');
  if (!stage || !itemsContainer || !label) return;

  async function fetchLines() {
    try {
      const res = await fetch('resources/atm.txt', {cache: "no-store"});
      if (!res.ok) return [];
      const text = await res.text();
      return text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    } catch (e) {
      return [];
    }
  }

  function clearItems() {
    itemsContainer.innerHTML = '';
  }

  function makeCharsContainer(text, itemPhase, baseDuration, letterDelay) {
    // Create wrapper span containing per-character spans
    const charsWrapper = document.createElement('span');
    charsWrapper.className = 'np-chars';
    // iterate characters including spaces
    for (let i = 0; i < text.length; i++) {
      const ch = text[i] === ' ' ? '\u00A0' : text[i]; // use NBSP so whitespace is visible and preserved
      const chSpan = document.createElement('span');
      chSpan.className = 'np-char';
      chSpan.textContent = ch;
      // compute animation delay: combine itemPhase (so different items are phase-shifted around the diamond)
      // and per-letter staggering so letters ripple across the string.
      const delay = -(itemPhase + i * letterDelay);
      chSpan.style.animationDelay = `${delay}s`;
      // Use CSS variables as fallback/consistency:
      chSpan.style.setProperty('--np-wave-duration', `${baseDuration}s`);
      chSpan.style.setProperty('--np-wave-distance', getComputedStyle(document.documentElement)
        .getPropertyValue('--np-wave-distance') || '8px');
      charsWrapper.appendChild(chSpan);
    }
    return charsWrapper;
  }

  /*
    Diamond point mapping:
    Map u in [0,1) to perimeter of diamond as before.
  */
  function diamondPointByFraction(u, R) {
    u = (u % 1 + 1) % 1;
    const sideF = u * 4;
    const side = Math.floor(sideF);
    const t = sideF - side;
    let x = 0, y = 0;
    switch (side) {
      case 0: x = R * (1 - t); y = R * t; break;
      case 1: x = -R * t; y = R * (1 - t); break;
      case 2: x = -R * (1 - t); y = -R * t; break;
      case 3: x = R * t; y = -R * (1 - t); break;
    }
    return {x, y};
  }

  function createItemElement(text, idx, total, isCenter, peripheryIndex, peripheryCount) {
    const el = document.createElement('div');
    el.className = 'now-playing-item';
    if (isCenter) el.classList.add('center');
    // Non-interactive
    el.style.pointerEvents = 'none';
    el.style.userSelect = 'none';
    el.style.webkitUserSelect = 'none';

    // Per-item base phase (so each item's wave starts offset around the diamond)
    const baseDuration = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-wave-duration')) || 2.6;
    const itemPhase = (idx / Math.max(1, total)) * baseDuration;

    // letter delay (seconds)
    const letterDelay = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-letter-delay')) || 0.06;

    // Build chars wrapper with per-letter animation delays
    const chars = makeCharsContainer(text, itemPhase, baseDuration, letterDelay);
    el.appendChild(chars);

    return el;
  }

  function placeItems(titles) {
    clearItems();
    const n = titles.length;
    if (n === 0) {
      label.style.display = 'none';
      return;
    } else {
      label.style.display = '';
    }

    const hasCenter = (n % 2 === 1);
    const peripheryCount = hasCenter ? (n - 1) : n;

    const baseR = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-base-radius')) || 90;
    const maxR = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-max-radius')) || 140;

    // grow radius slightly with peripheryCount but cap at maxR
    const radius = Math.min(maxR, baseR + Math.max(0, peripheryCount - 4) * 6);

    let centerIdx = -1;
    if (hasCenter) centerIdx = Math.floor(n / 2);

    let peripheryIndex = 0;
    for (let i = 0; i < n; i++) {
      if (i === centerIdx) {
        const el = createItemElement(titles[i], i, n, true, -1, peripheryCount);
        el.style.left = '50%';
        el.style.top = '50%';
        el.style.zIndex = '4';
        el.style.transform = 'translate(-50%, -50%)';
        el.style.opacity = getComputedStyle(document.documentElement)
          .getPropertyValue('--np-center-opacity') || '0.96';
        itemsContainer.appendChild(el);
        continue;
      }

      const el = createItemElement(titles[i], peripheryIndex, peripheryCount, false, peripheryIndex, peripheryCount);

      const frac = peripheryIndex / peripheryCount;
      const pt = diamondPointByFraction(frac, radius);

      const px = pt.x;
      const py = pt.y;

      el.style.left = '50%';
      el.style.top = '50%';
      // Keep baseline centering via transform; use margins for pixel offsets to avoid transform conflicts with per-letter animations
      el.style.marginLeft = `${px}px`;
      el.style.marginTop = `${py}px`;
      el.style.zIndex = '2';

      itemsContainer.appendChild(el);
      peripheryIndex++;
    }
  }

  const lines = await fetchLines();
  placeItems(lines);

  let pollInterval = 6000;
  setInterval(async () => {
    const newLines = await fetchLines();
    if (newLines.length === 0 && lines.length === 0) return;
    const same = newLines.length === lines.length && newLines.every((v,i) => v === lines[i]);
    if (!same) placeItems(newLines);
  }, pollInterval);

})();
