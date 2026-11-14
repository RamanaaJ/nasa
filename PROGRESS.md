# Progress Log

## Current milestone

M1: Mock data generator (preparing: verifying targets first)

## Done

- Environment set up (Python 3.13, venv, libraries installed)
- Project brief, challenge text, priority list, structure created
- Todo Backend 1: workflow files created (PROGRESS.md, FRAME_FORMAT.md, docs/DATA_NOTES.md, rules file, .gitignore) and committed to Git.
- Todo Backend 2: targets verified against SIMBAD (Harvard mirror) and targets.py written (J2000 positions + proper motion + position_at_epoch)

## In progress

- (nothing)

## Next step

- Todo Backend 3: Mock data generator (waiting for go-ahead)

## Decisions made

- Server renders PNGs; browser only displays them
- Mock and real data return the same "frame" format
- All settings live in the URL (?ra=&dec=&fov=)
- targets.py stores J2000 positions and proper motion; cutouts must use
  position_at_epoch() for the observation year, because fast movers have
  moved several arcminutes since 2000

## Known problems

- SIMBAD Strasbourg is down (CDS cybersecurity incident, Nov 2026);
  using the Harvard mirror via pyvo (verify_targets_mirror.py)
- targets.txt coordinates for Epsilon Indi B look like the bright star
  Eps Ind A, not the brown dwarf pair (about 6.7 arcmin apart)
- WISE 0855 coordinates in the brief (08h55m10.831s) are from about 2010,
  not J2000

## How to run and test

- (fill in after each milestone)
