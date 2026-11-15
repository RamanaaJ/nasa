# Frontend Progress Log

## Current task

Frontend Tasks 1-14 written (not yet tested by me in the browser). Task 15 is blocked (see Requests for backend).

## Done

- Task 1-5: skeleton, one image, RA/Dec form, name search (presets only), animation player.
- Task 6: Frame counter ("5 / 12") and Loop checkbox. With loop off, play stops on the last frame.
- Task 7: Space = play/pause, Left/Right arrows = step, swipe left/right on the picture. Keys are ignored inside text boxes, dropdowns, the slider and when a button is focused.
- Task 8: Preset buttons, built from /api/targets?year=2026.
- Task 9: ra, dec, fov are read from the page address on load and written back (history.replaceState) on every load.
- Task 10: Copy link button (navigator.clipboard).
- Task 11: FOV dropdown filled from /api/limits (min, a few sizes in range, default, max). Changing it reloads the frames.
- Task 12: Frame info panel: date, detector (0 shown as "several (stacked)"), wavelength, frames stacked, source. Flags row says "Not available yet" (API has no flags).
- Task 13: Wavelength colour strip: one block per frame, colour from the frame list's own min/max wavelength, click to jump, current frame highlighted.
- Task 14: Spinner on the picture while loading; errors show the API's "detail" sentence.

## In progress

- (nothing)

## Next step

Frontend Task 15 is blocked until the backend request below is answered. Test Tasks 6-14 first.

## Decisions made

- Plain HTML + CSS + JS. No framework, library or CDN.
- Page address uses the same names as the API: ?ra=&dec=&fov= (stretch, mode will be added in later tasks).
- FOV dropdown sizes (3, 10, 15) are my own choices inside the limits from /api/limits.
- Colour strip range is the loaded frames' own min/max wavelength, not a fixed range.

## Requests for backend

- Name search endpoint (names.py has no URL). Until then the name box only finds the 5 presets.
- (Optional) One-box coordinates: a `name=` or `coords=` parameter.
- Task 15 (brightness slider): API_GUIDE.md only offers stretch=linear|sqrt|log|asinh. There is no parameter for brightness level (e.g. black/white percentile). Please add one (for example `clip_low` / `clip_high` or `brightness`) to /api/frames and the image links, with its min/max/default in /api/limits. Task 16 (stretch type dropdown) needs no backend change.

## Known problems

- I could not read main.py, params.py, errors.py, config.py or targets.py. Everything is based on API_GUIDE.md. Not checked: that /api/frames accepts fov together with ra/dec exactly as described (API_GUIDE says it does).
- With mock data only WISE 0855 returns frames; the other 4 presets give 404 and the page shows the server's message (expected).
- The copy-link button may be blocked outside https/localhost.
- Swipe and keyboard not tested on a real phone / with a screen reader.
- Wavelength strip with 258 real frames will have very thin blocks (see Task 4 "after data").

## How to run and test

- Backend: venv active, python data_mock.py (once), python cache.py clear, uvicorn main:app --reload
- Open http://127.0.0.1:8000/
