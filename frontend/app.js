// SPHEREx Sky Blink: Tasks 1-14.
// Only uses what API_GUIDE.md describes:
//   GET /api/targets?year=2026   -> the 5 preset targets
//   GET /api/limits              -> FOV min / max / default (arcminutes)
//   GET /api/frames?ra=&dec=&fov= -> frame list, each with a ready-to-use image_url

// ---------------------------------------------------------------
// 1. Page elements
// ---------------------------------------------------------------
const skyImage = document.getElementById("sky-image");
const stage = document.getElementById("stage");
const stageMessage = document.getElementById("stage-message");
const statusLine = document.getElementById("status");
const spinner = document.getElementById("spinner");

const coordForm = document.getElementById("coord-form");
const raInput = document.getElementById("ra-input");
const decInput = document.getElementById("dec-input");
const fovSelect = document.getElementById("fov-select");

const nameForm = document.getElementById("name-form");
const nameInput = document.getElementById("name-input");

const playButton = document.getElementById("play-button");
const slider = document.getElementById("frame-slider");
const speedSelect = document.getElementById("speed-select");
const counter = document.getElementById("frame-counter");
const loopToggle = document.getElementById("loop-toggle");

const waveStrip = document.getElementById("wave-strip");
const stripMin = document.getElementById("strip-min");
const stripMax = document.getElementById("strip-max");

const presetList = document.getElementById("preset-list");
const copyButton = document.getElementById("copy-link");

const info = {
  date: document.getElementById("info-date"),
  detector: document.getElementById("info-detector"),
  wave: document.getElementById("info-wave"),
  stacked: document.getElementById("info-stacked"),
  source: document.getElementById("info-source"),
};

// ---------------------------------------------------------------
// 2. Things the page remembers
// ---------------------------------------------------------------
let frames = [];
let currentIndex = 0;
let timer = null;
let targets = [];
let latestRequest = 0;
let source = ""; // the "source" label from /api/frames

// ---------------------------------------------------------------
// 3. Small helpers
// ---------------------------------------------------------------
function setStatus(text, isError = false) {
  statusLine.textContent = text;
  statusLine.classList.toggle("error", isError);
}

// Ask the server for JSON; on an error, throw the friendly "detail" sentence.
async function fetchJson(url) {
  let response;
  try {
    response = await fetch(url);
  } catch (networkError) {
    throw new Error(
      "Could not reach the server. Check that it is running (uvicorn main:app --reload)."
    );
  }
  let data = null;
  try {
    data = await response.json();
  } catch (parseError) {
    // body was not JSON
  }
  if (!response.ok) {
    throw new Error(
      data && data.detail ? data.detail : "Something went wrong (code " + response.status + ")."
    );
  }
  return data;
}

// "Barnard's Star" and "barnards star" both become "barnardsstar".
function simplifyName(text) {
  return String(text).toLowerCase().replace(/[\s'’`\-_]/g, "");
}

// ---------------------------------------------------------------
// 4. Show one frame (Tasks 2, 6, 12, 13)
// ---------------------------------------------------------------
function showFrame(index) {
  currentIndex = index;
  const frame = frames[index];
  skyImage.src = frame.image_url; // ready to use: never build it ourselves
  skyImage.alt = "Sky image taken " + frame.obs_time;
  skyImage.hidden = false;
  stageMessage.hidden = true;
  slider.value = String(index);

  // Task 6: counter "5 / 12"
  counter.textContent = index + 1 + " / " + frames.length;

  // Task 12: info panel
  info.date.textContent = frame.obs_time;
  // API_GUIDE: detector 0 means "several detectors stacked"
  info.detector.textContent = frame.detector === 0 ? "several (stacked)" : frame.detector;
  info.wave.textContent = Number(frame.wavelength_um).toFixed(3) + " µm";
  info.stacked.textContent = frame.n_stacked;
  info.source.textContent = source;

  // Task 13: highlight this frame in the colour strip
  Array.from(waveStrip.children).forEach((block, i) => {
    block.classList.toggle("current", i === index);
  });
}

function clearInfo() {
  counter.textContent = "0 / 0";
  Object.values(info).forEach((el) => (el.textContent = "-"));
  waveStrip.replaceChildren();
  stripMin.textContent = "";
  stripMax.textContent = "";
}

// ---------------------------------------------------------------
// 5. Task 13: wavelength colour strip
// ---------------------------------------------------------------
// One coloured block per frame. Short wavelength = violet, long = red.
function buildStrip() {
  waveStrip.replaceChildren();
  const waves = frames.map((f) => Number(f.wavelength_um));
  const low = Math.min(...waves);
  const high = Math.max(...waves);
  frames.forEach((frame, i) => {
    const t = high > low ? (frame.wavelength_um - low) / (high - low) : 0;
    const block = document.createElement("button");
    block.type = "button";
    block.style.background = "hsl(" + Math.round(270 - 270 * t) + ", 85%, 55%)";
    const label = "Frame " + (i + 1) + ": " + Number(frame.wavelength_um).toFixed(2) + " µm";
    block.title = label;
    block.setAttribute("aria-label", label);
    block.addEventListener("click", () => {
      pause();
      showFrame(i);
    });
    waveStrip.appendChild(block);
  });
  stripMin.textContent = low.toFixed(2) + " µm";
  stripMax.textContent = high.toFixed(2) + " µm";
}

// ---------------------------------------------------------------
// 6. Load the frames for a position (Tasks 3, 9, 11, 14)
// ---------------------------------------------------------------
function currentParams(ra, dec) {
  // URLSearchParams encodes special characters (like "+") for us.
  const params = new URLSearchParams({ ra: ra, dec: dec });
  if (fovSelect.value) params.set("fov", fovSelect.value);
  return params;
}

async function loadFrames(ra, dec) {
  const thisRequest = ++latestRequest;
  pause();
  setStatus("Loading...");
  spinner.hidden = false; // Task 14

  const params = currentParams(ra, dec);
  // Task 9: put the settings in the page address (same names as the API)
  history.replaceState(null, "", "?" + params.toString());

  try {
    const data = await fetchJson("/api/frames?" + params.toString());
    if (thisRequest !== latestRequest) return;

    frames = data.frames;
    source = data.source;
    if (frames.length === 0) {
      throw new Error("No images were returned for this position.");
    }

    // Preload every picture so the animation does not flicker.
    frames.forEach((frame) => {
      const preload = new Image();
      preload.src = frame.image_url;
    });

    slider.max = String(frames.length - 1);
    slider.disabled = frames.length < 2;
    playButton.disabled = frames.length < 2;

    buildStrip();
    showFrame(0);
    setStatus("Loaded " + frames.length + " frames (source: " + data.source + ").");
  } catch (error) {
    if (thisRequest !== latestRequest) return;
    frames = [];
    skyImage.hidden = true;
    stageMessage.hidden = false;
    stageMessage.textContent = "No image to show.";
    slider.disabled = true;
    playButton.disabled = true;
    clearInfo();
    setStatus(error.message, true);
  } finally {
    if (thisRequest === latestRequest) spinner.hidden = true;
  }
}

coordForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadFrames(raInput.value.trim(), decInput.value.trim());
});

// ---------------------------------------------------------------
// 7. Targets: name search (Task 4) and preset buttons (Task 8)
// ---------------------------------------------------------------
async function loadTargets() {
  try {
    const data = await fetchJson("/api/targets?year=2026");
    targets = data.targets;
  } catch (error) {
    setStatus("Targets are unavailable: " + error.message, true);
  }
}

function findTarget(typedName) {
  const wanted = simplifyName(typedName);
  if (!wanted) return null;
  return (
    targets.find(
      (t) =>
        simplifyName(t.id) === wanted ||
        simplifyName(t.label) === wanted ||
        simplifyName(t.simbad_name) === wanted
    ) || null
  );
}

function goToTarget(target) {
  raInput.value = target.ra_deg;
  decInput.value = target.dec_deg;
  loadFrames(String(target.ra_deg), String(target.dec_deg));
}

nameForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const target = findTarget(nameInput.value);
  if (!target) {
    const known = targets.map((t) => t.label).join(", ");
    setStatus("Name not found. For now only these targets work by name: " + known + ".", true);
    return;
  }
  goToTarget(target);
});

// Task 8: one button per target, straight from /api/targets
function buildPresets() {
  presetList.replaceChildren();
  targets.forEach((target) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = target.label;
    if (target.note) button.title = target.note;
    button.addEventListener("click", () => goToTarget(target));
    presetList.appendChild(button);
  });
}

// ---------------------------------------------------------------
// 8. Task 11: field-of-view dropdown (limits come from /api/limits)
// ---------------------------------------------------------------
async function loadLimits() {
  try {
    const data = await fetchJson("/api/limits");
    const { min, max, default: def } = data.fov_arcmin;
    // Some handy sizes inside the allowed range, plus min, default and max.
    const sizes = [min, 3, def, 10, 15, max].filter((v) => v >= min && v <= max);
    const unique = Array.from(new Set(sizes)).sort((a, b) => a - b);
    fovSelect.replaceChildren();
    unique.forEach((value) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = value + (value === def ? " (default)" : "");
      fovSelect.appendChild(option);
    });
    fovSelect.value = String(def);
  } catch (error) {
    // Keep the single "Default" option; the server then uses its own default.
    setStatus("Zoom control unavailable: " + error.message, true);
  }
}

// Changing the size reloads the frames at the same position.
fovSelect.addEventListener("change", () => {
  if (raInput.value.trim() && decInput.value.trim()) {
    loadFrames(raInput.value.trim(), decInput.value.trim());
  }
});

// ---------------------------------------------------------------
// 9. Animation player (Tasks 5, 6, 7)
// ---------------------------------------------------------------
function nextFrame() {
  const last = frames.length - 1;
  if (currentIndex >= last && !loopToggle.checked) {
    pause(); // Task 6: loop is off, so stop at the end
    return;
  }
  showFrame((currentIndex + 1) % frames.length);
}

function play() {
  if (frames.length < 2) return;
  pause();
  // If loop is off and we are at the end, start again from the beginning.
  if (currentIndex >= frames.length - 1 && !loopToggle.checked) showFrame(0);
  timer = setInterval(nextFrame, Number(speedSelect.value));
  playButton.textContent = "Pause";
}

function pause() {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
  playButton.textContent = "Play";
}

function togglePlay() {
  if (timer === null) play();
  else pause();
}

// Task 7: step one frame back (-1) or forward (+1), wrapping round.
function step(direction) {
  if (frames.length < 2) return;
  pause();
  showFrame((currentIndex + direction + frames.length) % frames.length);
}

playButton.addEventListener("click", togglePlay);

slider.addEventListener("input", () => {
  pause();
  showFrame(Number(slider.value));
});

speedSelect.addEventListener("change", () => {
  if (timer !== null) play();
});

// Task 7: keyboard. Space = play/pause, arrows = step.
document.addEventListener("keydown", (event) => {
  const el = event.target;
  // Leave typing boxes, dropdowns and the slider alone (they use these keys).
  if (el.matches("input[type=text], input[type=range], select, textarea")) return;
  if (event.code === "Space") {
    if (el.tagName === "BUTTON") return; // a focused button handles Space itself
    event.preventDefault(); // stop the page from scrolling
    togglePlay();
  } else if (event.key === "ArrowRight") {
    step(1);
  } else if (event.key === "ArrowLeft") {
    step(-1);
  }
});

// Task 7: swipe on the picture (phones). Left = next, right = previous.
let touchStartX = null;
stage.addEventListener("touchstart", (event) => {
  touchStartX = event.touches[0].clientX;
}, { passive: true });
stage.addEventListener("touchend", (event) => {
  if (touchStartX === null) return;
  const dx = event.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  if (Math.abs(dx) < 40) return; // too short: a tap, not a swipe
  step(dx < 0 ? 1 : -1);
});

// ---------------------------------------------------------------
// 10. Task 10: copy link
// ---------------------------------------------------------------
copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(window.location.href);
    setStatus("Link copied.");
  } catch (error) {
    // Clipboard can be blocked (for example on plain http outside localhost).
    setStatus("Could not copy. Copy the address from the browser bar instead.", true);
  }
});

// ---------------------------------------------------------------
// 11. When the page opens (Task 9 reads the URL here)
// ---------------------------------------------------------------
async function start() {
  await Promise.all([loadTargets(), loadLimits()]);
  buildPresets();

  const url = new URLSearchParams(window.location.search);
  const ra = url.get("ra");
  const dec = url.get("dec");

  // Use the link's fov only if it is one of the dropdown choices.
  const fov = url.get("fov");
  if (fov && Array.from(fovSelect.options).some((o) => o.value === fov)) {
    fovSelect.value = fov;
  }

  if (ra && dec) {
    raInput.value = ra;
    decInput.value = dec;
    loadFrames(ra, dec);
  } else {
    // No coordinates in the link: show WISE 0855 so there is something to see.
    const wise = targets.find((t) => t.id === "wise0855");
    if (wise) goToTarget(wise);
  }
}
start();