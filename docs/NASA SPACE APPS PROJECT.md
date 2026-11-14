##### NASA SPACE APPS PROJECT

#####

##### Simple Explanation of the Problem Statement

Imagine taking pictures of the entire night sky every six months. Because Earth orbits the sun and things in space move (like asteroids, comets, and nearby stars), objects change their positions or brightness over time.

NASA’s SPHEREx mission is capturing over a billion objects in infrared light, creating a massive treasure trove of data that no single person can look through alone.

Your Challenge: Build an easy-to-use, public-facing web tool. When a user types in coordinates of a patch of the sky (Right Ascension and Declination), your tool fetches images taken at different times and plays them back like a short video, making it super easy to spot moving or changing objects!

What SPHEREx Does: It maps the whole sky every six months using 102 bands of near-infrared light, making it great for spotting things rich in water, ice, and molecules.

Why Motion Matters: Tracking how objects shift helps discover new asteroids, comets, brown dwarfs, and measure distances in space.

The Test Targets: Your tool should be tested on specific fascinating space objects:

&#x09;WISE 0855: A very fast-moving, extremely faint brown dwarf.

&#x09;Barnard’s Star: A bright star with fast proper motion.

&#x09;Epsilon Indi B: A brown dwarf pair orbiting a star.

&#x09;RW Aurigae \& R Draconis: Variable stars that change in brightness rather than moving across the sky.

##### What we’re building

NASA has a space telescope called SPHEREx. It photographs the whole sky, then does it again six months later. If you compare photos of the same patch of sky taken on different dates, things that moved or changed stand out. That’s how Pluto was discovered.

We’re building a website where someone types a spot in the sky and sees those photos played like a short video. A dot that jumps from frame to frame is something moving: a comet, an asteroid, a nearby star, or a brown dwarf (a failed star).

###### Terms you’ll meet

RA / Dec: the sky’s version of longitude and latitude. Two numbers that point to a spot.

FOV (field of view): how wide a patch of sky you look at. Zoom in or zoom out.

FITS file: the file format astronomers use for images. It’s a picture plus extra information.

WCS: a rule inside the file that converts “pixel 40, 60 in the picture” into “RA/Dec in the sky”.

Frame: one photo plus its date, wavelength and extras.

Mock data: fake practice data we make ourselves.

Cutout: a small piece cropped from a big image.

Stretch: adjusting brightness so faint things become visible.

Proper motion: how fast a star drifts across the sky over the years.

Flags: labels marking bad or unreliable pixels.

API / backend: the behind-the-scenes program that does the work. The frontend is the web page you see.

###### The plan: four stages

Think of it like a restaurant. Data is the ingredients, processing is the kitchen, the API is the waiter, and the web page is the table.

Web page → API → Processing → Data

Each part only talks to the next one, so we can fix one without breaking the rest.

**Phase 1:** Before the real data (where we are now)

We don’t have real SPHEREx data yet, so we build everything using fake data.

**NASA wants:** a public website where anyone types a spot in the sky (RA and Dec, like a sky address) and sees the pictures of that spot played like a tiny video. If a dot jumps around, it’s moving. They will test it on 5 things: Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis.

######

###### What a “good solution” looks like to them

- Easy enough for a normal person, not only scientists.
- Fast.
- Easy to update when new data arrives.
- Link-shareable and embeddable in other sites.
- Smart use of the 102 colors (bands) of infrared light.

###### Backend (the behind-the-scenes work)

Workflow files: notes and rules so we never lose track. (Done)

Verify the 5 targets: look up exact coordinates for Barnard’s Star, WISE 0855, etc. (Done)

Mock data generator: make 12 fake sky images with one moving dot. (Done)

Mock flags and noise: add fake bad pixels and noise to practice with. (Done)

Cutout, stretch, PNG: crop a patch, adjust brightness, save as a picture. (Done)

Config switch: one setting to flip between fake and real data. (File exists; this is your next step) (Done)

Cache: save finished results so repeat requests are instant.

Frames endpoint: a web address that returns the list of images and their info.

URL parameters and validation: let the address carry the coordinates, and reject nonsense like Dec = 200.

Targets endpoint: send the 5 preset targets to the page.

Friendly errors: clear messages instead of crashes.

FOV handling: zoom in and out with sensible limits.

Difference imaging: subtract one image from another so only changes remain. Moving things pop out.

Stacking: add images together to reduce noise and see faint things.

Real data skeleton: empty, documented code ready for the real data.

Try one real query by hand: practice fetching real WISE 0855 data and note what we learn.

Easy-update design: so new data releases need only a one-line change.

Flags and metadata: decode what the pixel labels mean.

Spectrum function: a graph of brightness vs. color (wavelength) for a point.

Overlay function: mark known stars from other telescopes (Gaia, WISE).

GIF export: save the animation as a shareable GIF.

Tests: small checks that prove each part works.

README: instructions for others.

###### Frontend (the web page)

Page skeleton: the basic layout.

Show one image: display a single picture.

RA/Dec form: type coordinates, press Go, image changes.

Animation player: play/pause, slider and speed control.

Preset buttons: one click per test target.

URL parameters: coordinates live in the link, so it’s shareable.

FOV control: zoom dropdown.

Frame info panel: shows date, detector, wavelength.

Spinner and errors: “loading...” and friendly messages.

Stretch control: brightness slider.

Mode switch: Normal / Difference / Stack buttons.

Embed mode: a stripped-down version to put inside other websites.

Marker tool: click to circle an object and follow it.

GIF download button.

Placeholders: empty spaces reserved for spectrum, flags and overlays.

Design and mobile layout: dark theme, works on phones.

Beginner tutorial: “how to spot a moving object”.

**Phase 2:** After the real data arrives

Now we swap fake for real, then fix whatever differs.

###### Backend

Inspect real files: see what’s actually inside them.

Real image search: ask NASA’s archive (IRSA) which images cover a spot.

Real cutout download: fetch only the small piece we need.

Read real cutouts: put them into our standard frame format.

Wavelength map: read the color of each pixel.

Contract test: confirm real and fake frames look identical to our code.

Cleaning: handle empty pixels and mask bad ones.

Sort, group, limit: order by date, group by detector, cap the count.

Robust downloading: retries, longer timeouts, handling “no images”.

Edge cases: targets near image edges, different pointings.

WISE 0855 first: test the hardest target end to end and check the motion matches its known speed.

All 5 targets: confirm each one works.

Retune processing: adjust brightness and difference settings for real values.

Real flags: use the true meaning of the pixel labels.

Real spectra: graph from real wavelength data.

Real overlays: show Gaia/WISE stars, accounting for their movement.

Update path: switching to a newer data release is a one-line change.

Performance: measure speed, limit big requests, pre-save the 5 targets for demos.

Public hosting plan: choose where to put it online safely.

Update docs and commit.

###### Frontend

Switch to real data and check every button still works.

Real frame info (true date, detector, wavelength, quality).

Wavelength warning: so a color change isn’t mistaken for a real change.

Retune the brightness slider for real data.

Slow-load handling: progress text, cancel and retry.

No-data message for empty spots.

Preset check: each target shows what we expect.

Speed and frame order: a default speed that makes small shifts visible.

Difference and stack views: tune so moving objects pop out.

Marker test: confirm it tracks WISE 0855 and Barnard’s Star.

Flags display: real legend, highlight bad pixels.

Spectrum plot: real axes and units.

Overlays: toggle Gaia/WISE markers and check they line up.

GIF download test.

Embed and URL test inside another page.

Mobile and design polish on a real phone.

Tutorial update with real screenshots and a WISE 0855 example.

Demo materials: a video, screenshots and a short script for the judges.

## The finish line

Someone opens your website, clicks WISE 0855, presses play, and watches a faint dot drift across the sky. That’s the whole project.

##### The full feature list, by priority

**Priority 1: Must-have (the minimum demo)**

\# Feature Where

1 Fake data generator Backend (done)

2 Crop a patch of sky from an image Backend (done)

3 Brightness adjust and PNG picture Backend (done)

4 Config switch (fake or real) Backend

5 Frames endpoint (list of pictures and info) Backend

6 Page layout (index.html, app.js, style.css) Frontend

7 Show one image Frontend

8 RA/Dec input boxes and a Go button Frontend

9 Play/pause button Frontend

10 Frame slider Frontend

11 Real SPHEREx data Backend

12 All 5 targets work Both

**Priority 2: Easy and valuable**

\# Feature Where

13 5 preset target buttons Frontend

14 Coordinates in the URL Both

15 Input checking (RA 0 to 360, Dec -90 to 90) Backend

16 Zoom (FOV) control Both

17 Frame info (date, detector, color) Frontend

18 Loading spinner Frontend

19 Friendly error messages Both

20 Brightness slider (stretch) Both

21 Speed control for the animation Frontend

22 Cache (saved results for instant repeats) Backend

23 Targets endpoint (presets come from one list) Backend

**Priority 3: The “wow” features**

\# Feature Where

24 Difference mode (subtract frames so movers pop out) Both

25 Stack mode (add frames to cut noise, per detector) Both

26 Spectrum plot when you click a pixel Both

27 Flags/contamination info Both

28 Mode buttons: Normal / Difference / Stack Frontend

**Priority 4: Stretch goals**

\# Feature Where

29 Gaia/WISE star overlay Both

30 Marker circle that follows an object Frontend

31 GIF download Both

32 Embed mode (?embed=1) Frontend

33 Dark theme and phone layout Frontend

34 Beginner tutorial panel Frontend

35 Wavelength warning (color changes aren’t real motion) Frontend

36 Slow-load progress text, cancel/retry Frontend

37 “No images here” message Frontend

38 Demo video and judge script Support

**Small frontend things people forget**

Page title and favicon, keyboard shortcuts (space = play, arrows = step), a frame counter (“5 / 12”), a loop on/off toggle, a copy-link button, tooltips on buttons, a hidden-until-needed advanced panel, a “reset view” button, and accessible colors with button labels for screen readers.

##### How ours can be different

Most teams will build: type coordinates, see a video, maybe a slider. Ours can stand out in these ways. “New” means NASA didn’t list it.

**Idea - Status - Why it’s good**

1. Proper-motion-aware centering (we already do this with position_at_epoch, so the image follows fast movers like WISE 0855) - New - Without it, fast movers fall out of the picture. Most teams will miss it.
2. Expected-path overlay: draw where a known star should be on each date, so users see whether the real dot matches - New - Makes verification instant
3. Motion-arrow / trail view: draw a line connecting the dot’s positions across frames - New - Movement visible at a glance without playing
4. Blink compare mode: flick between two chosen frames, like astronomers did for Pluto - New - Classic technique, easy to add
5. “Is it real?” score: tell users when a jump is from detector or color change instead of true motion - New - Builds trust
6. Beginner “guided mission”: step-by-step find-the-mover tutorial with WISE 0855 - New - Great for public use
7. Keyboard and mobile gestures (swipe to step frames) - New - Feels professional
8. Colour-coded wavelength strip under the slider - New - Makes the 102 bands understandable
9. Mock mode as a built-in “practice game”: fake moving dots users try to find - New - Teaches the technique
10. Difference imaging, stacking by detector, spectra, overlays, URL coordinates - In the challenge - Expected; do them well

###### Status labels:

- Asked = NASA’s challenge mentions it
- Our twist = NASA mentions the topic, but we do it in a special way
- New = NASA didn’t mention it

**Part A: Data (data_mock.py, data_irsa.py, cache/)**

**Idea - Simple explanation - Status**

- Pre-save the 5 targets - Download them ahead of time so the demo opens instantly - New
- Skip bad frames automatically - If a picture is mostly flagged as bad, leave it out - New
- Practice mock files - Fake sky with several dots at different speeds, for the practice game - New
- Release name in config - Switch to newer data with a one-line change - Asked

**Part B: Processing (processing.py)**

**Idea - Simple explanation - Status**

- Difference imaging - Subtract one picture from another, so only changes are left - Asked
- Stack by detector - Add pictures together so faint things show up - Asked
- Match the brightness of frames - Make the background level the same in every frame, so flicker isn’t mistaken for movement - New
- Motion trail - Draw a line through the dot’s positions across frames - New
- Colour picture - Use 3 wavelengths as red, green and blue, to show infrared “colour” - Our twist (on the “use the 102 bands creatively” hint)
- Auto-find movers - Highlight dots that appear in different places - New (may need a new library, so we ask you first)
- Extra stretch type (asinh) - Another brightness style that is good for faint things next to bright ones - New

**Part C: API (main.py)**

**Idea - Simple explanation - Status**

- Embed and URL settings - Put the viewer inside other websites - Asked
- GIF export - Download the animation as a GIF - New
- Predicted-path endpoint - Ask the server where a star should be on each date - New
- Request limits - Stop one visitor from overloading the server - New

**Part D: Frontend (static/)**

**Idea - Simple explanation - Status**

- Blink compare - Flip quickly between two chosen frames, like the Pluto discoverers did - New
- Marker circle - Click an object and a circle follows it - New
- Wavelength colour strip - A rainbow bar under the slider showing each frame’s colour - New
- Hover readout - Move the mouse over a pixel to see its brightness and RA/Dec - New
- Magnifier - Zoom into a small area without reloading - New
- Keyboard and swipe - Space = play, arrows = step, swipe on phones - New
- Copy-link button - One click to copy the shareable URL - Our twist (URL was asked)
- Guided mission - A step-by-step “find the moving dot” lesson - New
- Practice game - Find hidden fake movers using mock data - New
- Dark theme and phone layout - Looks good on any device - New

**Part E: Config and targets (config.py, targets.py)**

**Idea - Simple explanation - Status**

- Search by name Type “Barnard’s Star” - instead of numbers (astropy can do this, no new library) - New
- Flexible coordinates - Accept 08h55m10.8s and plain degrees - New
- Follow the mover - Use position_at_epoch() so the picture follows fast stars (already built) - New
- Expected-path marker - Show where proper motion says the star should be, and compare - New

**Part F: Extras (spectra.py, flags.py, overlays.py)**

**Idea - Simple explanation - Status**

- Spectrum on click - Graph of brightness vs colour - Asked
- Contamination flags - Show which pixels are unreliable - Asked
- Gaia/WISE overlay - Mark known stars from other telescopes - Asked
- Spectrum of mover vs fixed star - Compare the two on one graph - New
- “Is it real?” hint - Warn when a change comes from a different detector or colour - New
- Export a find - Download the positions and dates of an object as a CSV - New

**Part G: Project support (README, tests, docs)**

**Idea - Simple explanation - Status**

- Tutorial and README - Teach beginners how to use it - New
- Demo video - Show it working on WISE 0855 - New
- Future-work notes - Auto-detection, “report a find” button - New

##### Things that were added later

**# Idea Part**

1 Search by name (type “Barnard’s Star”) E, D

2 Flexible coordinate input (degrees or 08h55m10.8s) E, D

3 Config limits and units (min/max FOV, one unit everywhere) E

4 asinh stretch B, D

5 Background-level matching between frames B, D

6 Motion trail (line through the dot’s positions) B, D

7 Colour picture from 3 wavelengths B, D

8 Expected-path marker (where proper motion says the star should be) E, C, D

9 Skip mostly-bad frames A

10 “Is it real?” hint F, D

11 Spectrum comparison (mover vs fixed star) F, D

12 Export a find as CSV C, D

13 Practice mock files and practice game A, C, D

14 Guided mission (interactive tutorial) D

15 Blink compare D

16 Hover readout and magnifier D

17 Wavelength colour strip D

18 Keyboard shortcuts and swipe D

19 Small polish: frame counter, loop toggle, copy-link, tooltips, accessibility D

20 Auto-find movers (optional, may need a new library) B

21 Future-work notes G
