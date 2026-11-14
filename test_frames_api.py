# test_frames_api.py
# Tests the Frames endpoint in main.py.
#
# 1. In one terminal window, start the server:   uvicorn main:app --reload
# 2. In a second terminal window, run:           python test_frames_api.py
#
# (The `requests` library is already in requirements.txt.)

import sys
import time
from pathlib import Path

import requests
from astropy.io import fits

import cache

BASE = "http://127.0.0.1:8000"
MOCK_FILE = Path(__file__).parent / "data" / "mock" / "mock_00.fits"
STATIC_DIR = Path(__file__).parent / "static"

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


# The centre of the mock images, read from the file header
header = fits.getheader(MOCK_FILE)
RA, DEC = header["CRVAL1"], header["CRVAL2"]
FOV = 6.0

try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("Cannot reach the server. Start it first with:  uvicorn main:app --reload")
    sys.exit(1)

print("--- Test 1: the frame list ---")
r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "fov": FOV})
check("status 200", r.status_code == 200)
data = r.json()
frames = data.get("frames", [])
check("12 frames", data.get("frame_count") == 12 and len(frames) == 12)
check("source is 'mock'", data.get("source") == "mock")
needed = {"index", "image_url", "obs_time", "detector", "wavelength_um", "width_px",
          "height_px", "pixel_scale_arcsec", "center_ra_deg", "center_dec_deg"}
check("every frame has all the expected fields", all(needed <= set(f) for f in frames))
dates = [f["obs_time"] for f in frames]
check("frames are sorted by date", dates == sorted(dates))
check("detectors run 1..6 then repeat", [f["detector"] for f in frames][:7] == [1, 2, 3, 4, 5, 6, 1])
check("wavelengths grow from 0.75 to 5.0",
      abs(frames[0]["wavelength_um"] - 0.75) < 0.01 and abs(frames[-1]["wavelength_um"] - 5.0) < 0.01)
f0 = frames[0]
print(f"   frame 0: {f0['width_px']}x{f0['height_px']} px, scale {f0['pixel_scale_arcsec']:.3f} arcsec/px, "
      f"centre {f0['center_ra_deg']:.5f} {f0['center_dec_deg']:+.5f}")
check("pixel scale is about 6.2 arcsec (the mock value)", abs(f0["pixel_scale_arcsec"] - 6.2) < 0.05)
check("cutout is about 58 px wide (6 arcmin / 6.2 arcsec)", 55 <= f0["width_px"] <= 61)
off_arcsec = max(abs(f0["center_ra_deg"] - RA) * 3600 * 0.99, abs(f0["center_dec_deg"] - DEC) * 3600)
check(f"cutout centre is within 7 arcsec of the request (off by {off_arcsec:.1f})", off_arcsec < 7)

print("\n--- Test 2: an image link works ---")
img = requests.get(BASE + f0["image_url"])
check("status 200", img.status_code == 200)
check("content type is image/png", img.headers.get("content-type") == "image/png")
check("bytes start with the PNG signature", img.content[:8] == b"\x89PNG\r\n\x1a\n")
last = requests.get(BASE + frames[-1]["image_url"])
check("the last frame's image link works too", last.status_code == 200)
check("first and last pictures differ", img.content != last.content)
n_files, _ = cache.cache_info()
check(f"the cache now holds {n_files} file(s) (should be 1 or more)", n_files >= 1)

print("\n--- Test 3: a different stretch ---")
r2 = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "fov": FOV, "stretch": "log"})
check("log stretch is accepted and put in the links", "stretch=log" in r2.json()["frames"][0]["image_url"])
check("capital letters are fine (stretch=LOG)",
      requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "stretch": "LOG"}).status_code == 200)
check("a bad stretch gives 400",
      requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "stretch": "banana"}).status_code == 400)

print("\n--- Test 4: things that should fail politely ---")
no_img = requests.get(f"{BASE}/api/frames/99/image", params={"ra": RA, "dec": DEC, "fov": FOV})
check("frame number 99 gives 404", no_img.status_code == 404)
print("   message:", no_img.json().get("detail"))
far = requests.get(f"{BASE}/api/frames", params={"ra": (RA + 5) % 360, "dec": DEC, "fov": FOV})
check("a position far from the images gives 404", far.status_code == 404)
print("   message:", far.json().get("detail"))
for label, query in [("RA 400", {"ra": 400, "dec": 0}),
                     ("Dec 95", {"ra": 10, "dec": 95}),
                     ("FOV 100 (above the limit)", {"ra": RA, "dec": DEC, "fov": 100})]:
    resp = requests.get(f"{BASE}/api/frames", params=query)
    check(f"{label} is refused with 400 and a message", resp.status_code == 400 and "detail" in resp.json())
    print("   message:", resp.json().get("detail"))
check("missing RA is refused (422, FastAPI's own message)",
      requests.get(f"{BASE}/api/frames", params={"dec": 0}).status_code == 422)

print("\n--- Test 5: the static/ folder is served ---")
STATIC_DIR.mkdir(exist_ok=True)
probe = STATIC_DIR / "_test_probe.txt"
probe.write_text("hello from static")
try:
    s = requests.get(BASE + "/_test_probe.txt")
    check("a file in static/ can be fetched", s.status_code == 200 and s.text == "hello from static")
finally:
    # On Windows a file cannot be deleted while the server still has it open.
    # The server lets go a moment after replying, so try a few times.
    for _ in range(20):
        try:
            probe.unlink()
            break
        except PermissionError:
            time.sleep(0.25)
    else:
        print("   (could not delete static/_test_probe.txt; delete it by hand)")
check("the API still works next to static files", requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC}).status_code == 200)

print("\n--- Test 6: URL parameters (Backend 11) ---")


def to_hms(ra_deg):
    hours = ra_deg / 15
    h = int(hours)
    m = int((hours - h) * 60)
    sec = (hours - h - m / 60) * 3600
    return f"{h:02d}h{m:02d}m{sec:07.4f}s"


def to_dms(dec_deg):
    sign = "-" if dec_deg < 0 else "+"
    d = abs(dec_deg)
    deg = int(d)
    m = int((d - deg) * 60)
    sec = (d - deg - m / 60) * 3600
    return f"{sign}{deg:02d}d{m:02d}m{sec:07.4f}s"


hms, dms = to_hms(RA), to_dms(DEC)
print(f"   RA {RA:.5f} written as {hms}, Dec {DEC:.5f} written as {dms}")
r = requests.get(f"{BASE}/api/frames", params={"ra": hms, "dec": dms, "fov": FOV})
check("sexagesimal RA and Dec are accepted", r.status_code == 200)
echo = r.json()
check("they come back as the same degrees",
      abs(echo.get("ra_deg", 0) - RA) < 1e-5 and abs(echo.get("dec_deg", 0) - DEC) < 1e-5)
check("the image links use plain numbers", "ra=" + str(echo["ra_deg"]) in echo["frames"][0]["image_url"])

r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC})
check("fov missing -> default 6 arcmin", r.status_code == 200 and r.json()["fov_arcmin"] == 6.0)
check("mode missing -> normal, and it is in the links",
      r.json()["mode"] == "normal" and "mode=normal" in r.json()["frames"][0]["image_url"])
check("mode=normal is accepted",
      requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "normal"}).status_code == 200)

for label, query in [("mode=difference (not built yet)", {"ra": RA, "dec": DEC, "mode": "difference"}),
                     ("mode=banana", {"ra": RA, "dec": DEC, "mode": "banana"}),
                     ("fov=big", {"ra": RA, "dec": DEC, "fov": "big"}),
                     ("ra=abc", {"ra": "abc", "dec": DEC}),
                     ("RA hours 25h", {"ra": "25h", "dec": 0})]:
    resp = requests.get(f"{BASE}/api/frames", params=query)
    check(f"{label} gives 400 and a message", resp.status_code == 400 and "detail" in resp.json())
    print("   message:", resp.json().get("detail"))

bad_image = requests.get(f"{BASE}/api/frames/0/image", params={"ra": RA, "dec": 95})
check("the image endpoint checks the settings too", bad_image.status_code == 400)

print("\nTry it in your browser:")
print(f"  {BASE}/api/frames?ra={RA}&dec={DEC}&fov={FOV}")
print(f"  {BASE}{f0['image_url']}")
print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")