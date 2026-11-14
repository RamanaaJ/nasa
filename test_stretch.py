# test_stretch.py
# Tests the stretch modes in processing.py, especially the new "asinh" (Backend 16).
#
# Part 1 needs nothing:                   python test_stretch.py
# Part 2 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 2 is skipped.

from pathlib import Path

import numpy as np
import requests
from astropy.io import fits

import params
import processing

BASE = "http://127.0.0.1:8000"
MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


# A smooth ramp from 0 to 100, one row of 101 pixels
ramp = np.linspace(0, 100, 101).reshape(1, 101)

print("--- Part 1: processing.stretch_image ---")
check("asinh is in STRETCH_MODES", "asinh" in processing.STRETCH_MODES)
grey = processing.stretch_image(ramp, mode="asinh")
check("asinh gives uint8", grey.dtype == np.uint8)
check("asinh keeps the shape", grey.shape == ramp.shape)
check("asinh runs from 0 to 255", int(grey.min()) == 0 and int(grey.max()) == 255)
check("asinh never gets darker as the input gets brighter", bool(np.all(np.diff(grey[0].astype(int)) >= 0)))

# Compare the middle pixel of the ramp in each mode
mid = {m: int(processing.stretch_image(ramp, mode=m)[0, 50]) for m in processing.STRETCH_MODES}
print("   middle pixel:", mid)
check("asinh lifts faint values more than linear", mid["asinh"] > mid["linear"])
check("asinh lifts faint values more than sqrt", mid["asinh"] > mid["sqrt"])
check("asinh is gentler than log", mid["asinh"] < mid["log"])

with_nan = ramp.copy()
with_nan[0, 10] = np.nan
check("NaN pixel is black in asinh", processing.stretch_image(with_nan, mode="asinh")[0, 10] == 0)
check("flat image is all black in asinh", int(processing.stretch_image(np.full((5, 5), 7.0), mode="asinh").max()) == 0)
check("all-NaN image is all black in asinh", int(processing.stretch_image(np.full((5, 5), np.nan), mode="asinh").max()) == 0)
check("old modes still work",
      all(processing.stretch_image(ramp, mode=m).dtype == np.uint8 for m in ("linear", "sqrt", "log")))
try:
    processing.stretch_image(ramp, mode="banana")
    check("unknown stretch is refused", False)
except ValueError:
    check("unknown stretch is refused", True)

print("\n--- Part 2: params.py ---")
check("stretch=asinh is accepted", params.validate_request("10", "0", None, "asinh").stretch == "asinh")
check("stretch=ASINH (capitals) is accepted", params.validate_request("10", "0", None, "ASINH").stretch == "asinh")
try:
    params.validate_request("10", "0", None, "banana")
    check("the error for a bad stretch is still raised", False)
except ValueError as err:
    print("        message:", err)
    check("the error for a bad stretch is still raised and now lists asinh", "asinh" in str(err))

print("\n--- Part 3: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    header = fits.getheader(MOCK_FILE)
    RA, DEC = header["CRVAL1"], header["CRVAL2"]
    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "stretch": "asinh"})
    check("stretch=asinh gives 200", r.status_code == 200)
    first = r.json()["frames"][0]
    check("the image link carries stretch=asinh", "stretch=asinh" in first["image_url"])
    img = requests.get(BASE + first["image_url"])
    check("the asinh image is a PNG", img.status_code == 200 and img.content[:8] == b"\x89PNG\r\n\x1a\n")
    sq = requests.get(BASE + first["image_url"].replace("stretch=asinh", "stretch=sqrt"))
    check("the asinh picture differs from the sqrt picture", img.content != sq.content)

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")