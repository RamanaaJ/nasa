# test_expected.py
# Tests the expected path (Backend 22).
#
# Parts 1-3 need nothing:                 python test_expected.py
# Part 4 needs the mock files:            python data_mock.py   (once)
# Part 5 needs the server running first:  uvicorn main:app --reload   (other terminal)
# Parts 4 and 5 are skipped if their requirements are missing.

import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.wcs import WCS

import processing
import targets
from targets import TARGETS, position_at_epoch

BASE = "http://127.0.0.1:8000"
MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fails(func, *args):
    try:
        func(*args)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


print("--- Part 1: decimal_year ---")
check("2026-01-01 is 2026.0", abs(targets.decimal_year(datetime(2026, 1, 1)) - 2026.0) < 1e-9)
check("2026-07-02 12:00 is 2026.5", abs(targets.decimal_year(datetime(2026, 7, 2, 12)) - 2026.5) < 1e-9)
check("a leap year starts on its whole number too", abs(targets.decimal_year(datetime(2028, 1, 1)) - 2028.0) < 1e-9)
check("the last second of 2026 is just below 2027",
      2026.99 < targets.decimal_year(datetime(2026, 12, 31, 23, 59, 59)) < 2027.0)
check("a timezone-aware time gives the same answer",
      abs(targets.decimal_year(datetime(2026, 7, 2, 12, tzinfo=timezone.utc)) - 2026.5) < 1e-9)

print("\n--- Part 2: expected_positions ---")
times = [datetime(2026, 1, 1), datetime(2026, 7, 2, 12), datetime(2027, 1, 1)]
pos = targets.expected_positions("barnard", times)
check("one position per time", len(pos) == 3)
ra, dec = position_at_epoch("barnard", 2026.0)
check("first position = position_at_epoch(2026.0)",
      abs(pos[0][0] - ra % 360) < 1e-9 and abs(pos[0][1] - dec) < 1e-9)
check("Barnard's Star moves north (Dec grows) as time passes", pos[0][1] < pos[1][1] < pos[2][1])
check("every target gives RA in 0..360",
      all(0 <= p[0] < 360 for t in TARGETS for p in targets.expected_positions(t, times)))
check("empty list gives empty list", targets.expected_positions("barnard", []) == [])
check("unknown target id is refused", fails(targets.expected_positions, "vega", times))

print("\n--- Part 3: locate_in_frames on a fake frame ---")
w = WCS(naxis=2)
w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
w.wcs.crval = [150.0, 2.0]
w.wcs.crpix = [25.5, 25.5]                    # 1-based, so pixel 24.5 counting from 0
w.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
w.wcs.cunit = ["deg", "deg"]
frame = {"image": np.zeros((50, 50)), "wcs": w, "obs_time": datetime(2026, 1, 1)}

e = processing.locate_in_frames([frame], [(150.0, 2.0)])[0]
check("the reference position lands at pixel (24.5, 24.5)", abs(e["x"] - 24.5) < 0.01 and abs(e["y"] - 24.5) < 0.01)
check("and is inside", e["inside"] is True)
check("png position matches pixel_to_png_position",
      (e["png_x"], e["png_y"]) == processing.pixel_to_png_position(e["x"], e["y"], 50, 50))
check("obs_time is copied", e["obs_time"] == datetime(2026, 1, 1))

d_ra = 62 / 3600 / math.cos(math.radians(2.0))    # 10 pixels of 6.2 arcsec, towards the east
east = processing.locate_in_frames([frame], [(150.0 + d_ra, 2.0)])[0]
check("10 pixels EAST (bigger RA) is 10 pixels to the LEFT (x = 14.5)", abs(east["x"] - 14.5) < 0.05)
north = processing.locate_in_frames([frame], [(150.0, 2.0 + 62 / 3600)])[0]
check("10 pixels NORTH is y = 34.5", abs(north["y"] - 34.5) < 0.05)
far = processing.locate_in_frames([frame], [(151.0, 2.0)])[0]
check("a far position is reported with inside=False", far["inside"] is False and far["x"] is not None)
nowcs = processing.locate_in_frames([{"image": np.zeros((5, 5)), "obs_time": None}], [(1.0, 1.0)])[0]
check("a frame without a WCS gives x=None, inside=False", nowcs["x"] is None and nowcs["inside"] is False)
check("wrong number of positions is refused", fails(processing.locate_in_frames, [frame], []))
check("empty lists give an empty list", processing.locate_in_frames([], []) == [])
check("original frame is not changed", "x" not in frame)

if MOCK_FILE.exists():
    header = fits.getheader(MOCK_FILE)
    RA, DEC = header["CRVAL1"], header["CRVAL2"]

print("\n--- Part 4: on the mock data ---")
if not MOCK_FILE.exists():
    print("SKIPPED  no mock files. Run:  python data_mock.py")
else:
    import data_mock

    mock = data_mock.get_frames(RA, DEC, 6.0)
    check("12 mock frames", len(mock) == 12)
    positions = targets.expected_positions("wise0855", [f["obs_time"] for f in mock])
    located = processing.locate_in_frames(mock, positions)
    trail = processing.find_moving_dot(mock)
    gap = math.hypot(located[0]["x"] - trail[0]["x"], located[0]["y"] - trail[0]["y"])
    print(f"   frame 0: expected ({located[0]['x']:.1f}, {located[0]['y']:.1f}), "
          f"dot found at ({trail[0]['x']:.1f}, {trail[0]['y']:.1f}), gap {gap:.2f} px")
    check("frame 0: expected position is within 1.5 pixels of the mock dot "
          "(the mock dot starts at WISE 0855's 2026.0 position)", gap < 1.5)
    moved = math.hypot(located[-1]["x"] - located[0]["x"], located[-1]["y"] - located[0]["y"])
    dot_moved = math.hypot(trail[-1]["x"] - trail[0]["x"], trail[-1]["y"] - trail[0]["y"])
    print(f"   expected path moves {moved:.1f} px, the mock dot moves {dot_moved:.1f} px")
    check("the expected path moves about 1 pixel in 11 months (real speed); the mock dot is 10x faster",
          0.3 < moved < 3.0 and dot_moved > 5 * moved)
    check("all 12 expected positions are inside the cutout", all(x["inside"] for x in located))

print("\n--- Part 5: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    if not MOCK_FILE.exists():
        print("SKIPPED  no mock files.")
    else:
        q = {"ra": RA, "dec": DEC, "target": "wise0855"}
        r = requests.get(f"{BASE}/api/expected-path", params=q)
        check("status 200", r.status_code == 200)
        data = r.json()
        check("12 entries, target named", data["frame_count"] == 12 and len(data["path"]) == 12
              and data["target"]["id"] == "wise0855")
        needed = {"index", "obs_time", "ra_deg", "dec_deg", "x", "y", "png_x", "png_y", "inside"}
        check("every entry has all the fields", all(needed <= set(p) for p in data["path"]))
        frames_json = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC}).json()
        check("obs_time matches the frame list for every frame",
              [p["obs_time"] for p in data["path"]] == [f["obs_time"] for f in frames_json["frames"]])
        check("another spelling works (wise 0855)",
              requests.get(f"{BASE}/api/expected-path", params={**q, "target": "wise 0855"}).status_code == 200)
        st = requests.get(f"{BASE}/api/expected-path", params={**q, "mode": "stack"}).json()
        check("mode=stack gives 6 entries, like /api/frames", st["frame_count"] == 6)

        bad = requests.get(f"{BASE}/api/expected-path", params={**q, "target": "Vega"})
        check("an unknown target gives 400 and a message", bad.status_code == 400 and "detail" in bad.json())
        print("   message:", bad.json().get("detail"))
        miss = requests.get(f"{BASE}/api/expected-path", params={"ra": RA, "dec": DEC})
        check("missing target gives 422 with a sentence", miss.status_code == 422 and "target" in miss.json()["detail"])
        far = requests.get(f"{BASE}/api/expected-path", params={**q, "ra": (RA + 5) % 360})
        check("a position with no images gives 404", far.status_code == 404)

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")