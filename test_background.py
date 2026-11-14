# test_background.py
# Tests background-level matching (Backend 17).
#
# Parts 1-5 need nothing:                 python test_background.py
# Part 6 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 6 is skipped.

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


def fails(func, *args):
    """True if the call raises a ValueError. Prints the message."""
    try:
        func(*args)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


# Small fake sky: noise around 0 plus one bright "star". Each test frame is
# this same sky plus a different constant background.
rng = np.random.default_rng(1)
base = rng.normal(0.0, 1.0, (40, 40))
base[20, 20] += 300.0


def make_frames(offsets):
    return [{"image": base + off, "source_file": f"fake_{i}"} for i, off in enumerate(offsets)]


def levels(frames):
    return [processing.estimate_background(f["image"]) for f in frames]


print("--- Part 1: estimate_background ---")
check("flat image gives its value", processing.estimate_background(np.full((5, 5), 7.0)) == 7.0)
with_nan = np.full((5, 5), 7.0)
with_nan[0, 0] = np.nan
check("NaN pixels are ignored", processing.estimate_background(with_nan) == 7.0)
check("all-NaN image gives None", processing.estimate_background(np.full((5, 5), np.nan)) is None)
check("a bright star hardly moves it", abs(processing.estimate_background(base + 10.0) - 10.0) < 0.2)

print("\n--- Part 2: match_backgrounds ---")
frames = make_frames([0.0, 5.0, -3.0, 10.0])
before = levels(frames)
matched = processing.match_backgrounds(frames)
after = levels(matched)
print(f"   levels before: {[round(x, 2) for x in before]}")
print(f"   levels after : {[round(x, 2) for x in after]}")
check("backgrounds differed before", max(before) - min(before) > 10)
check("backgrounds are equal after", max(after) - min(after) < 1e-9)
check("the common level is the median of the old levels", abs(after[0] - float(np.median(before))) < 1e-9)
check("same number of frames", len(matched) == 4)
check("original frames are not changed", np.array_equal(frames[1]["image"], base + 5.0))
check("contrast is kept (star and noise unchanged)",
      all(np.allclose(m["image"] - a, f["image"] - b)
          for m, f, a, b in zip(matched, frames, after, before)))
check("other keys are kept", matched[0]["source_file"] == "fake_0")

nan_frames = make_frames([0.0, 5.0])
nan_frames[0]["image"] = nan_frames[0]["image"].copy()
nan_frames[0]["image"][3, 3] = np.nan
nan_matched = processing.match_backgrounds(nan_frames)
check("NaN stays NaN", bool(np.isnan(nan_matched[0]["image"][3, 3])))

mixed = make_frames([0.0, 5.0]) + [{"image": np.full((40, 40), np.nan)}]
mixed_matched = processing.match_backgrounds(mixed)
check("an all-NaN frame does not crash and stays all-NaN", bool(np.isnan(mixed_matched[2]["image"]).all()))
check("the other frames are still matched", abs(levels(mixed_matched[:2])[0] - levels(mixed_matched[:2])[1]) < 1e-9)
check("empty list gives an empty list", processing.match_backgrounds([]) == [])
single = make_frames([4.0])
check("one frame is left as it is", np.allclose(processing.match_backgrounds(single)[0]["image"], single[0]["image"]))

print("\n--- Part 3: shared_limits and stretch_image(limits=...) ---")
lim = processing.shared_limits(make_frames([0.0, 5.0]))
check("shared_limits gives (vmin, vmax) with vmin < vmax", lim is not None and lim[0] < lim[1])
check("no usable pixels gives None", processing.shared_limits([{"image": np.full((3, 3), np.nan)}]) is None)
check("empty list gives None", processing.shared_limits([]) is None)
ramp = np.linspace(0, 100, 101).reshape(1, 101)
grey = processing.stretch_image(ramp, mode="linear", limits=(0.0, 50.0))
check("limits: below/at the low point is black", int(grey[0, 0]) == 0)
check("limits: at and above the high point is white", int(grey[0, 50]) == 255 and int(grey[0, 100]) == 255)
check("limits: the middle of the range is mid-grey", 120 <= int(grey[0, 25]) <= 135)
check("limits=None still works as before",
      np.array_equal(processing.stretch_image(ramp), processing.stretch_image(ramp, limits=None)))

print("\n--- Part 4: why matching and shared limits go together ---")
a_img, b_img = base + 10.0, base + 60.0


def mean_grey(image, limits=None):
    return float(processing.stretch_image(image, limits=limits).astype(float).mean())


check("alone, each frame's own stretch already hides a pure offset",
      abs(mean_grey(a_img) - mean_grey(b_img)) < 1)
raw = [{"image": a_img}, {"image": b_img}]
raw_lim = processing.shared_limits(raw)
gap_raw = abs(mean_grey(a_img, raw_lim) - mean_grey(b_img, raw_lim))
print(f"   same scale, no matching: pictures differ by {gap_raw:.0f} grey levels")
check("same scale WITHOUT matching: the pictures look very different", gap_raw > 50)
fixed = processing.match_backgrounds(raw)
fixed_lim = processing.shared_limits(fixed)
gap_fixed = abs(mean_grey(fixed[0]["image"], fixed_lim) - mean_grey(fixed[1]["image"], fixed_lim))
print(f"   same scale, with matching: pictures differ by {gap_fixed:.2f} grey levels")
check("same scale WITH matching: the pictures look the same", gap_fixed < 1)

print("\n--- Part 5: params.py ---")
check("default is off", params.validate_request("10", "0").match is False)
for word in ("on", "ON", "1", "true", "Yes", True):
    check(f"match={word!r} means on", params.validate_request("10", "0", match=word).match is True)
for word in ("off", "0", "false", "no", "", None):
    check(f"match={word!r} means off", params.validate_request("10", "0", match=word).match is False)
check("match=banana is refused",
      fails(params.validate_request, "10", "0", None, None, None, "banana"))
check("old five-setting calls still work",
      params.validate_request("10", "0", "6", "log", "normal").stretch == "log")

print("\n--- Part 6: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    header = fits.getheader(MOCK_FILE)
    RA, DEC = header["CRVAL1"], header["CRVAL2"]

    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC})
    check("match missing -> off, shown in the answer and the links",
          r.status_code == 200 and r.json()["match"] is False and "match=off" in r.json()["frames"][0]["image_url"])

    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "match": "on"})
    check("match=on gives 200", r.status_code == 200)
    data = r.json()
    check("match=on is echoed and put in the image links",
          data["match"] is True and "match=on" in data["frames"][0]["image_url"])
    for i in (0, 11):
        img = requests.get(BASE + data["frames"][i]["image_url"])
        check(f"matched image {i} is a PNG", img.status_code == 200 and img.content[:8] == b"\x89PNG\r\n\x1a\n")

    bad = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "match": "banana"})
    check("match=banana gives 400 and a message", bad.status_code == 400 and "detail" in bad.json())
    print("   message:", bad.json().get("detail"))
    bad_img = requests.get(f"{BASE}/api/frames/0/image", params={"ra": RA, "dec": DEC, "match": "banana"})
    check("the image endpoint checks match too", bad_img.status_code == 400)
    missing = requests.get(f"{BASE}/api/frames/99/image", params={"ra": RA, "dec": DEC, "match": "on"})
    check("frame 99 with match=on still gives 404", missing.status_code == 404)

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")