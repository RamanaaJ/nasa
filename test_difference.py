# test_difference.py
# Tests difference imaging (Backend 18).
#
# Parts 1-4 need the mock files:          python test_difference.py
# Part 5 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 5 is skipped.

import io
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from PIL import Image

import data_mock
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


def fails(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


def fake(dot_xy, value=100.0, variance=1.0):
    """A 40x40 empty frame with one bright dot."""
    image = np.zeros((40, 40))
    image[dot_xy[1], dot_xy[0]] = value
    return {"image": image, "variance": np.full((40, 40), variance),
            "flags": np.zeros((40, 40), dtype=np.int32), "source_file": "fake"}


print("--- Part 1: difference_frames on a tiny fake sky ---")
frames = [fake((10, 10)), fake((20, 20)), fake((30, 30))]
first = processing.difference_frames(frames, "first")
prev = processing.difference_frames(frames, "previous")
check("same number of frames", len(first) == 3 and len(prev) == 3)
check("frame 0 is all zeros (first)", not first[0]["image"].any())
check("frame 0 is all zeros (previous)", not prev[0]["image"].any())
check("first: old dot position is -100, new one +100",
      first[1]["image"][10, 10] == -100 and first[1]["image"][20, 20] == 100)
check("first: frame 2 still compares with frame 0",
      first[2]["image"][10, 10] == -100 and first[2]["image"][30, 30] == 100)
check("previous: frame 2 compares with frame 1",
      prev[2]["image"][20, 20] == -100 and prev[2]["image"][30, 30] == 100
      and prev[2]["image"][10, 10] == 0)
check("frame 1 is the same for first and previous", np.array_equal(first[1]["image"], prev[1]["image"]))
check("original frames are not changed", frames[1]["image"][10, 10] == 0 and frames[1]["image"][20, 20] == 100)
check("variances add", float(first[1]["variance"][0, 0]) == 2.0)
check("other keys are kept", first[1]["source_file"] == "fake")
nan_frames = [fake((10, 10)), fake((20, 20))]
nan_frames[1]["image"][5, 5] = np.nan
check("NaN stays NaN", bool(np.isnan(processing.difference_frames(nan_frames)[1]["image"][5, 5])))
check("empty list gives empty list", processing.difference_frames([]) == [])
check("unknown reference is refused", fails(processing.difference_frames, frames, "banana"))
other_size = [fake((10, 10)), {"image": np.zeros((30, 30))}]
check("frames of different sizes are refused", fails(processing.difference_frames, other_size))

print("\n--- Part 2: stretch_difference ---")
img = np.array([[-50.0, 0.0, 50.0, 25.0, np.nan]])
for mode in processing.STRETCH_MODES:
    g = processing.stretch_difference(img, mode=mode, limit=50.0)
    check(f"{mode}: -limit black, 0 mid grey, +limit white",
          g[0, 0] == 0 and g[0, 1] in (127, 128) and g[0, 2] == 255)
    check(f"{mode}: NaN is black", g[0, 4] == 0)
    sym = processing.stretch_difference(np.array([[-20.0, 20.0]]), mode=mode, limit=50.0)
    check(f"{mode}: +x and -x are mirror images", abs(int(sym[0, 0]) + int(sym[0, 1]) - 255) <= 1)
lin = processing.stretch_difference(img, mode="linear", limit=50.0)
check("linear: +25 is about 3/4 of the way to white", 188 <= lin[0, 3] <= 194)
none = processing.stretch_difference(img, mode="linear", limit=None)
check("no limit -> mid grey (NaN black)", none[0, 1] in (127, 128) and none[0, 4] == 0)
check("unknown stretch is refused", fails(processing.stretch_difference, img, "banana", 50.0))
big = []
for pos in ((10, 10), (20, 20), (30, 30)):
    f = fake(pos)
    f["image"][pos[1]-2:pos[1]+3, pos[0]-2:pos[0]+3] = 100.0   # 5x5 block, not a single pixel
    big.append(f)
lim = processing.shared_difference_limit(processing.difference_frames(big, "first"))
check("shared limit is a positive number", lim is not None and lim > 0)
check("all-zero frames give None", processing.shared_difference_limit(processing.difference_frames([fake((1, 1))])) is None)

print("\n--- Part 3: on the mock data ---")
header = fits.getheader(MOCK_FILE)
RA, DEC = header["CRVAL1"], header["CRVAL2"]
mock = data_mock.get_frames(RA, DEC, 6.0)
check("12 mock frames", len(mock) == 12)
d_first = processing.difference_frames(mock, "first")
d_prev = processing.difference_frames(mock, "previous")
check("frame 5 first = frame 5 minus frame 0", np.allclose(d_first[5]["image"], mock[5]["image"] - mock[0]["image"]))
check("frame 5 previous = frame 5 minus frame 4", np.allclose(d_prev[5]["image"], mock[5]["image"] - mock[4]["image"]))
check("the moving dot leaves a bright and a dark spot in frame 5",
      d_first[5]["image"].max() > 100 and d_first[5]["image"].min() < -100)
check("the fixed stars are mostly gone (typical |difference| is small)",
      float(np.median(np.abs(d_first[5]["image"]))) < 3)

print("\n--- Part 4: params.py ---")
check("default ref is first", params.validate_request("10", "0").ref == "first")
check("ref=previous", params.validate_request("10", "0", ref="previous").ref == "previous")
check("ref=PREVIOUS (capitals)", params.validate_request("10", "0", ref="PREVIOUS").ref == "previous")
check("empty ref means first", params.validate_request("10", "0", ref="").ref == "first")
check("ref=banana is refused", fails(params.validate_request, "10", "0", ref="banana"))
check("mode=difference is accepted", params.validate_request("10", "0", mode="difference").mode == "difference")
check("mode=stack is still not built", fails(params.validate_request, "10", "0", mode="stack"))
check("old six-setting calls still work", params.validate_request("10", "0", "6", "log", "normal", "on").match is True)

print("\n--- Part 5: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    def get_grey(url):
        r = requests.get(BASE + url)
        assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"
        return np.array(Image.open(io.BytesIO(r.content)))

    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "difference"})
    check("mode=difference gives 200", r.status_code == 200)
    data = r.json()
    check("mode and ref are echoed", data["mode"] == "difference" and data["ref"] == "first")
    check("links carry mode=difference and ref=first",
          "mode=difference" in data["frames"][0]["image_url"] and "ref=first" in data["frames"][0]["image_url"])

    g0 = get_grey(data["frames"][0]["image_url"])
    check("frame 0 is one flat grey", len(np.unique(g0)) == 1 and int(g0[0, 0]) in (127, 128))
    g5 = get_grey(data["frames"][5]["image_url"])
    check("frame 5 is not flat (the dot moved)", len(np.unique(g5)) > 5)
    check("frame 5 has both white and black spots", int(g5.max()) > 200 and int(g5.min()) < 60)

    rp = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "difference", "ref": "previous"})
    check("ref=previous is echoed", rp.json()["ref"] == "previous" and "ref=previous" in rp.json()["frames"][5]["image_url"])
    g5p = get_grey(rp.json()["frames"][5]["image_url"])
    check("first and previous give different pictures for frame 5", not np.array_equal(g5, g5p))

    gm = get_grey(requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "difference", "match": "on"})
                  .json()["frames"][5]["image_url"])
    check("difference works together with match=on", gm.shape == g5.shape)

    normal = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC}).json()
    gn = get_grey(normal["frames"][5]["image_url"])
    check("normal mode is unchanged (not a difference picture)", not np.array_equal(gn, g5))

    bad = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "difference", "ref": "banana"})
    check("ref=banana gives 400 and a message", bad.status_code == 400 and "detail" in bad.json())
    print("   message:", bad.json().get("detail"))
    bad_img = requests.get(f"{BASE}/api/frames/0/image", params={"ra": RA, "dec": DEC, "mode": "difference", "ref": "banana"})
    check("the image endpoint checks ref too", bad_img.status_code == 400)
    miss = requests.get(f"{BASE}/api/frames/99/image", params={"ra": RA, "dec": DEC, "mode": "difference"})
    check("frame 99 in difference mode gives 404", miss.status_code == 404)

    print("\nTry it in your browser (look at frame 5):")
    print(f"  {BASE}/api/frames/5/image?ra={RA}&dec={DEC}&fov=6&mode=difference&ref=first")
    print(f"  {BASE}/api/frames/5/image?ra={RA}&dec={DEC}&fov=6&mode=difference&ref=previous")

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")