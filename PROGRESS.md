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
- Todo Backend 15: FOV handling. params.py rounds fov to 3 decimals (same as the cache key); main.py has GET /api/limits (min, max, default FOV in arcmin, from config.py); config.py comment corrected (limits are enforced). test_fov.py checks cutout sizes at 1, 3, 6, 15 and 30 arcmin, the limits and rounding (offline part + server part).
- Todo Backend 16: processing.py has an "asinh" stretch (STRETCH_MODES now linear, sqrt, log, asinh; strength ASINH_SCALE = 10). params.py and the /docs help pick it up automatically, so stretch=asinh works in the URL. test_stretch.py checks it (offline part + server part).
- Todo Backend 17: background-level matching. processing.py has estimate_background (median), match_backgrounds (shifts every frame to a common level, returns new frames), shared_limits (one black/white point pair for all frames) and stretch_image(limits=...). params.py has parse_match (match=on/off, default off); main.py passes match to /api/frames and /api/frames/{index}/image and puts match=on/off in the image links. test_background.py checks it (offline parts + server part).
- Todo Backend 18: difference imaging. processing.py has difference_frames (subtract the first or the previous frame, returns new frames), shared_difference_limit and stretch_difference (grey = no change, white = brighter, black = dimmer, one shared scale). params.py has parse_ref (ref=first|previous, default first) and "difference" is now in READY_MODES. main.py passes ref to /api/frames and /api/frames/{index}/image and puts ref in the image links. Old tests that used mode=difference as "not built yet" now use mode=stack. test_difference.py checks it (offline parts + server part).
- Todo Backend 19: stacking. processing.py has stack_frames (mean or sum, grouped by detector or all frames together; returns new frames sorted by mean time with n_stacked, mean wavelength, combined variance and OR-ed flags). params.py has parse_combine (combine=mean|sum, default mean) and parse_group (group=detector|all, default detector), and "stack" is now in READY_MODES. main.py passes combine and group to /api/frames and /api/frames/{index}/image, puts them in the image links, adds n_stacked to each frame, and in stack mode the frame list is the stacked list (6 frames on the mock data with group=detector). Old tests that used mode=stack as "not built yet" were changed (test_params.py, test_frames_api.py, test_difference.py). test_stack.py checks it (offline parts + server part).
- Todo Backend 20: motion trail data. processing.py has find_moving_dot (fixed sky = median of all frames, subtract, brightest leftover spot + centroid; returns one dictionary per frame with found, x, y, png_x, png_y, ra_deg, dec_deg, snr, obs_time) and pixel_to_png_position (data pixel -> position in the PNG, undoing the north-up flip and the whole-number enlargement). image_to_png_bytes now shares \_png_factor with it. Not connected to main.py yet. test_trail.py checks it (offline parts + mock-data part).
- Todo Backend 21: colour picture. processing.py has pick_colour_frames (longest wavelength = red, middle = green, shortest = blue), colour_picture (stretches 3 frames and stacks them into a (height, width, 3) uint8 array; channels=(r, g, b) to choose frames by hand; shared_scale=False/True) and rgb_to_png_bytes (colour PNG, north up, same enlargement as the grey PNG). Not connected to main.py yet. test_colour.py checks it (offline parts + mock-data part).
- Todo Backend 22: expected path. targets.py has decimal_year (datetime -> year number) and expected_positions (target id + list of times -> list of (ra, dec) using position_at_epoch). processing.py has locate_in_frames (sky positions -> pixel x, y, png_x, png_y and an "inside" flag for each frame, using the frame's WCS). main.py has GET /api/expected-path?target=..&ra=..&dec=..&fov=..&mode=..&combine=..&group=.. returning one entry per frame (same numbering as /api/frames). test_expected.py checks it (offline parts + mock-data part + server part).
- Todo Backend 23: practice mock files. data_practice.py (run: python data_practice.py) writes 12 fake FITS files to data/practice/ (same parts and header names as the mock files, no DOTX/DOTY) with 4 hidden movers at different speeds (A slow 0.6, B medium about 1.7, C fast about 3.0, D very fast about 4.7 pixels per frame) plus the fixed stars, on a fake sky centred on RA 150.0, Dec +2.0. The answers are in a separate file, data/practice/answers.json (per mover and per frame: x, y, ra_deg, dec_deg, obs_time, speeds). data_practice.get_frames() reads the files back as frames. config.py has PRACTICE_DIR. data/practice/ is in .gitignore. test_practice_data.py checks it. Not connected to main.py yet.

## In progress

- (nothing)

## Next step

- Todo Backend 24: Practice game answer check (waiting for go-ahead).

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
- URL settings: ra, dec (text, parsed by coords.py), fov (arcmin, limits from config.py, empty = default), stretch (processing.STRETCH_MODES), mode (normal, difference, stack), match, ref, combine, group.
- Bad URL values give HTTP 400 with {"detail": "..."}; a missing ra/dec gives 422 with a friendly {"detail": "..."} (Backend 14).
- When a new mode is built, add its name to READY_MODES in params.py. New stretches (asinh) appear automatically. All three modes (normal, difference, stack) are now built, so no test can use a mode as "not built yet" any more.
- names.py: names are compared ignoring capitals, spaces, hyphens and apostrophes. Local targets are checked first and never use the internet. Local results are J2000 unless a year is given (then position_at_epoch is used). Online results are whatever the service returns (no proper-motion correction).
- NameSearchError subclasses ValueError. Name search is not wired into the URL yet; ra/dec are still required by /api/frames. Wiring it in (e.g. a name parameter) needs a go-ahead.
- The extra spellings for the local targets (e.g. "GJ 699", "eps Ind Ba") come from the names tried in verify_targets\*.py and SIMBAD names in targets.py.
- /api/targets is the single source for preset buttons (data comes from targets.py). Without year, ra_deg/dec_deg are J2000; with year=2026 they are moved by proper motion. J2000 values are always included as ra_j2000_deg / dec_j2000_deg. The page should use year=2026 positions with the frames endpoint, because SPHEREx observes in 2025-2026.
- year is accepted from 1900 to 2100; anything else gives HTTP 400.
- Error format: every API error is {"detail": "<one friendly sentence>"}, so the page can show detail directly. Status codes: 400 bad value, 404 no images / no such frame / no such address, 405 wrong request type, 422 missing or wrongly typed setting (kept as 422 so test_frames_api.py is unchanged), 500 unexpected crash, 501 real data not connected, 503 mock files missing, 504 data source too slow.
- Unexpected crashes show a generic message to the visitor; the real error and traceback go to the uvicorn terminal.
- Real data code (data_irsa.py) must raise TimeoutError for a slow download so frames_for() can turn it into HTTP 504.
- FOV is rounded to 3 decimals in params.parse_fov (cache.FOV_DECIMALS), so the cache key and the cutout always match. The range check uses the unrounded value.
- /api/limits is the single source for the page's FOV control (min, max, default in arcmin, all from config.py).
- asinh stretch: after the percentile clip, scaled = arcsinh(ASINH_SCALE \* x) / arcsinh(ASINH_SCALE). ASINH_SCALE = 10 is a guess, to retune on real data (after-data #15, #16). The default stretch stays sqrt.
- Background matching (match=on/off, default off) is applied AFTER the cache, so cached cutouts and cache keys are unchanged. Background level = median of the finite pixels. Common level = median of all frames' levels. Only an additive offset is removed.
- When match is on, the image endpoint also uses ONE shared brightness scale (shared_limits over all frames). Without it matching would show nothing, because stretch_image already subtracts each frame's own low percentile.
- match accepts on/off, 1/0, true/false, yes/no (any capitals); anything else gives HTTP 400. The image links always carry match=on or match=off.
- Difference mode: mode=difference plus ref=first|previous (default first). Frame 0 is always blank (nothing to subtract). If match=on, backgrounds are matched first, then frames are subtracted.
- Difference pictures use a symmetric scale: 0 is mid grey, +limit white, -limit black. The limit is the 99.5th percentile of |difference| over all frames (all-zero frames skipped). The chosen stretch curve is applied to |difference| and the sign is kept. NaN pixels are black.
- Difference is computed after the cache, so cache keys are unchanged. Variances add and flags are OR-ed (not used by the picture yet).
- Stack mode: mode=stack plus combine=mean|sum (default mean) and group=detector|all (default detector). Stacking is done after the cache, so cache keys are unchanged. If match=on, backgrounds are matched first, then frames are stacked, then one shared brightness scale is used for the stacked frames.
- In stack mode the frame list is the STACKED list, so frame numbers refer to stacked frames (6 on the mock data with group=detector, 1 with group=all). Normal and difference modes still list every raw frame.
- A stacked frame keeps the first frame's WCS and other keys, and gets: obs_time = mean time, wavelength_um = mean wavelength, detector = the detector number (0 when group=all, meaning "several detectors"), n_stacked = number of frames added, variance combined (mean: sum of variances / n^2; sum: sum of variances), flags OR-ed, source_file = "stack of N: ...". /api/frames shows n_stacked for every frame (1 for unstacked frames).
- NaN pixels are skipped when stacking; a pixel that is NaN in every frame stays NaN.
- Stacked frames are sorted by their mean observation time.
- Trail positions: x, y are pixel numbers counted from 0, with y counted from the bottom row (FITS way). png_x, png_y are in the PNG (top-left origin, north up, after enlargement), ready for the page to draw on.
- find_moving_dot needs at least 3 frames of the same size (HTTP 400 once wired in). A spot must stand out by TRAIL_MIN_SNR = 5 times the noise (guess, retune on real data); noise = robust sigma (MAD) of the frame minus the fixed sky. Each frame's own median is removed first, so different background levels do not matter.
- Centroid uses the pixels within TRAIL_CENTROID_HALF = 3 of the brightest one that are above 2 sigma. snr is capped at 9999 so it is JSON-friendly.
- Colour picture: automatic choice by wavelength, longest = red, middle = green, shortest = blue; fewer than 3 frames, or all frames with the same wavelength, gives a ValueError (HTTP 400 once wired in). channels=(r, g, b) overrides the choice. Each channel is stretched on its own by default (shared_scale=False); shared_scale=True uses one black/white point for all three so colours show real brightness ratios.
- A colour picture mixes frames from different dates. Fixed sources look white or grey, moving sources show as separate red, green and blue dots. That is intended; it is not a real colour of the object.
- rgb_to_png_bytes uses the same flip and enlargement as image_to_png_bytes, so pixel_to_png_position() also works for colour pictures.
- Expected path: target is matched with names.resolve_local (same tolerant spelling as name search, offline; only the 5 built-in targets). The path uses each frame's obs_time (a stacked frame uses its mean time) and position_at_epoch (straight-line proper motion from J2000, no parallax). The endpoint takes the same ra/dec/fov/mode/combine/group as /api/frames so entry N belongs to frame N. A position outside the frame still gets x, y but inside=False.
- Practice set: its own folder (data/practice/) and its own sky position, so it never mixes with the normal mock data or its cache. The FITS files do not contain the answers; answers.json is never served (only static/ is served). The files use the same extension and header names as the mock files, so data_mock.load_mock_frame() reads them.
- Practice mover speeds, brightness (90-150), start positions and the sky centre (150.0, +2.0) are my own choices, to retune when the game is built. Tracks avoid the fixed stars. Cosmic rays and dead pixels come from the mock helpers (cosmic rays avoid rows 40-59 only), so a dead pixel can hide a mover in one frame; that is fine for a game.
- All practice frames share one WCS (like the mock frames), so pixel tracks in answers.json refer to the full 100x100 image. Use ra_deg/dec_deg for anything that must survive cutting.

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
- The name search (names.py, Backend 12) is still not connected to the URL.
- With mock data only the WISE 0855 preset (at its year-2026 position) finds frames; the other 4 presets give 404 ("No images cover this sky position") because the mock sky covers only that patch. This is expected until real data (Backend 25).
- Positions at a given year use straight-line proper motion only (no parallax); fine for centring a cutout.
- The 504 (slow data) branch is untested against real data; nothing raises TimeoutError yet. Revisit in after-data #10 (Robust downloading).
- The 500 handler was not triggered in the live test (optional step 5 in the Backend 14 instructions); it is only checked by reading the code.
- Environment: Python 3.15 could not install PyYAML on Windows (no C++ compiler). The project uses Python 3.13; the venv was rebuilt with `py -3.13 -m venv venv`.
- A FOV bigger than the image gives a cutout with NaN (black) edges; this is expected. On the mock data (about 10.3 arcmin wide) anything above about 10 arcmin has black edges.
- MAX_FRAMES (config.py) is still not enforced anywhere. Planned for after-data #8 (Sort, group, limit).
- Background matching removes only an offset, not scale differences between frames or bands. Real SPHEREx bands will probably differ in scale. Retune in after-data #16.
- The mock frames already have almost the same background (noise around 10), so matching changes little on mock data; test_background.py uses frames with big offsets to prove it works.
- estimate_background ignores flags (real flag bits are not known yet) and the median still includes stars in very crowded fields.
- With match=on, each image request recomputes the levels from all frames (cheap on the mock data; recheck speed on real data, after-data #27).
- Difference imaging subtracts pixel by pixel and assumes every frame has the same pixel grid. The mock frames share one WCS, so this works. Real SPHEREx pointings will differ, so real frames probably need re-aligning (reprojecting) onto one grid first; frames of different sizes give HTTP 400. Revisit in after-data #11 (Edge cases).
- In difference mode, frame 0 is a flat grey picture by design.
- Real bands/detectors differ in brightness scale, so subtracting frames from different bands may show large residuals on bright stars. Retune in after-data #15.
- Stacking has the same pixel-grid assumption as difference imaging: frames of different sizes give HTTP 400, and same-sized frames with different WCS would be added wrongly. Real frames probably need re-aligning first (after-data #11).
- Stacking does not use flags to skip bad pixels (real flag bits are not known yet), and there is no outlier rejection: in a mean of 2 frames a cosmic ray is only halved, not removed. Revisit with real flags (after-data #7, #17) and maybe a median option.
- A moving object is smeared into several dots in a stack, because frames from different dates are added. That is expected; stacking is meant for faint fixed sources. Use difference mode to find movers.
- Stacking frames from different bands (and group=all especially) mixes wavelengths; the stacked wavelength_um is only the mean. For real data, stack within one band or detector.
- Sum and mean give the SAME picture, because the brightness stretch rescales every picture (a sum is just the mean times N). They differ only in the numbers (flux, variance), which matter later for spectra and the hover readout.
- A sum of a pixel that is NaN in some frames adds fewer frames, so it is a little smaller than its neighbours (only matters at image edges).
- In stack mode the frame numbers differ from normal mode, so a page must reload the frame list when the mode changes.
- The trail is not connected to main.py (no endpoint yet). It needs a go-ahead; Todo Backend 22 plans a small endpoint for the expected path.
- The median method removes very slow movers. A dot that stays near the same pixels in half the frames or more is partly absorbed into the "fixed sky". Real WISE 0855 moves about 8 arcsec/year, which is about one SPHEREx pixel per 9 months, so it may NOT be found this way on real data. Expected-path tracking (Backend 22) or a user-placed starting point may be needed. Revisit in after-data #12 and #22.
- Same pixel-grid assumption as difference and stack: real pointings need re-aligning first (after-data #11).
- Flags are not used (real bits unknown). A cosmic ray is only rejected because it is fainter than the dot. Bright fixed-star variability or a brighter artefact can be picked instead of the mover.
- On pure noise the strongest spot reaches about 4 to 5 sigma, close to the 5-sigma limit, so real noisy data may need a higher limit or flags.
- Mock-data check (Part 5 of test_trail.py) has not been run by me; run it and note the result.
- The colour picture is not connected to main.py (no endpoint, no URL setting yet). It needs a go-ahead.
- The 3 frames must have the same pixel size and the same pixel grid (same assumption as difference, stack and trail). Real pointings need re-aligning first (after-data #11).
- The mock frames have the same brightness at every wavelength, so mock fixed stars look grey or white. Real stars will have real colours, and different bands and detectors differ in brightness scale. Real band choice and scaling must be retuned (after-data #23).
- Flags are not used (real bits unknown).
- Mock-data check (Part 4 of test_colour.py) has not been run by me; run it and note the result.
- The mock dot moves at 10x WISE 0855's real proper motion (SPEED_BOOST), so on mock data the expected path only agrees with the dot in frame 0; later frames drift apart by design. On real data they should line up (check in after-data #22).
- Expected path ignores parallax. For nearby stars (Barnard's Star, Eps Ind) and SPHEREx's Earth-orbit viewpoint this may cause offsets of a pixel or so; check on real data.
- With mock data only the WISE 0855 target has frames (same as the other presets), so the other 4 targets give 404.
- The practice set is not wired into main.py (no practice frames endpoint, no cache key for it). The frames endpoint still only serves the normal mock data. Wiring it (e.g. a source parameter) needs a go-ahead; cache.current_release() returns "mock" for both, so a practice request must not share the mock cache key.
- After re-running data_practice.py nothing in the cache refers to practice data (it is not cached), so no cache clearing is needed.

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
- python test_fov.py (cutout sizes and limits; server part if uvicorn is running)
- python test_stretch.py (stretch modes; server part if uvicorn is running)
- python test_background.py (background matching; server part if uvicorn is running)
- python test_difference.py (difference imaging; server part if uvicorn is running)
- python test_stack.py (stacking; server part if uvicorn is running)
- python test_trail.py (motion trail; mock-data part needs data/mock/ files)
- python test_colour.py (colour picture; mock-data part needs data/mock/ files and saves cache/test_png/colour_mock.png)
- python test_expected.py (expected path; mock-data part needs data/mock/ files; server part if uvicorn is running)
- python data_practice.py (creates data/practice/practice_00..11.fits and answers.json)
- python test_practice_data.py (checks the practice files and answers; skipped if they do not exist)
