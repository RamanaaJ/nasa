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

## In progress

- (nothing)

## Next step

- Todo Backend 11: URL parameters and validation (waiting for go-ahead)

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

## Known problems

- SIMBAD Strasbourg is down (CDS cybersecurity incident, Nov 2026); using the Harvard mirror via pyvo (verify_targets_mirror.py)
- targets.txt coordinates for Epsilon Indi B look like the bright star Eps Ind A, not the brown dwarf pair (about 6.7 arcmin apart)
- WISE 0855 coordinates in the brief (08h55m10.831s) are from about 2010, not J2000
- Mock assumptions not yet verified: pixel scale 6.2 arcsec, wavelength range 0.75-5.0 um
- All 12 mock frames share one WCS; real SPHEREx pointings will differ
- Mock extension names (FLAGS, VARIANCE) and the variance recipe are guesses; real file layout must be inspected (Backend after-data #1)
- Mock FLAGS/VARIANCE extensions have no WCS of their own
- No function yet turns the mock FITS files into frames; test_processing.py builds them by hand. A mock get_frames() is needed before the Frames endpoint (Backend 9)
- FOV minimum/maximum limits not enforced yet (Backend 12)
- Online name lookup depends on CDS, which is currently down
- config.py is the single place for settings; other files use import config
- config.py uses DEFAULT_FOV_ARCMIN (arcminutes) from the start; the old degrees version is not carried over
- MAX_FRAMES = 50 and RELEASE_NAME = "spherex_qr2" are placeholders, not verified values
- FOV limits exist in config.py but are not enforced yet (Backend 11 and 15)
- cache.py is not used by anything yet; the Frames endpoint (Backend 9) will call get_or_load. config.py's CACHE_DIR is used by cache.py.
- Real data returns 501 until data_irsa.py exists (Backend 25).
- coords.py is not used by main.py yet (Backend 11 will connect it). Decimal commas (133,8) are not supported; a comma means "separator".

## How to run and test

- python data_mock.py (creates data/mock/mock_00..11.fits with image, FLAGS, VARIANCE)
- python check_mock.py (prints a summary, including flag counts)
- python test_processing.py (needs data/mock/ files; saves PNGs in cache/test_png/)
- python config.py (prints all settings)
- python test_cache.py (checks the cache) and - python cache.py (shows cache size) / python cache.py clear (empties it)
- uvicorn main:app --reload (start the server; docs at http://127.0.0.1:8000/docs)
- python test_frames_api.py (with the server running)
- python test_coords.py (checks coordinate parsing) and python coords.py "08h55m10.8s -07d14m42s" (try one by hand)
