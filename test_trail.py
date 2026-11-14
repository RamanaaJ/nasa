# test_trail.py
# Tests motion trail data (Backend 20): processing.find_moving_dot().
#
# Parts 1-4 need nothing:                 python test_trail.py
# Part 5 needs the mock files:            python data_mock.py   (once)
# Part 5 is skipped if the mock files are missing.

import io
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

import processing

MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fails(func, *args, **kwargs):
    """True if the call raises a ValueError. Prints the message."""
    try:
        func(*args, **kwargs)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


SIZE = 60


def blob(x, y, amp, sigma=1.2):
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    return amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma ** 2))


def make_sky(dots, seed=0, offset=0.0, noise=1.0, cosmic=None):
    """One fake frame: noise + fixed stars + moving dots (x, y, amp) [+ a cosmic ray]."""
    rng = np.random.default_rng(seed)
    image = rng.normal(10.0 + offset, noise, (SIZE, SIZE))
    for sx, sy, amp in ((10, 12, 80), (45, 15, 60), (15, 48, 50)):     # fixed stars
        image += blob(sx, sy, amp, 1.5)
    for x, y, amp in dots:
        image += blob(x, y, amp)
    if cosmic is not None:
        image[cosmic[1], cosmic[0]] += cosmic[2]
    return {"image": image, "obs_time": datetime(2026, 1, 1) + timedelta(days=seed),
            "wcs": None, "source_file": f"fake_{seed}"}


# A dot that moves 3 pixels per frame along a sloping line (8 frames)
TRUE = [(8.0 + 3.0 * i, 25.0 + 1.0 * i) for i in range(8)]

print("--- Part 1: a clean fake sky ---")
frames = [make_sky([(x, y, 150.0)], seed=i) for i, (x, y) in enumerate(TRUE)]
trail = processing.find_moving_dot(frames)
check("one entry per frame, in order", len(trail) == 8 and [t["index"] for t in trail] == list(range(8)))
check("the dot is found in every frame", all(t["found"] for t in trail))
errors = [math.hypot(t["x"] - x, t["y"] - y) for t, (x, y) in zip(trail, TRUE)]
print(f"   biggest position error: {max(errors):.3f} pixels")
check("every position is within 0.5 pixel of the truth", max(errors) < 0.5)
check("the fixed stars are not picked (every position is near the dot, not a star)",
      all(abs(t["x"] - x) < 2 for t, (x, y) in zip(trail, TRUE)))
check("snr is large for a bright dot", all(t["snr"] > 20 for t in trail))
check("obs_time is copied from the frames", trail[3]["obs_time"] == frames[3]["obs_time"])
check("no WCS -> no sky position", trail[0]["ra_deg"] is None and trail[0]["dec_deg"] is None)
check("x grows frame by frame (the trail goes the right way)", all(a["x"] < b["x"] for a, b in zip(trail, trail[1:])))
check("original frames are not changed", np.array_equal(frames[0]["image"], make_sky([(TRUE[0][0], TRUE[0][1], 150.0)], seed=0)["image"]))

print("\n--- Part 2: things that could fool it ---")
spoiled = [make_sky([(x, y, 150.0)], seed=i, cosmic=(50, 5, 60.0) if i == 2 else None)
           for i, (x, y) in enumerate(TRUE)]
t2 = processing.find_moving_dot(spoiled)
check("a cosmic ray (60) smaller than the dot (150) does not fool it",
      all(t["found"] and abs(t["x"] - x) < 1 and abs(t["y"] - y) < 1 for t, (x, y) in zip(t2, TRUE)))

offsets = [make_sky([(x, y, 150.0)], seed=i, offset=7.0 * (i % 3)) for i, (x, y) in enumerate(TRUE)]
t3 = processing.find_moving_dot(offsets)
check("different background levels in each frame are fine",
      all(t["found"] and abs(t["x"] - x) < 1 and abs(t["y"] - y) < 1 for t, (x, y) in zip(t3, TRUE)))

holes = [make_sky([(x, y, 150.0)], seed=i) for i, (x, y) in enumerate(TRUE)]
holes[4]["image"][:, :10] = np.nan                       # a NaN strip at the left edge
holes[4]["image"][int(TRUE[4][1]), int(TRUE[4][0]) + 6] = np.nan     # and a NaN pixel near the dot
t4 = processing.find_moving_dot(holes)
check("NaN pixels do not crash it and the dot is still found",
      all(t["found"] and abs(t["x"] - x) < 1 for t, (x, y) in zip(t4, TRUE)))

allnan = [make_sky([(x, y, 150.0)], seed=i) for i, (x, y) in enumerate(TRUE)]
allnan[5]["image"] = np.full((SIZE, SIZE), np.nan)
t5 = processing.find_moving_dot(allnan)
check("an all-NaN frame is simply 'not found'", t5[5]["found"] is False and t5[5]["x"] is None)
check("the other frames still work", all(t["found"] for i, t in enumerate(t5) if i != 5))

empty_sky = [make_sky([], seed=i) for i in range(8)]
t6 = processing.find_moving_dot(empty_sky)
print("   snr values with no dot:", [round(t["snr"], 1) for t in t6])
check("pure noise: nothing is found", not any(t["found"] for t in t6))

faint = [make_sky([(x, y, 150.0)], seed=i) for i, (x, y) in enumerate(TRUE)]
check("a very high min_snr turns every frame into 'not found'",
      not any(t["found"] for t in processing.find_moving_dot(faint, min_snr=5000)))

noiseless = []
for i, (x, y) in enumerate(TRUE):
    img = np.zeros((SIZE, SIZE))
    img[int(y), int(x)] = 100.0
    noiseless.append({"image": img, "obs_time": datetime(2026, 1, 1 + i)})
t7 = processing.find_moving_dot(noiseless)
check("a perfectly noiseless sky works (noise = 0 does not divide by zero)",
      all(t["found"] and t["x"] == int(x) and t["y"] == int(y) for t, (x, y) in zip(t7, TRUE)))
check("snr stays a normal number", all(t["snr"] <= processing.TRAIL_SNR_CAP for t in t7))

print("\n--- Part 3: bad input ---")
check("fewer than 3 frames is refused", fails(processing.find_moving_dot, frames[:2]))
check("no frames is refused", fails(processing.find_moving_dot, []))
check("frames of different sizes are refused",
      fails(processing.find_moving_dot, frames[:2] + [{"image": np.zeros((30, 30))}]))
check("min_snr = 0 is refused", fails(processing.find_moving_dot, frames, 0))

print("\n--- Part 4: where the dot is in the PNG picture ---")
check("a 60 x 60 image is enlarged 6 times (400 // 60)", processing._png_factor(60, 60) == 6)
px, py = processing.pixel_to_png_position(10, 5, 50, 50)
check("pixel (10, 5) of a 50 x 50 image -> PNG (84, 356) (factor 8, north up)", (px, py) == (84.0, 356.0))
grey = np.zeros((50, 50), dtype=np.uint8)
grey[5, 10] = 255                                          # row 5 counted from the bottom
png = Image.open(io.BytesIO(processing.image_to_png_bytes(grey)))
png_array = np.array(png)
check("the PNG really is bright at that PNG position", png_array[int(py), int(px)] == 255)
check("and dark a little way off", png_array[int(py), int(px) + 12] == 0 and png_array[int(py) - 12, int(px)] == 0)
big = np.zeros((500, 500), dtype=np.uint8)
bx, by = processing.pixel_to_png_position(100, 100, 500, 500)
check("an image bigger than 400 px is not enlarged (factor 1)", (bx, by) == (100.5, 399.5))
first = trail[0]
check("trail entries carry png_x / png_y",
      (first["png_x"], first["png_y"]) == processing.pixel_to_png_position(first["x"], first["y"], SIZE, SIZE))

print("\n--- Part 5: on the mock data ---")
if not MOCK_FILE.exists():
    print("SKIPPED  no mock files. Run:  python data_mock.py")
else:
    from astropy.io import fits
    import data_mock

    header = fits.getheader(MOCK_FILE)
    RA, DEC = header["CRVAL1"], header["CRVAL2"]
    mock = data_mock.get_frames(RA, DEC, 6.0)
    check("12 mock frames", len(mock) == 12)
    mtrail = processing.find_moving_dot(mock)
    check("the dot is found in all 12 frames", all(t["found"] for t in mtrail))
    check("sky positions are given", all(t["ra_deg"] is not None for t in mtrail))

    errs = []
    for t, f in zip(mtrail, mock):
        days = (f["obs_time"] - data_mock.START_DATE).total_seconds() / 86400.0
        true_ra, true_dec = data_mock.dot_sky_position(days)
        d_ra = (t["ra_deg"] - true_ra) * math.cos(math.radians(true_dec)) * 3600
        d_dec = (t["dec_deg"] - true_dec) * 3600
        errs.append(math.hypot(d_ra, d_dec))
    print("   position errors (arcsec):", [round(e, 1) for e in errs])
    pix = data_mock.PIXEL_SCALE_ARCSEC
    check(f"every position is within 1 pixel ({pix} arcsec) of the true dot", max(errs) < pix)
    check("the dot moves between first and last frame (trail is not a single spot)",
          math.hypot(mtrail[-1]["x"] - mtrail[0]["x"], mtrail[-1]["y"] - mtrail[0]["y"]) > 5)
    check("x runs steadily one way", all(a["x"] < b["x"] for a, b in zip(mtrail, mtrail[1:]))
          or all(a["x"] > b["x"] for a, b in zip(mtrail, mtrail[1:])))
    print("   first and last (x, y):",
          (round(mtrail[0]["x"], 1), round(mtrail[0]["y"], 1)), (round(mtrail[-1]["x"], 1), round(mtrail[-1]["y"], 1)))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")