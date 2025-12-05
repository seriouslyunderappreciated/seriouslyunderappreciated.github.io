/* now-playing.js
   - Fetches /atm.txt (one title per line).
   - Builds the diamond-shaped layout around logo.png.
   - If atm.txt is empty, hides the whole label (and shows nothing).
   - If odd count, places the middle item centered on the logo (overlay).
   - Non-interactive text; wave animation applied with phase shifts.
*/

(async function () {
  const stage = document.getElementById('now-playing-stage');
  const itemsContainer = document.getElementById('now-playing-items');
  const label = document.getElementById('now-playing-label');
  if (!stage || !itemsContainer || !label) return;

  async function fetchLines() {
    try {
      const res = await fetch('/atm.txt', {cache: "no-store"});
      if (!res.ok) return [];
      const text = await res.text();
      // split on newlines, trim and filter out empties
      return text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    } catch (e) {
      // fail silently; return empty
      return [];
    }
  }

  function clearItems() {
    itemsContainer.innerHTML = '';
  }

  function createItemElement(text, idx, total, isCenter) {
    const el = document.createElement('div');
    el.className = 'now-playing-item';
    if (isCenter) el.classList.add('center');
    el.textContent = text;
    // Make non-interactive
    el.style.pointerEvents = 'none';
    el.style.userSelect = 'none';
    el.style.webkitUserSelect = 'none';

    // Wave animation: phase shift based on index
    const baseDuration = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-wave-duration')) || 2.6;
    const phase = (idx / Math.max(1, total));
    el.style.animation = `np-wave ${baseDuration}s ease-in-out infinite`;
    el.style.animationDelay = `-${(phase * baseDuration).toFixed(3)}s`;

    return el;
  }

  /*
    Diamond parameterization:
    - We map u in [0,1) to the perimeter of a diamond (rotated square).
    - Diamond perimeter is split into 4 sides:
      side 0: (R,0) -> (0,R)
      side 1: (0,R) -> (-R,0)
      side 2: (-R,0) -> (0,-R)
      side 3: (0,-R) -> (R,0)
    - For each point we compute x,y in pixels relative to center.
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

    // Compute radius: grows slightly with peripheryCount but capped
    const baseR = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-base-radius')) || 90;
    const maxR = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--np-max-radius')) || 140;

    // Use a modest growth so things stay close:
    // radius = baseR + scaled(peripheryCount)
    const radius = Math.min(maxR, baseR + Math.max(0, peripheryCount - 4) * 6);

    // If there's a center item, pick the middle title as center
    let centerIdx = -1;
    if (hasCenter) centerIdx = Math.floor(n / 2);

    // Build elements for periphery
    let peripheryIndex = 0;
    for (let i = 0; i < n; i++) {
      if (i === centerIdx) {
        // center overlay
        const el = createItemElement(titles[i], i, n, true);
        // center in the stage; placed with transform translate(-50%, -50%)
        el.style.left = '50%';
        el.style.top = '50%';
        el.style.zIndex = '4';
        el.style.transform = 'translate(-50%, -50%)';
        // Slightly reduce opacity to let logo show through
        el.style.opacity = '0.96';
        itemsContainer.appendChild(el);
        continue;
      }

      const el = createItemElement(titles[i], peripheryIndex, peripheryCount, false);

      // fraction around diamond
      const frac = peripheryIndex / peripheryCount;
      const pt = diamondPointByFraction(frac, radius);

      // optionally, push items slightly outward by a small factor depending on how far from center
      const distanceFactor = 1.0; // keep near by default; adjust if you want more spread

      const px = pt.x * distanceFactor;
      const py = pt.y * distanceFactor;

      // Position using left/top percent + pixel offsets via transform
      // We'll set style.transform to translate(-50%,-50%) and then translate by pixel offsets inside translate
      el.style.left = '50%';
      el.style.top = '50%';
      // combine with animation translateY applied by keyframes; but we want baseline offset in transform as well.
      // We'll set an inline transform that will be combined with animation (animations override entire transform),
      // so use a wrapper approach: put offsets as CSS custom properties and use translate in keyframes.
      // Simpler approach: set el.style.transform to include the pixel offset, then animate using translateY in keyframes which also sets translate(-50%, -50%), so we will instead emulate wave by animating translateY only and keep offsets via CSS vars.
      // To keep compatibility, we'll set a CSS variable that keyframes use; but for simplicity, set transform with offset and then apply animation that toggles translateY using calc with var fallback.
      // We'll construct a transform string that includes translate by px offset and a placeholder for wave; keyframes will fully set transform to translate(-50%, calc(-50% +/- wave)), so we need animation to not overwrite the px offset. To keep it simple across browsers, we rely on animation doing translateY relative to current computed transform via translateY only (many browsers will replace transform). To avoid cross-browser complexity, we'll apply animation on a child; but dynamic DOM complexity increases.
      // Simpler and robust: apply pixel offsets via style.marginLeft/marginTop instead of transform, then use animation that animates transform translateY. That keeps offsets independent.
      el.style.marginLeft = `${px}px`;
      el.style.marginTop = `${py}px`;
      // set an initial transform baseline
      el.style.transform = 'translate(-50%, -50%)';
      el.style.zIndex = '2';

      itemsContainer.appendChild(el);
      peripheryIndex++;
    }
  }

  // initial load
  const lines = await fetchLines();
  placeItems(lines);

  // optional: watch for updates every 6 seconds
  let pollInterval = 6000;
  setInterval(async () => {
    const newLines = await fetchLines();
    // quick equality check
    if (newLines.length === 0 && lines.length === 0) return;
    const same = newLines.length === lines.length && newLines.every((v,i) => v === lines[i]);
    if (!same) placeItems(newLines);
  }, pollInterval);

})();