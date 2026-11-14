# practice_check.py
# Task 24: checks a click in the practice game against the hidden answers.
#
# The answers come from data/practice/answers.json (made by data_practice.py).
# A click counts as a hit if it is within HIT_RADIUS_ARCSEC of a mover's
# position IN THAT FRAME (movers are in a different place in every frame).
# Pure Python: no astropy, no web server. Easy to test.

import json
import math

import config

# Same file data_practice.py writes
ANSWERS_FILE = config.PRACTICE_DIR / "answers.json"

# How close a click must be. One mock pixel is 6.2 arcsec, so 15 arcsec is
# about 2.4 pixels. A guess: retune when the game page exists.
HIT_RADIUS_ARCSEC = 15.0


def load_answers():
    """Read the answers file. Raises FileNotFoundError with a friendly message."""
    if not ANSWERS_FILE.exists():
        raise FileNotFoundError("Practice data not found. Run: python data_practice.py")
    return json.loads(ANSWERS_FILE.read_text(encoding="utf-8"))


def separation_arcsec(ra1, dec1, ra2, dec2):
    """Small-angle distance between two sky positions, in arcseconds.

    Handles the RA wrap at 360 and shrinks the RA difference by cos(Dec).
    """
    d_ra = (ra1 - ra2 + 180.0) % 360.0 - 180.0
    d_dec = dec1 - dec2
    mid_dec = math.radians((dec1 + dec2) / 2.0)
    return math.hypot(d_ra * math.cos(mid_dec), d_dec) * 3600.0


def check_click(ra_deg, dec_deg, frame_index, answers=None, radius_arcsec=HIT_RADIUS_ARCSEC):
    """Is this click on a hidden mover in this frame?

    Returns a dictionary:
      hit            True or False
      mover_id       "A".."D" on a hit, else None
      label          "slow", "fast", ... on a hit, else None
      frame          the frame number that was checked
      radius_arcsec  the hit radius used
      movers_total   how many movers are hidden in the set
    If two movers are both in range, the nearer one is chosen.
    Raises ValueError if the frame number does not exist.
    answers: used by tests to pass fake answers; normally None.
    """
    if answers is None:
        answers = load_answers()
    n_frames = answers["n_frames"]
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or not 0 <= frame_index < n_frames:
        raise ValueError(f"There is no frame {frame_index}. The practice set has {n_frames} frames.")

    best = None                                   # (distance, mover)
    for mover in answers["movers"]:
        spot = next((p for p in mover["positions"] if p["frame"] == frame_index), None)
        if spot is None:
            continue
        distance = separation_arcsec(ra_deg, dec_deg, spot["ra_deg"], spot["dec_deg"])
        if distance <= radius_arcsec and (best is None or distance < best[0]):
            best = (distance, mover)

    return {
        "hit": best is not None,
        "mover_id": best[1]["id"] if best else None,
        "label": best[1]["label"] if best else None,
        "frame": frame_index,
        "radius_arcsec": radius_arcsec,
        "movers_total": len(answers["movers"]),
    }