// SPHEREx Sky Blink: Tasks 1-5.
// Only uses what API_GUIDE.md describes:
//   GET /api/targets?year=2026   -> the 5 preset targets
//   GET /api/frames?ra=&dec=     -> list of frames, each with a ready-to-use image_url

// ---------------------------------------------------------------
// 1. Grab the page elements we need
// ---------------------------------------------------------------
const skyImage = document.getElementById("sky-image");
const stageMessage = document.getElementById("stage-message");
const statusLine = document.getElementById("status");

const coordForm = document.getElementById("coord-form");
const raInput = document.getElementById("ra-input");
const decInput = document.getElementById("dec-input");

const nameForm = document.getElementById("name-form");
const nameInput = document.getElementById("name-input");

const playButton = document.getElementById("play-button");
const slider = document.getElementById("frame-slider");
const speedSelect = document.getElementById("speed-select");

// ---------------------------------------------------------------
// 2. Things the page remembers
// ---------------------------------------------------------------
let frames = [];        // the frame list from /api/frames
let currentIndex = 0;   // which frame is on screen
let timer = null;       // the setInterval id while playing (null = paused)
let targets = [];       // the 5 presets from /api/targets
let latestRequest = 0;  // so an old, slow answer cannot replace a newer one

// ---------------------------------------------------------------
// 3. Small helpers
// ---------------------------------------------------------------

// Show a message under the player. isError = true makes it red.
function setStatus(text, isError = false) {
  statusLine.textContent = text;
  statusLine.classList.toggle("error", isError);
}

// Ask the server for JSON. If the server answers with an error,
// throw an Error whose message is the friendly "detail" sentence.
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
    // The body was not JSON; we handle that below.
  }

  if (!response.ok) {
    throw new Error(
      data && data.detail ? data.detail : "Something went wrong (code " + response.status + ")."
    );
  }
  return data;
}

// Make a name easy to compare: lower case, and no spaces, hyphens or apostrophes.
// "Barnard's Star" and "barnards star" both become "barnardsstar".
function simplifyName(text) {
  return String(text).toLowerCase().replace(/[\s'’`\-_]/g, "");
}

// ---------------------------------------------------------------
// 4. Task 2: show one image
// ---------------------------------------------------------------
function showFrame(index) {
  currentIndex = index;
  const frame = frames[index];
  skyImage.src = frame.image_url; // image_url is ready to use: never build it ourselves
  skyImage.alt = "Sky image taken " + frame.obs_time;
  skyImage.hidden = false;
  stageMessage.hidden = true;
  slider.value = String(index);
}

// ---------------------------------------------------------------
// 5. Task 3: load the frames for a position
// ---------------------------------------------------------------
async function loadFrames(ra, dec) {
  const thisRequest = ++latestRequest;
  pause();
  setStatus("Loading...");

  // URLSearchParams encodes special characters (like "+") for us.
  const params = new URLSearchParams({ ra: ra, dec: dec });

  try {
    const data = await fetchJson("/api/frames?" + params.toString());
    if (thisRequest !== latestRequest) return; // a newer request replaced this one

    frames = data.frames;
    if (frames.length === 0) {
      throw new Error("No images were returned for this position.");
    }

    // Preload every picture so the animation does not flicker.
    frames.forEach((frame) => {
      const preload = new Image();
      preload.src = frame.image_url;
    });

    // Set up the slider for the new list.
    slider.max = String(frames.length - 1);
    slider.disabled = frames.length < 2;
    playButton.disabled = frames.length < 2;

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
    setStatus(error.message, true); // the server's friendly sentence, shown as it is
  }
}

coordForm.addEventListener("submit", (event) => {
  event.preventDefault(); // stop the page from reloading
  // We send the text exactly as typed: the server understands degrees and sexagesimal.
  loadFrames(raInput.value.trim(), decInput.value.trim());
});

// ---------------------------------------------------------------
// 6. Task 4: search by name (only the 5 presets, from /api/targets)
// ---------------------------------------------------------------
async function loadTargets() {
  try {
    const data = await fetchJson("/api/targets?year=2026");
    targets = data.targets;
  } catch (error) {
    setStatus("Name search is unavailable: " + error.message, true);
  }
}

// Does the typed name match a preset's id, label or SIMBAD name?
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

nameForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const target = findTarget(nameInput.value);
  if (!target) {
    const known = targets.map((t) => t.label).join(", ");
    setStatus(
      "Name not found. For now only these targets work by name: " + known + ".",
      true
    );
    return;
  }
  // Fill the RA/Dec boxes so the person can see the numbers, then load.
  raInput.value = target.ra_deg;
  decInput.value = target.dec_deg;
  loadFrames(String(target.ra_deg), String(target.dec_deg));
});

// ---------------------------------------------------------------
// 7. Task 5: animation player
// ---------------------------------------------------------------
function nextFrame() {
  // After the last frame, go back to the first (the animation loops).
  showFrame((currentIndex + 1) % frames.length);
}

function play() {
  if (frames.length < 2) return;
  pause(); // never run two timers at once
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

playButton.addEventListener("click", () => {
  if (timer === null) {
    play();
  } else {
    pause();
  }
});

// Dragging the slider pauses the animation and jumps to that frame.
slider.addEventListener("input", () => {
  pause();
  showFrame(Number(slider.value));
});

// Changing the speed while playing restarts the timer at the new speed.
speedSelect.addEventListener("change", () => {
  if (timer !== null) {
    play();
  }
});

// ---------------------------------------------------------------
// 8. When the page opens
// ---------------------------------------------------------------
// Load the presets, then fill the boxes with WISE 0855 and show it,
// so there is something on screen to test with. (Preset buttons are Task 8.)
async function start() {
  await loadTargets();
  const wise = targets.find((t) => t.id === "wise0855");
  if (wise) {
    raInput.value = wise.ra_deg;
    decInput.value = wise.dec_deg;
    loadFrames(String(wise.ra_deg), String(wise.dec_deg));
  }
}
start();