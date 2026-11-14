# Progress Log

## Current milestone

M1: Mock data generator (preparing: verifying targets first)

## Done

- Environment set up (Python 3.13, venv, libraries installed)
- Project brief, challenge text, priority list, structure created
- Todo Backend 1: workflow files created (PROGRESS.md, FRAME_FORMAT.md, docs/DATA_NOTES.md, rules file, .gitignore) and committed to Git.
- Todo Backend 2: targets verified against SIMBAD (Harvard mirror) and targets.py written (J2000 positions + proper motion + position_at_epoch)
- Todo Backend 3: data_mock.py writes 12 mock FITS files to data/mock/ (moving dot, WCS, DATE-OBS, DETECTOR, WAVE_UM in headers); check_mock.py reads them back
- Todo Backend 4: data_mock.py now also writes FLAGS (bits 1=bad, 2=cosmic ray, 4=contaminated) and VARIANCE extensions; check_mock.py checks them
- Todo Backend 5: processing.py with cutout_frame (WCS-based, returns a new frame), stretch_image (linear/sqrt/log + percentile clip) and image_to_png_bytes / frame_to_png; test_processing.py checks it and saves PNGs to cache/test_png/
- Todo Backend 6: config.py with USE_MOCK, RELEASE_NAME, DEFAULT_FOV_ARCMIN, MAX_FRAMES, plus MOCK_DIR / CACHE_DIR paths. python config.py prints the settings.
- Todo Backend 7: config.py now has MIN_FOV_ARCMIN (1.0) and MAX_FOV_ARCMIN (30.0) next to DEFAULT_FOV_ARCMIN (6.0); all FOV values in arcminutes. Limits are not enforced yet.
- Todo Backend 8: cache.py saves lists of frames in cache/cutouts/, keyed by release, RA, Dec and FOV; get_or_load(ra, dec, fov, loader) returns cached frames or calls the loader; test_cache.py checks it.
- Todo Backend 9: main.py (FastAPI) with GET /api/frames (list with image links, dates, detectors, wavelengths, pixel scale, centre), GET /api/frames/{index}/image (PNG) and static/ serving; data_mock.py now has get_frames() (cutouts from the mock files); cache.py uses a lock for simultaneous requests; test_frames_api.py checks the endpoint.
- Todo Backend 9 checked live: all test_frames_api.py checks passed (cleanup bug on Windows fixed).
- Todo Backend 10: coords.py (parse_coordinates, parse_ra, parse_dec, CoordinateError) accepts degrees, 08h55m10.8s, 08:55:10.8 and 08 55 10.8 forms and gives friendly errors; test_coords.py checks it.
- Todo Backend 11: params.py (validate_request) checks ra, dec, fov, mode, stretch from the URL; main.py uses it; bad values return HTTP 400 with a friendly message; ra/dec accept degrees or sexagesimal via coords.py; test_params.py and test_frames_api.py (Test 6) check it.
- Todo Backend 12: names.py (resolve_name, resolve_local, NameSearchError, NameResult) turns a name into RA/Dec. Checks the 5 local targets first (offline, spelling-tolerant), then astropy's SkyCoord.from_name; friendly message if the online lookup fails. test_names.py checks it with a fake online service. Not connected to main.py/URL yet.
- Todo Backend 13: targets.py has target_list(year=None); main.py has GET /api/targets?year=.. returning the 5 preset targets (id, label, simbad_name, ra/dec at the chosen epoch, J2000 ra/dec, proper motion, note). Optional year moves positions with position_at_epoch(). Bad year gives HTTP 400. test_targets.py checks it (offline part + server part).
- Todo Backend 14: errors.py holds the message wording; main.py has handlers so every error is JSON {"detail": "friendly sentence"}: missing settings (422), stock 404/405 wording, unexpected crashes (500, details only in the terminal). frames_for() now has a TimeoutError -> 504 branch and a no-images 404 that names the position. test_errors.py checks it (offline part + server part). All checks passed live.

## In progress

- (nothing)

## Next step

- Todo Backend 15: FOV handling (waiting for go-ahead)

## Decisions made

- Server renders PNGs; browser only displays them
- Mock and real data return the same "frame" format
- All settings live in the URL (?ra=&dec=&fov=)
- targets.py stores J2000 positions and proper motion; cutouts must use position_at_epoch() for the observation year, because fast movers have moved several arcminutes since 2000
- Mock dot moves at 10x WISE 0855's real proper motion so it is visible
- Mock header keywords (DETECTOR, WAVE_UM, DOTX, DOTY) are our own names;
  real SPHEREx keywords must be checked later
- Mock files have 3 parts: PRIMARY (image), FLAGS, VARIANCE
- Mock flag bit meanings (1/2/4) are invented; real ones come from the SPHEREx documentation later; flags.py must keep the table swappable
- Mock bad pixels are the same in every frame; cosmic rays are random
- Defects avoid the dot's rows (y 40-59) so tests stay clear
- processing.py takes frames in and gives bytes out; it never reads files or downloads anything
- PNGs are flipped so north is up; small images are enlarged with nearest neighbour (whole-number factor, about 400 px)
- Cutouts outside the image edge are filled with NaN (image, variance) or 0 (flags); NaN pixels are drawn black
- Default stretch is sqrt, with 1% / 99.5% percentile clipping (a guess to retune on real data)
- Extra ideas are tracked in TODO_LIST.md (marked "new") and Priority 5 in Priority_list.txt
- TODO_LIST.md replaces Todo_List.pdf
- All FOV values use arcminutes (config.py needs DEFAULT_FOV_ARCMIN)
- Name search checks local targets first, then the online lookup
- FOV limits 1 to 30 arcmin are guesses; 30 is large enough for Eps Ind A and B (about 6.7 arcmin apart). Retune on real data.
- Cache key = release + RA + Dec + FOV (rounded: 5 decimals for RA/Dec, 3 for FOV). Mock data uses the key "mock", real data uses config.RELEASE_NAME.
- Cache files are pickle files (fine for our own local cache; never load cache files from other people). Empty "no images" results are not cached.
- After re-running data_mock.py, run python cache.py clear.
- get_frames() returns cutouts (fov_arcmin wide), already cut around the requested position; the cache stores these cutouts.
- Frame list gives pixel scale and centre per frame (real pointings will differ). Hover maths assumes north up and east left; recheck on real data.
- Basic range checks use FastAPI (422); friendly errors come in Backend 11 and 14.
- Run the server with: uvicorn main:app --reload
- coords.py: plain numbers are degrees; sexagesimal RA without a unit letter is hours; Dec is always degrees. Pure Python, no astropy.
- CoordinateError subclasses ValueError. Name search (Backend 12) is a separate step.
- URL settings: ra, dec (text, parsed by coords.py), fov (arcmin, limits from config.py, empty = default), stretch (processing.STRETCH_MODES), mode (normal, difference, stack; only normal is built).
- Bad URL values give HTTP 400 with {"detail": "..."}; a missing ra/dec gives 422 with a friendly {"detail": "..."} (Backend 14).
- When a new mode is built (Backend 18/19), add its name to READY_MODES in params.py. New stretches (asinh) appear automatically.
- names.py: names are compared ignoring capitals, spaces, hyphens and apostrophes. Local targets are checked first and never use the internet. Local results are J2000 unless a year is given (then position_at_epoch is used). Online results are whatever the service returns (no proper-motion correction).
- NameSearchError subclasses ValueError. Name search is not wired into the URL yet; ra/dec are still required by /api/frames. Wiring it in (e.g. a name parameter) needs a go-ahead.
- The extra spellings for the local targets (e.g. "GJ 699", "eps Ind Ba") come from the names tried in verify_targets\*.py and SIMBAD names in targets.py.
- /api/targets is the single source for preset buttons (data comes from targets.py). Without year, ra_deg/dec_deg are J2000; with year=2026 they are moved by proper motion. J2000 values are always included as ra_j2000_deg / dec_j2000_deg. The page should use year=2026 positions with the frames endpoint, because SPHEREx observes in 2025-2026.
- year is accepted from 1900 to 2100; anything else gives HTTP 400.
- Error format: every API error is {"detail": "<one friendly sentence>"}, so the page can show detail directly. Status codes: 400 bad value, 404 no images / no such frame / no such address, 405 wrong request type, 422 missing or wrongly typed setting (kept as 422 so test_frames_api.py is unchanged), 500 unexpected crash, 501 real data not connected, 503 mock files missing, 504 data source too slow.
- Unexpected crashes show a generic message to the visitor; the real error and traceback go to the uvicorn terminal.
- Real data code (data_irsa.py) must raise TimeoutError for a slow download so frames_for() can turn it into HTTP 504.

## Known problems

- SIMBAD Strasbourg is down (CDS cybersecurity incident, Nov 2026); using the Harvard mirror via pyvo (verify_targets_mirror.py)
- targets.txt coordinates for Epsilon Indi B look like the bright star Eps Ind A, not the brown dwarf pair (about 6.7 arcmin apart)
- WISE 0855 coordinates in the brief (08h55m10.831s) are from about 2010, not J2000
- Mock assumptions not yet verified: pixel scale 6.2 arcsec, wavelength range 0.75-5.0 um
- All 12 mock frames share one WCS; real SPHEREx pointings will differ
- Mock extension names (FLAGS, VARIANCE) and the variance recipe are guesses; real file layout must be inspected (Backend after-data #1)
- Mock FLAGS/VARIANCE extensions have no WCS of their own
- No function yet turns the mock FITS files into frames; test_processing.py builds them by hand. A mock get_frames() is needed before the Frames endpoint (Backend 9)
- Online name lookup depends on CDS, which is currently down
- config.py is the single place for settings; other files use import config
- config.py uses DEFAULT_FOV_ARCMIN (arcminutes) from the start; the old degrees version is not carried over
- MAX_FRAMES = 50 and RELEASE_NAME = "spherex_qr2" are placeholders, not verified values
- cache.py is not used by anything yet; the Frames endpoint (Backend 9) will call get_or_load. config.py's CACHE_DIR is used by cache.py.
- Real data returns 501 until data_irsa.py exists (Backend 25).
- FOV limits are enforced by params.py (from config.py).
- A "+" in a URL means a space, so +04d41m36s loses its sign (still positive).
- Online name lookup (SkyCoord.from_name) is untested against the real service; CDS was down at the last check. names.py cannot tell "unknown name" from "service down", so its message covers both.
- With mock data only the WISE 0855 preset (at its year-2026 position) finds frames; the other 4 presets give 404 ("No images cover this sky position") because the mock sky covers only that patch. This is expected until real data (Backend 25).
- Positions at a given year use straight-line proper motion only (no parallax); fine for centring a cutout.
- The name search (names.py, Backend 12) is still not connected to the URL.
- The 504 (slow data) branch is untested against real data; nothing raises TimeoutError yet. Revisit in after-data #10 (Robust downloading).
- The 500 handler was not triggered in the live test (optional step 5 in the Backend 14 instructions); it is only checked by reading the code.
- Environment: Python 3.15 could not install PyYAML on Windows (no C++ compiler). The project uses Python 3.13; the venv was rebuilt with `py -3.13 -m venv venv`.

## How to run and test

- python data_mock.py (creates data/mock/mock_00..11.fits with image, FLAGS, VARIANCE)
- python check_mock.py (prints a summary, including flag counts)
- python test_processing.py (needs data/mock/ files; saves PNGs in cache/test_png/)
- python config.py (prints all settings)
- python test_cache.py (checks the cache) and - python cache.py (shows cache size) / python cache.py clear (empties it)
- uvicorn main:app --reload (start the server; docs at http://127.0.0.1:8000/docs)
- python test_frames_api.py (with the server running)
- python test_coords.py (checks coordinate parsing) and python coords.py "08h55m10.8s -07d14m42s" (try one by hand)
- python test_params.py (checks URL settings)
- python test_names.py (checks name search, offline) and python names.py "Barnard's Star" (try one by hand)
- python test_targets.py (offline part always; server part if uvicorn is running)
  python test_errors.py (offline part always; server part if uvicorn is running)
- First-time setup in a fresh clone: py -3.13 -m venv venv, .\venv\Scripts\Activate.ps1, pip install -r requirements.txt, python data_mock.py, python cache.py clear
