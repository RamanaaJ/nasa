# test_stack.py
# Tests stacking (Backend 19).
#
# Parts 1-4 need the mock files:          python test_stack.py
# Part 5 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 5 is skipped.

import io
from datetime import datetime, timedelta
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


def fake(detector, value, day, wave, flag=0, image=None, size=20):
    """A small frame with the keys stack_frames needs."""
    if image is None:
        image = np.full((size, size), float(value))
    return {"image": image, "variance": np.full(image.shape, 1.0),
            "flags": np.full(image.shape, flag, dtype=np.int32),
            "detector": detector, "wavelength_um": wave,
            "obs_time": datetime(2026, 1, 1) + timedelta(days=day),
            "wcs": None, "source_file": f"f{day}"}


# detector 1 at days 0 and 2, detector 2 at days 1 and 3
frames = [fake(1, 10, 0, 1.0, flag=1), fake(2, 20, 1, 2.0, flag=2),
          fake(1, 30, 2, 3.0, flag=4), fake(2, 40, 3, 4.0, flag=8)]

print("--- Part 1: stack_frames on tiny fake frames ---")
by_det = processing.stack_frames(frames, "mean", "detector")
check("two detectors give two stacked frames", len(by_det) == 2)
check("detectors are 1 and 2", [f["detector"] for f in by_det] == [1, 2])
check("mean of detector 1 is (10+30)/2 = 20", np.all(by_det[0]["image"] == 20.0))
check("mean of detector 2 is (20+40)/2 = 30", np.all(by_det[1]["image"] == 30.0))
check("n_stacked is 2 for both", [f["n_stacked"] for f in by_det] == [2, 2])
check("wavelength is the mean (2.0 and 3.0)", by_det[0]["wavelength_um"] == 2.0 and by_det[1]["wavelength_um"] == 3.0)
check("time is the mean (days 1 and 2)",
      by_det[0]["obs_time"] == datetime(2026, 1, 2) and by_det[1]["obs_time"] == datetime(2026, 1, 3))
check("flags are OR-ed (1|4 = 5 and 2|8 = 10)",
      np.all(by_det[0]["flags"] == 5) and np.all(by_det[1]["flags"] == 10))
check("variance of a mean of 2 is 1/2", np.allclose(by_det[0]["variance"], 0.5))
check("source_file says what was stacked", "stack of 2" in by_det[0]["source_file"])

summed = processing.stack_frames(frames, "sum", "detector")
check("sum of detector 1 is 10+30 = 40", np.all(summed[0]["image"] == 40.0))
check("sum of detector 2 is 20+40 = 60", np.all(summed[1]["image"] == 60.0))
check("variance of a sum of 2 is 2", np.allclose(summed[0]["variance"], 2.0))

everything = processing.stack_frames(frames, "mean", "all")
check("group=all gives one frame", len(everything) == 1)
check("its detector is 0 (mixed)", everything[0]["detector"] == 0)
check("its mean is (10+20+30+40)/4 = 25", np.all(everything[0]["image"] == 25.0))
check("n_stacked is 4", everything[0]["n_stacked"] == 4)
check("flags OR of all four = 15", np.all(everything[0]["flags"] == 15))
check("variance of a mean of 4 is 1/4", np.allclose(everything[0]["variance"], 0.25))
check("wavelength mean of 1,2,3,4 is 2.5", everything[0]["wavelength_um"] == 2.5)

check("input order does not matter (result sorted by time)",
      [f["detector"] for f in processing.stack_frames(frames[::-1], "mean", "detector")] == [1, 2])
check("original frames are not changed",
      frames[0]["image"][0, 0] == 10.0 and "n_stacked" not in frames[0] and frames[0]["detector"] == 1)
check("one frame stacks to itself", np.all(processing.stack_frames(frames[:1])[0]["image"] == 10.0))
check("empty list gives empty list", processing.stack_frames([]) == [])

nan_frames = [fake(1, 10, 0, 1.0), fake(1, 30, 2, 3.0)]
nan_frames[0]["image"][3, 3] = np.nan
nan_frames[0]["image"][5, 5] = np.nan
nan_frames[1]["image"][5, 5] = np.nan
nan_mean = processing.stack_frames(nan_frames, "mean")[0]["image"]
nan_sum = processing.stack_frames(nan_frames, "sum")[0]["image"]
check("a pixel that is NaN in one frame uses the other (mean = 30)", nan_mean[3, 3] == 30.0)
check("same for the sum (30)", nan_sum[3, 3] == 30.0)
check("a pixel that is NaN in every frame stays NaN", bool(np.isnan(nan_mean[5, 5])) and bool(np.isnan(nan_sum[5, 5])))

check("unknown combine is refused", fails(processing.stack_frames, frames, "banana"))
check("unknown group is refused", fails(processing.stack_frames, frames, "mean", "banana"))
check("frames of different sizes are refused",
      fails(processing.stack_frames, [fake(1, 1, 0, 1.0, size=20), fake(1, 1, 1, 1.0, size=30)]))

print("\n--- Part 2: stacking really cuts noise ---")
rng = np.random.default_rng(0)
noisy = [fake(1, 0, day, 1.0, image=rng.normal(0.0, 1.0, (100, 100))) for day in range(4)]
single_std = float(np.std(noisy[0]["image"]))
mean_std = float(np.std(processing.stack_frames(noisy, "mean")[0]["image"]))
sum_std = float(np.std(processing.stack_frames(noisy, "sum")[0]["image"]))
print(f"   noise: one frame {single_std:.3f}, mean of 4 {mean_std:.3f} (expect 0.5), sum of 4 {sum_std:.3f} (expect 2.0)")
check("a mean of 4 frames has about half the noise", 0.45 < mean_std < 0.55)
check("a sum of 4 frames has about twice the noise", 1.8 < sum_std < 2.2)

print("\n--- Part 3: on the mock data ---")
header = fits.getheader(MOCK_FILE)
RA, DEC = header["CRVAL1"], header["CRVAL2"]
mock = data_mock.get_frames(RA, DEC, 6.0)
check("12 mock frames", len(mock) == 12)
stacked = processing.stack_frames(mock, "mean", "detector")
check("6 stacked frames (one per detector)", len(stacked) == 6)
check("each holds 2 frames", all(f["n_stacked"] == 2 for f in stacked))
check("detectors 1 to 6 are all there", sorted(f["detector"] for f in stacked) == [1, 2, 3, 4, 5, 6])
d1 = next(f for f in stacked if f["detector"] == 1)
check("detector 1 = mean of mock frames 0 and 6",
      np.allclose(d1["image"], (mock[0]["image"] + mock[6]["image"]) / 2, equal_nan=True))
check("stacked frames are sorted by date", [f["obs_time"] for f in stacked] == sorted(f["obs_time"] for f in stacked))
everything = processing.stack_frames(mock, "mean", "all")
check("group=all gives 1 frame holding all 12", len(everything) == 1 and everything[0]["n_stacked"] == 12)
check("the mock frames themselves are not changed", len(mock) == 12 and "n_stacked" not in mock[0])

print("\n--- Part 4: params.py ---")
p = params.validate_request("10", "0", mode="stack")
check("defaults are combine=mean, group=detector", p.combine == "mean" and p.group == "detector")
check("combine=sum", params.validate_request("10", "0", combine="sum").combine == "sum")
check("combine=SUM (capitals)", params.validate_request("10", "0", combine="SUM").combine == "sum")
check("group=all", params.validate_request("10", "0", group="all").group == "all")
check("empty combine and group mean the defaults",
      params.validate_request("10", "0", combine="", group="").combine == "mean")
check("combine=banana is refused", fails(params.validate_request, "10", "0", combine="banana"))
check("group=banana is refused", fails(params.validate_request, "10", "0", group="banana"))
check("mode=stack is accepted", params.validate_request("10", "0", mode="stack").mode == "stack")
check("old seven-setting calls still work",
      params.validate_request("10", "0", "6", "log", "normal", "on", "previous").ref == "previous")

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

    r = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "stack"})
    check("mode=stack gives 200", r.status_code == 200)
    data = r.json()
    check("6 frames in the list (one per detector)", data["frame_count"] == 6 and len(data["frames"]) == 6)
    check("every frame says it holds 2 images", all(f["n_stacked"] == 2 for f in data["frames"]))
    check("mode, combine and group are echoed",
          data["mode"] == "stack" and data["combine"] == "mean" and data["group"] == "detector")
    link = data["frames"][0]["image_url"]
    check("links carry mode=stack, combine=mean and group=detector",
          "mode=stack" in link and "combine=mean" in link and "group=detector" in link)
    dates = [f["obs_time"] for f in data["frames"]]
    check("stacked frames are sorted by date", dates == sorted(dates))
    check("pixel scale and size are still reported", data["frames"][0]["width_px"] > 0)

    g_stack = get_grey(data["frames"][2]["image_url"])
    normal = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC}).json()
    check("normal mode still lists 12 frames", normal["frame_count"] == 12)
    g_normal = get_grey(normal["frames"][2]["image_url"])
    check("a stacked picture differs from a raw one", not np.array_equal(g_stack, g_normal))
    check("the last stacked frame (5) has a picture", get_grey(data["frames"][5]["image_url"]).shape == g_stack.shape)

    miss = requests.get(f"{BASE}/api/frames/6/image", params={"ra": RA, "dec": DEC, "mode": "stack"})
    check("frame 6 does not exist in a 6-frame stack (404)", miss.status_code == 404)
    print("   message:", miss.json().get("detail"))

    ra_all = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "stack", "group": "all"}).json()
    check("group=all gives 1 frame with detector 0 and n_stacked 12",
          ra_all["frame_count"] == 1 and ra_all["frames"][0]["detector"] == 0 and ra_all["frames"][0]["n_stacked"] == 12)
    check("its picture works", get_grey(ra_all["frames"][0]["image_url"]).shape == g_stack.shape)

    rs = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "stack", "combine": "sum"})
    check("combine=sum is echoed and in the links",
          rs.json()["combine"] == "sum" and "combine=sum" in rs.json()["frames"][0]["image_url"])
    check("combine=sum gives a picture", get_grey(rs.json()["frames"][0]["image_url"]).shape == g_stack.shape)

    rm = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "stack", "match": "on"})
    check("stack works together with match=on", get_grey(rm.json()["frames"][1]["image_url"]).shape == g_stack.shape)

    for name in ("combine", "group"):
        bad = requests.get(f"{BASE}/api/frames", params={"ra": RA, "dec": DEC, "mode": "stack", name: "banana"})
        check(f"{name}=banana gives 400 and a message", bad.status_code == 400 and "detail" in bad.json())
        print("   message:", bad.json().get("detail"))
        bad_img = requests.get(f"{BASE}/api/frames/0/image",
                               params={"ra": RA, "dec": DEC, "mode": "stack", name: "banana"})
        check(f"the image endpoint checks {name} too", bad_img.status_code == 400)

    print("\nTry it in your browser:")
    print(f"  {BASE}/api/frames/2/image?ra={RA}&dec={DEC}&fov=6&mode=stack")
    print(f"  {BASE}/api/frames/2/image?ra={RA}&dec={DEC}&fov=6&mode=normal")

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")