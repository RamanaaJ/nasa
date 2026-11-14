# test_practice_check.py
# Tests practice_check.py and /api/practice/check (Backend 24).
#
# Parts 1-2 need nothing:                 python test_practice_check.py
# Part 3 needs the practice files:        python data_practice.py   (once)
# Part 4 needs the server running first:  uvicorn main:app --reload   (other terminal)
# Parts 3 and 4 are skipped if their requirements are missing.

import json

import requests

import practice_check

BASE = "http://127.0.0.1:8000"
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


print("--- Part 1: separation_arcsec ---")
sep = practice_check.separation_arcsec
check("same place = 0", sep(10, 20, 10, 20) == 0)
check("1 arcsec in Dec = 1", abs(sep(10, 20, 10, 20 + 1 / 3600) - 1.0) < 1e-6)
check("RA difference shrinks with cos(Dec): 20 arcsec of RA at Dec 60 = 10 arcsec",
      abs(sep(10 + 20 / 3600, 60, 10, 60) - 10.0) < 0.01)
check("RA wrap: 359.9999 and 0.0001 are 0.72 arcsec apart", abs(sep(359.9999, 0, 0.0001, 0) - 0.72) < 0.01)

print("\n--- Part 2: check_click with fake answers ---")
fake = {"n_frames": 2, "movers": [
    {"id": "X", "label": "near", "positions": [
        {"frame": 0, "ra_deg": 10.0, "dec_deg": 60.0}, {"frame": 1, "ra_deg": 10.01, "dec_deg": 60.0}]},
    {"id": "Y", "label": "wrap", "positions": [
        {"frame": 0, "ra_deg": 359.9999, "dec_deg": 0.0}, {"frame": 1, "ra_deg": 0.01, "dec_deg": 0.0}]},
]}
r = practice_check.check_click(10.0, 60.0, 0, fake)
check("a click exactly on mover X in frame 0 is a hit", r["hit"] and r["mover_id"] == "X" and r["label"] == "near")
check("the answer says how many movers exist and the radius",
      r["movers_total"] == 2 and r["radius_arcsec"] == practice_check.HIT_RADIUS_ARCSEC and r["frame"] == 0)
check("10 arcsec away on the sky (20 arcsec of RA at Dec 60) is still a hit",
      practice_check.check_click(10.0 + 20 / 3600, 60.0, 0, fake)["hit"])
check("30 arcsec away is a miss", not practice_check.check_click(10.0, 60.0 + 30 / 3600, 0, fake)["hit"])
miss = practice_check.check_click(50.0, -20.0, 0, fake)
check("a miss gives hit=False and no mover", miss["hit"] is False and miss["mover_id"] is None and miss["label"] is None)
check("the old position is a miss in frame 1 (movers move)", not practice_check.check_click(10.0, 60.0, 1, fake)["hit"])
check("the new position is a hit in frame 1", practice_check.check_click(10.01, 60.0, 1, fake)["mover_id"] == "X")
check("RA wrap: a click at RA 0.0001 hits the mover at 359.9999",
      practice_check.check_click(0.0001, 0.0, 0, fake)["mover_id"] == "Y")
close = {"n_frames": 1, "movers": [
    {"id": "P", "label": "p", "positions": [{"frame": 0, "ra_deg": 10.0, "dec_deg": 0.0}]},
    {"id": "Q", "label": "q", "positions": [{"frame": 0, "ra_deg": 10.0, "dec_deg": 8 / 3600}]}]}
check("two movers in range: the nearer one wins",
      practice_check.check_click(10.0, 6 / 3600, 0, close)["mover_id"] == "Q")
check("frame -1 is refused", fails(practice_check.check_click, 10.0, 60.0, -1, fake))
check("frame 2 (does not exist) is refused", fails(practice_check.check_click, 10.0, 60.0, 2, fake))
check("a text frame number is refused", fails(practice_check.check_click, 10.0, 60.0, "0", fake))
check("a custom radius is used", not practice_check.check_click(10.0, 60.0 + 5 / 3600, 0, fake, radius_arcsec=2.0)["hit"])

print("\n--- Part 3: the real practice answers ---")
if not practice_check.ANSWERS_FILE.exists():
    print("SKIPPED  no practice files. Run:  python data_practice.py")
    answers = None
else:
    answers = json.loads(practice_check.ANSWERS_FILE.read_text(encoding="utf-8"))
    ok = True
    for m in answers["movers"]:
        for p in m["positions"]:
            res = practice_check.check_click(p["ra_deg"], p["dec_deg"], p["frame"])
            if not (res["hit"] and res["mover_id"] == m["id"]):
                ok = False
                print(f"   mover {m['id']} frame {p['frame']}: {res}")
    check("every mover in every frame is a hit on its own position (48 clicks)", ok)
    a = answers["movers"][0]["positions"]
    check("the slow mover A is far enough away in frame 11 that its frame 0 spot is a miss",
          not practice_check.check_click(a[0]["ra_deg"], a[0]["dec_deg"], 11)["hit"])
    d = answers["movers"][3]["positions"]
    check("the very fast mover D: its frame 0 spot is a miss in frame 1",
          not practice_check.check_click(d[0]["ra_deg"], d[0]["dec_deg"], 1)["hit"])
    check("the sky centre of the practice set (nothing hidden there in frame 0) is a miss",
          not practice_check.check_click(answers["center_ra_deg"], answers["center_dec_deg"], 0)["hit"])

print("\n--- Part 4: the live server ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    if answers is None:
        print("SKIPPED  no practice files.")
    else:
        url = BASE + "/api/practice/check"
        b5 = answers["movers"][1]["positions"][5]
        r = requests.get(url, params={"ra": b5["ra_deg"], "dec": b5["dec_deg"], "frame": 5})
        check("clicking mover B in frame 5 gives 200 and a hit", r.status_code == 200 and r.json()["hit"] is True
              and r.json()["mover_id"] == "B")
        print("   answer:", r.json())
        check("the answer contains only the expected keys (no secret positions)",
              set(r.json()) == {"hit", "mover_id", "label", "frame", "radius_arcsec", "movers_total"})
        r = requests.get(url, params={"ra": b5["ra_deg"] + 0.05, "dec": b5["dec_deg"], "frame": 5})
        check("a click far away is a miss", r.status_code == 200 and r.json()["hit"] is False)
        r = requests.get(url, params={"ra": f"{b5['ra_deg']}", "dec": f"{b5['dec_deg']}", "frame": 11})
        check("mover B's frame 5 spot is a miss in frame 11", r.json()["hit"] is False)

        bad = requests.get(url, params={"ra": b5["ra_deg"], "dec": b5["dec_deg"], "frame": 99})
        check("frame 99 gives 404 and a message", bad.status_code == 404 and "detail" in bad.json())
        print("   message:", bad.json().get("detail"))
        bad = requests.get(url, params={"ra": "abc", "dec": 0, "frame": 0})
        check("ra=abc gives 400 and a message", bad.status_code == 400 and "detail" in bad.json())
        bad = requests.get(url, params={"ra": 10, "dec": 95, "frame": 0})
        check("dec=95 gives 400", bad.status_code == 400)
        bad = requests.get(url, params={"ra": 10, "dec": 0})
        check("missing frame gives 422 with a sentence", bad.status_code == 422 and isinstance(bad.json().get("detail"), str))
        bad = requests.get(url, params={"ra": 10, "dec": 0, "frame": "x"})
        check("frame=x gives 422 with a sentence", bad.status_code == 422 and isinstance(bad.json().get("detail"), str))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")