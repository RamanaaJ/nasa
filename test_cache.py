# test_cache.py
# Tests cache.py. Run it with:  python test_cache.py
# It uses its own folder (cache/test_cache/), never your real cache, and
# deletes that folder at the end.

import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np

import cache
import config

TEST_DIR = config.CACHE_DIR / "test_cache"
shutil.rmtree(TEST_DIR, ignore_errors=True)

problems = 0


def check(label, ok):
    """Print PASS/FAIL for one check."""
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fake_frames(n=3):
    """A few small stand-in frames with the keys from FRAME_FORMAT.md."""
    return [{
        "image": np.full((5, 5), float(i)),
        "wcs": None,
        "obs_time": datetime(2026, 1, 1 + i),
        "wavelength_um": 1.0 + i,
        "detector": i + 1,
        "flags": np.zeros((5, 5), dtype=np.int32),
        "variance": np.ones((5, 5)),
        "source_file": f"fake_{i}.fits",
    } for i in range(n)]


print("--- Test 1: keys ---")
k1 = cache.make_key(133.81890, -7.24705, 6.0, "mock")
k2 = cache.make_key(133.818900001, -7.247050001, 6.0000001, "mock")
check("tiny differences give the same key", k1 == k2)
check("different FOV gives a different key", k1 != cache.make_key(133.81890, -7.24705, 8.0, "mock"))
check("different RA gives a different key", k1 != cache.make_key(133.9, -7.24705, 6.0, "mock"))
check("different release gives a different key", k1 != cache.make_key(133.81890, -7.24705, 6.0, "spherex_qr2"))
check("-0.0 and 0.0 give the same key", cache.make_key(-0.0, 0.0, 6, "x") == cache.make_key(0.0, 0.0, 6, "x"))
print("   example key:", k1)
check("release name with odd characters stays a safe file name",
      "/" not in cache.make_key(1, 2, 3, "a/b c") and " " not in cache.make_key(1, 2, 3, "a/b c"))
try:
    cache.make_key(float("nan"), 0, 6)
    check("NaN is rejected", False)
except ValueError:
    check("NaN is rejected", True)

print("\n--- Test 2: miss, save, hit ---")
check("empty cache gives None", cache.get(10, 20, 6, "mock", TEST_DIR) is None)
frames = fake_frames()
path = cache.save(frames, 10, 20, 6, "mock", TEST_DIR)
check("save made a file", path is not None and path.exists())
back = cache.get(10, 20, 6, "mock", TEST_DIR)
check("get returns the same number of frames", back is not None and len(back) == 3)
check("image data is identical", np.array_equal(back[2]["image"], frames[2]["image"]))
check("date and detector survive", back[1]["obs_time"] == datetime(2026, 1, 2) and back[1]["detector"] == 2)
check("other release does not see it", cache.get(10, 20, 6, "other", TEST_DIR) is None)
check("other FOV does not see it", cache.get(10, 20, 8, "mock", TEST_DIR) is None)

print("\n--- Test 3: get_or_load calls the loader only once ---")
calls = []


def slow_loader(ra, dec, fov):
    calls.append(1)
    time.sleep(0.3)            # pretend this is a slow download
    return fake_frames()


t0 = time.time()
first = cache.get_or_load(50, -30, 6, slow_loader, "mock", TEST_DIR)
t_first = time.time() - t0
t0 = time.time()
second = cache.get_or_load(50, -30, 6, slow_loader, "mock", TEST_DIR)
t_second = time.time() - t0
check("loader was called once for two requests", len(calls) == 1)
check(f"second request was faster ({t_first:.3f}s then {t_second:.3f}s)", t_second < t_first)
check("both requests gave the same data", np.array_equal(first[0]["image"], second[0]["image"]))

print("\n--- Test 4: empty results are not cached ---")
empty_calls = []


def empty_loader(ra, dec, fov):
    empty_calls.append(1)
    return []


cache.get_or_load(1, 1, 6, empty_loader, "mock", TEST_DIR)
cache.get_or_load(1, 1, 6, empty_loader, "mock", TEST_DIR)
check("loader called again after an empty result", len(empty_calls) == 2)

print("\n--- Test 5: damaged cache file ---")
bad_path = cache.save(fake_frames(), 70, 70, 6, "mock", TEST_DIR)
bad_path.write_bytes(b"this is not a pickle")
check("damaged file is treated as a miss", cache.get(70, 70, 6, "mock", TEST_DIR) is None)
check("damaged file was deleted", not bad_path.exists())

print("\n--- Test 6: info and clear ---")
n, size = cache.cache_info(TEST_DIR)
print(f"   {n} file(s), {size} bytes")
check("cache_info sees files", n >= 2 and size > 0)
removed = cache.clear_cache(TEST_DIR)
check("clear_cache deleted them all", removed == n and cache.cache_info(TEST_DIR)[0] == 0)

print("\n--- Test 7: mock and real data use different keys ---")
saved_flag = config.USE_MOCK
config.USE_MOCK = True
mock_key = cache.make_key(1, 2, 3)
config.USE_MOCK = False
real_key = cache.make_key(1, 2, 3)
config.USE_MOCK = saved_flag
check("mock key differs from real key", mock_key != real_key)
check("real key contains the release name", config.RELEASE_NAME in real_key)

print("\n--- Test 8: many requests at once (like the web page asking for 12 images) ---")
thread_calls = []


def counting_loader(ra, dec, fov):
    thread_calls.append(1)
    time.sleep(0.2)
    return fake_frames()


results = []
threads = [threading.Thread(
    target=lambda: results.append(cache.get_or_load(90, 45, 6, counting_loader, "mock", TEST_DIR)))
    for _ in range(8)]
for th in threads:
    th.start()
for th in threads:
    th.join()
check("8 simultaneous requests gave 8 answers", len(results) == 8 and all(len(r) == 3 for r in results))
check("the loader ran only once", len(thread_calls) == 1)

print("\n--- Test 9: a real WCS survives (needs astropy) ---")
try:
    from astropy.wcs import WCS
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [133.8, -7.2]
    w.wcs.crpix = [50, 50]
    w.wcs.cdelt = [-0.0017, 0.0017]
    f = fake_frames(1)
    f[0]["wcs"] = w
    cache.save(f, 5, 5, 6, "mock", TEST_DIR)
    got = cache.get(5, 5, 6, "mock", TEST_DIR)[0]["wcs"]
    same = np.allclose(got.wcs.crval, w.wcs.crval) and np.allclose(got.wcs.cdelt, w.wcs.cdelt)
    check("WCS values are the same after loading", same)
    sky = got.pixel_to_world(49, 49)
    check("loaded WCS still converts pixels to sky", abs(sky.ra.deg - 133.8) < 0.01)
except ImportError:
    print("SKIPPED  astropy is not installed here")

shutil.rmtree(TEST_DIR, ignore_errors=True)
print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")