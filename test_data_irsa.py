# test_data_irsa.py
# Tests the skeleton data_irsa.py (Backend 25). Run it with:  python test_data_irsa.py
# No server, no data files and no internet are needed.

import inspect
from pathlib import Path

import data_irsa
import data_mock

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def not_written(func, *args):
    """True if the call raises NotImplementedError with the friendly text."""
    try:
        func(*args)
    except NotImplementedError as err:
        print(f"        message: {err}")
        return "not written yet" in str(err)
    print("        NO ERROR RAISED")
    return False


print("--- Test 1: same shape as the mock source ---")
check("get_frames has the same parameter names as data_mock.get_frames",
      list(inspect.signature(data_irsa.get_frames).parameters)
      == list(inspect.signature(data_mock.get_frames).parameters))

try:
    data_irsa.get_frames(10, 10, 0)
    check("fov 0 gives ValueError", False)
except ValueError:
    check("fov 0 gives ValueError", True)

print("\n--- Test 2: every function is an empty, documented skeleton ---")
check("get_frames raises NotImplementedError", not_written(data_irsa.get_frames, 10, 10, 6.0))
check("search_images raises NotImplementedError", not_written(data_irsa.search_images, 10, 10, 6.0))
check("download_cutout raises NotImplementedError", not_written(data_irsa.download_cutout, "x"))
check("read_cutout raises NotImplementedError", not_written(data_irsa.read_cutout, None, "x", None))
check("every function has a docstring",
      all(inspect.getdoc(f) for f in (data_irsa.get_frames, data_irsa.search_images,
                                      data_irsa.download_cutout, data_irsa.read_cutout)))

print("\n--- Test 3: FRAME_KEYS matches FRAME_FORMAT.md ---")
text = (Path(__file__).parent / "FRAME_FORMAT.md").read_text(encoding="utf-8")
check("8 keys", len(data_irsa.FRAME_KEYS) == 8)
check("every key is listed in FRAME_FORMAT.md", all(f"- {k}:" in text for k in data_irsa.FRAME_KEYS))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")