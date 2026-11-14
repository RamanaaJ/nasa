# test_practice_data.py
# Tests data_practice.py (Backend 23).
# First run:   python data_practice.py
# Then:        python test_practice_data.py
# Skipped if the practice files are missing.

import json

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import config
import data_mock
import data_practice

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


files = sorted(config.PRACTICE_DIR.glob("practice_*.fits"))
if not files or not data_practice.ANSWERS_FILE.exists():
    print("SKIPPED  no practice files. Run:  python data_practice.py")
    raise SystemExit

print("--- Part 1: the files ---")
check("12 FITS files", len(files) == 12)
with fits.open(files[0]) as hdul:
    hdr = hdul[0].header
    check("three parts: PRIMARY, FLAGS, VARIANCE", [h.name for h in hdul] == ["PRIMARY", "FLAGS", "VARIANCE"])
    check("the header does NOT reveal the dot positions (no DOTX / DOTY)", "DOTX" not in hdr and "DOTY" not in hdr)
    check("header says PRACTICE", hdr["PRACTICE"] is True)
dates = [fits.getheader(f)["DATE-OBS"] for f in files]
check("dates grow from file to file", dates == sorted(dates) and len(set(dates)) == 12)

print("\n--- Part 2: the answers file ---")
answers = json.loads(data_practice.ANSWERS_FILE.read_text(encoding="utf-8"))
movers = answers["movers"]
check("4 movers with ids A, B, C, D", [m["id"] for m in movers] == ["A", "B", "C", "D"])
check("every mover has a position for each of the 12 frames",
      all([p["frame"] for p in m["positions"]] == list(range(12)) for m in movers))
speeds = [m["speed_pix_per_frame"] for m in movers]
print("   speeds (pixels per frame):", speeds)
check("the 4 speeds are all different (slow to very fast)", speeds == sorted(speeds) and len(set(speeds)) == 4)
check("every position stays inside the 100 x 100 image",
      all(0 <= p["x"] <= 99 and 0 <= p["y"] <= 99 for m in movers for p in m["positions"]))

print("\n--- Part 3: the movers are really in the pictures ---")
all_bright = True
all_wcs = True
for i, f in enumerate(files):
    with fits.open(f) as hdul:
        image = np.array(hdul[0].data, dtype=float)
        wcs = WCS(hdul[0].header)
    for m in movers:
        p = m["positions"][i]
        x, y = int(round(p["x"])), int(round(p["y"]))
        window = image[max(0, y - 1):y + 2, max(0, x - 1):x + 2]   # 3x3 around the answer
        if window.max() < 40:                                      # background is about 10
            all_bright = False
            print(f"   mover {m['id']} not bright in frame {i}")
        bx, by = wcs.wcs_world2pix(p["ra_deg"], p["dec_deg"], 0)
        if abs(float(bx) - p["x"]) > 0.01 or abs(float(by) - p["y"]) > 0.01:
            all_wcs = False
check("at every answer position the picture is bright (4 movers x 12 frames)", all_bright)
check("ra_deg/dec_deg of every answer match its pixel position through the file's WCS", all_wcs)

print("\n--- Part 4: get_frames and separation from the mock sky ---")
got = data_practice.get_frames(data_practice.PRACTICE_RA, data_practice.PRACTICE_DEC, 6.0)
check("get_frames gives 12 frames", len(got) == 12)
check("frames are sorted by date", [g["obs_time"] for g in got] == sorted(g["obs_time"] for g in got))
check("the practice set has nothing at WISE 0855's position", data_practice.get_frames(133.8, -7.2, 6.0) == [])
try:
    check("the normal mock set has nothing at the practice position",
          data_mock.get_frames(data_practice.PRACTICE_RA, data_practice.PRACTICE_DEC, 6.0) == [])
except FileNotFoundError:
    print("SKIPPED  no mock files (python data_mock.py) for the last check")

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")