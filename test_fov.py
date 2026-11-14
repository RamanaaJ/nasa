# test_fov.py
# Tests field-of-view handling (Backend 15).
#
# Part 1 needs the mock files only:       python test_fov.py
# Part 2 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 2 is skipped.

from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.wcs.utils import proj_plane_pixel_scales

import config
import data_mock
import params

BASE = "http://127.0.0.1:8000"
MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"
PIXEL_SCALE = 6.2          # arcsec per pixel in the mock files (an assumption, see PROGRESS.md)

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


header = fits.getheader(MOCK_FILE)
RA, DEC = header["CRVAL1"], header["CRVAL2"]

print("--- Part 1: cutouts at different field-of-view sizes ---")
widths = []
for fov in (config.MIN_FOV_ARCMIN, 3.0, 6.0, 15.0, config.MAX_FOV_ARCMIN):
    frames = data_mock.get_frames(RA, DEC, fov)
    check(f"fov {fov:g} arcmin: all 12 frames found", len(frames) == 12)
    f = frames[0]
    h, w = f["image"].shape
    expected = fov * 60 / PIXEL_SCALE
    nan_share = float(np.isnan(f["image"]).mean())
    print(f"   {w}x{h} px (expected about {expected:.1f}), {nan_share:.0%} of pixels are NaN (outside the image)")
    check(f"fov {fov:g} arcmin: width is about {expected:.0f} px", abs(w - expected) <= 2)
    check(f"fov {fov:g} arcmin: cutout is square", w == h)
    scale = float(np.mean(proj_plane_pixel_scales(f["wcs"]))) * 3600
    check(f"fov {fov:g} arcmin: pixel scale unchanged ({scale:.3f} arcsec/px)", abs(scale - PIXEL_SCALE) < 0.05)
    check(f"fov {fov:g} arcmin: flags and variance have the same shape",
          f["flags"].shape == f["image"].shape == f["variance"].shape)
    widths.append(w)
    if fov == 6.0:
        check("fov 6: the patch lies fully inside the mock image (no NaN)", nan_share == 0)
    if fov == config.MAX_FOV_ARCMIN:
        check("fov max: the patch is bigger than the mock image, so edges are NaN", nan_share > 0)
check("a bigger fov gives a bigger cutout", widths == sorted(widths) and len(set(widths)) == len(widths))

print("\n--- Part 2: params.py limits and rounding ---")
check("minimum is accepted", params.validate_request("10", "0", str(config.MIN_FOV_ARCMIN)).fov == config.MIN_FOV_ARCMIN)
check("maximum is accepted", params.validate_request("10", "0", str(config.MAX_FOV_ARCMIN)).fov == config.MAX_FOV_ARCMIN)
for label, value in [("just below the minimum", config.MIN_FOV_ARCMIN - 0.001),
                     ("just above the maximum", config.MAX_FOV_ARCMIN + 0.001)]:
    try:
        params.validate_request("10", "0", str(value))
        check(f"{label} is refused", False)
    except ValueError as err:
        print("        message:", err)
        check(f"{label} is refused", True)
check("6.0004 is rounded to 6.0", params.validate_request("10", "0", "6.0004").fov == 6.0)
check("6.0006 is rounded to 6.001", abs(params.validate_request("10", "0", "6.0006").fov - 6.001) < 1e-9)

print("\n--- Part 3: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    r = requests.get(f"{BASE}/api/limits")
    check("/api/limits gives 200", r.status_code == 200)
    lim = r.json().get("fov_arcmin", {})
    check("limits match config.py",
          lim == {"min": config.MIN_FOV_ARCMIN, "max": config.MAX_FOV_ARCMIN, "default": config.DEFAULT_FOV_ARCMIN})

    for fov in (config.MIN_FOV_ARCMIN, config.MAX_FOV_ARCMIN):
        resp = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "fov": fov})
        data = resp.json()
        check(f"fov {fov:g}: frame list works", resp.status_code == 200 and data.get("frame_count") == 12)
        img = requests.get(BASE + data["frames"][0]["image_url"])
        check(f"fov {fov:g}: image link gives a PNG",
              img.status_code == 200 and img.content[:8] == b"\x89PNG\r\n\x1a\n")

    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "fov": "6.0004"})
    check("fov 6.0004 is echoed as 6.0", r.json().get("fov_arcmin") == 6.0)
    for label, value in [("fov=0.5", "0.5"), ("fov=31", "31")]:
        resp = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "fov": value})
        check(f"{label} gives 400 and a message", resp.status_code == 400 and "detail" in resp.json())
        print("   message:", resp.json().get("detail"))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")