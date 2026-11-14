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

## In progress

- (nothing)

## Next step

- Todo Backend 6: Config switch (waiting for go-ahead)

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

## Known problems

- SIMBAD Strasbourg is down (CDS cybersecurity incident, Nov 2026); using the Harvard mirror via pyvo (verify_targets_mirror.py)
- targets.txt coordinates for Epsilon Indi B look like the bright star Eps Ind A, not the brown dwarf pair (about 6.7 arcmin apart)
- WISE 0855 coordinates in the brief (08h55m10.831s) are from about 2010, not J2000
- Mock assumptions not yet verified: pixel scale 6.2 arcsec, wavelength range 0.75-5.0 um
- All 12 mock frames share one WCS; real SPHEREx pointings will differ
- Mock extension names (FLAGS, VARIANCE) and the variance recipe are guesses; real file layout must be inspected (Backend after-data #1)
- Mock FLAGS/VARIANCE extensions have no WCS of their own
- No function yet turns the mock FITS files into frames; test_processing.py builds them by hand. A mock get_frames() is needed before the Frames endpoint (Backend 8)
- FOV minimum/maximum limits not enforced yet (Backend 12)

## How to run and test

- python data_mock.py (creates data/mock/mock_00..11.fits with image, FLAGS, VARIANCE)
- python check_mock.py (prints a summary, including flag counts)
- python test_processing.py (needs data/mock/ files; saves PNGs in cache/test_png/)
