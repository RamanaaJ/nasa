# test_errors.py
# Tests errors.py and the friendly error handling in main.py (Backend 14).
#
# Part 1 needs nothing:                   python test_errors.py
# Part 2 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 2 is skipped.

import requests

import errors

BASE = "http://127.0.0.1:8000"
problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


print("--- Part 1: errors.py (no server) ---")
msg = errors.validation_message([{"type": "missing", "loc": ("query", "ra")}])
check("missing ra -> friendly sentence", "ra" in msg and "dec" in msg and isinstance(msg, str))
msg = errors.validation_message([{"type": "missing", "loc": ("query", "dec")}])
check("missing dec -> same friendly sentence", "ra" in msg and "dec" in msg)
msg = errors.validation_message([{"type": "missing", "loc": ("query", "banana")}])
check("another missing setting names it", "banana" in msg)
msg = errors.validation_message([{"type": "int_parsing", "loc": ("path", "index")}])
check("bad frame number -> friendly sentence", "frame number" in msg)
msg = errors.validation_message([{"type": "whatever", "loc": ("query", "fov")}])
check("other problems name the setting", "fov" in msg)
check("empty error list still gives text", len(errors.validation_message([])) > 0)

check("stock 404 wording is replaced", errors.friendly_http_detail(404, "Not Found") != "Not Found")
check("stock 405 wording is replaced", errors.friendly_http_detail(405, "Method Not Allowed") != "Method Not Allowed")
check("our own message is kept",
      errors.friendly_http_detail(404, "There is no frame 99.") == "There is no frame 99.")
check("a non-text detail does not crash", errors.friendly_http_detail(404, {"a": 1}) == {"a": 1})

text = errors.no_images_message(133.8, -7.2, False)
check("no-images message shows the position", "133.8000" in text and "-7.2000" in text)
check("practice-mode note only appears for mock data",
      "Practice mode" in errors.no_images_message(1, 2, True) and "Practice mode" not in text)
check("server and timeout messages exist",
      len(errors.SERVER_ERROR_MESSAGE) > 20 and len(errors.TIMEOUT_MESSAGE) > 20)

print("\n--- Part 2: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    def friendly(resp, status):
        """True if the answer has this status and 'detail' is a plain sentence."""
        try:
            detail = resp.json().get("detail")
        except ValueError:
            return False
        print("   message:", detail)
        return resp.status_code == status and isinstance(detail, str) and len(detail) > 0

    check("missing ra -> 422 with a sentence",
          friendly(requests.get(f"{BASE}/api/frames", params={"dec": 0}), 422))
    check("missing dec -> 422 with a sentence",
          friendly(requests.get(f"{BASE}/api/frames", params={"ra": 10}), 422))
    check("frame number 'abc' -> 422 with a sentence",
          friendly(requests.get(f"{BASE}/api/frames/abc/image", params={"ra": 10, "dec": 0}), 422))
    check("unknown address -> 404 with a sentence",
          friendly(requests.get(f"{BASE}/api/nothing_here"), 404))
    check("wrong request type -> 405 with a sentence",
          friendly(requests.post(f"{BASE}/api/frames"), 405))
    check("bad value still gives 400 (Backend 11 unchanged)",
          friendly(requests.get(f"{BASE}/api/frames", params={"ra": 400, "dec": 0}), 400))

    far = requests.get(f"{BASE}/api/frames", params={"ra": 10, "dec": 60, "fov": 6})
    check("a position with no images -> 404 that shows the position",
          friendly(far, 404) and "10.0000" in far.json()["detail"])

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")