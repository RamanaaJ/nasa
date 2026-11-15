# Frontend Progress Log

## Current task

Frontend Tasks 1-5 written (not yet tested by me in the browser).

## Done

- Task 1: Page skeleton. index.html, style.css, app.js. Dark theme, picture on the left, controls on the right, stacks on narrow screens.
- Task 2: Show one image. Fetches /api/frames and shows frames[0].image_url in an <img>.
- Task 3: RA/Dec form. Two text boxes and a Go button. Text is sent as typed (the server parses degrees and sexagesimal).
- Task 4: Name search box. Matches the typed name against /api/targets?year=2026 (id, label, simbad_name; ignores capitals, spaces, hyphens, apostrophes) and fills the RA/Dec boxes. Presets only.
- Task 5: Animation player. Play/Pause, frame slider, Slow/Normal/Fast speed. Loops at the end. Dragging the slider pauses.

## In progress

- (nothing)

## Next step

Frontend Task 6: Frame counter and loop toggle (waiting for go-ahead).
Before that, test Tasks 1-5 (see below).

## Decisions made

- Plain HTML + CSS + JS in frontend/. No framework, no libraries, no CDN, no web fonts.
- The page only displays PNGs made by the server (see PROGRESS.md "Decisions").
- All settings will live in the URL (?ra=&dec=&fov=...). Not done yet (Task 9).
- FOV is not sent, so the server default is used. The FOV control is Task 11 and will read /api/limits.
- On page load the page fills in WISE 0855 (id "wise0855", year-2026 position from /api/targets) and loads it, so there is something to test. Task 8 will replace this with preset buttons.
- The animation always loops. Task 6 adds the on/off switch.
- Loading shows plain text in the status line. A real spinner is Task 14.
- Errors show the API's "detail" sentence as it is.
- The "+" problem from API_GUIDE.md is handled with URLSearchParams.

## Requests for backend

- Name search endpoint: names.py exists but has no URL. Until it does, the name box only finds the 5 presets (API_GUIDE.md says the same).
- (Optional) One-box coordinates: the TODO Task 4 wording asks for ONE box taking degrees, sexagesimal or a name. The API takes ra and dec separately, so the page keeps two boxes plus a name box. A combined endpoint, for example `name=` or `coords=`, would let one box do everything.

## Known problems

- With mock data only WISE 0855 returns frames. The other 4 presets give 404; the page shows the server's message (expected).
- I could not read main.py, params.py, errors.py, config.py or targets.py in this session (only API_GUIDE.md was available). Everything is based on API_GUIDE.md. Not checked: how main.py serves style.css and app.js. The page links them as "style.css" and "app.js" (relative paths).
- The image is shown as large as the picture area allows. Not yet tested on a real phone.

## How to run and test

- Backend: venv active, python data_mock.py (once), python cache.py clear,
  uvicorn main:app --reload
- Open http://127.0.0.1:8000/ (serves frontend/index.html)
- API docs: http://127.0.0.1:8000/docs
