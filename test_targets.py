# test_targets.py
# Tests target_list() in targets.py and the /api/targets endpoint in main.py.
#
# Part 1 needs nothing:                   python test_targets.py
# Part 2 needs the server running first:  uvicorn main:app --reload   (other terminal)
# If the server is not running, Part 2 is skipped.

import math

import requests

import targets
from targets import TARGETS, position_at_epoch

BASE = "http://127.0.0.1:8000"
problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


print("--- Part 1: target_list() ---")
items = targets.target_list()
check("5 targets", len(items) == 5)
check("ids match targets.py", [i["id"] for i in items] == list(TARGETS))
needed = {"id", "label", "simbad_name", "ra_deg", "dec_deg", "ra_j2000_deg",
          "dec_j2000_deg", "pmra_mas_yr", "pmdec_mas_yr", "note"}
check("every item has all the fields", all(needed <= set(i) for i in items))
check("no year -> ra/dec are the J2000 values",
      all(i["ra_deg"] == i["ra_j2000_deg"] and i["dec_deg"] == i["dec_j2000_deg"] for i in items))
check("all RA in 0..360 and Dec in -90..90",
      all(0 <= i["ra_deg"] <= 360 and -90 <= i["dec_deg"] <= 90 for i in targets.target_list(2026.0)))

items26 = {i["id"]: i for i in targets.target_list(2026.0)}
ra, dec = position_at_epoch("wise0855", 2026.0)
check("year=2026.0 matches position_at_epoch",
      abs(items26["wise0855"]["ra_deg"] - ra % 360) < 1e-9 and abs(items26["wise0855"]["dec_deg"] - dec) < 1e-9)
check("J2000 values are still there with a year",
      items26["barnard"]["ra_j2000_deg"] == TARGETS["barnard"]["ra_deg"])
moved = items26["barnard"]["dec_deg"] - items26["barnard"]["dec_j2000_deg"]
print(f"   Barnard's Star moved {moved:.4f} deg in Dec between 2000 and 2026")
check("Barnard's Star moved more than 0.07 deg in Dec (about 10 arcsec/yr x 26 yr)", moved > 0.07)

print("\n--- Part 2: /api/targets (needs the server) ---")
try:
    requests.get(BASE + "/docs", timeout=5)
except requests.exceptions.ConnectionError:
    print("SKIPPED  server is not running. Start it with:  uvicorn main:app --reload")
else:
    r = requests.get(f"{BASE}/api/targets")
    check("status 200", r.status_code == 200)
    data = r.json()
    check("epoch is J2000 and count is 5", data.get("epoch") == "J2000" and data.get("count") == 5)
    check("same ids as targets.py", [t["id"] for t in data["targets"]] == list(TARGETS))

    r = requests.get(f"{BASE}/api/targets", params={"year": 2026})
    d26 = r.json()
    check("year=2026 accepted and echoed", r.status_code == 200 and d26.get("epoch") == 2026.0)
    wise = next(t for t in d26["targets"] if t["id"] == "wise0855")
    check("WISE 0855 position is moved to 2026",
          abs(wise["ra_deg"] - wise["ra_j2000_deg"]) > 0.01)

    for label, q in [("year=abc", "abc"), ("year=1000", "1000"), ("year=nan", "nan"), ("year=inf", "inf")]:
        resp = requests.get(f"{BASE}/api/targets", params={"year": q})
        check(f"{label} gives 400 and a message", resp.status_code == 400 and "detail" in resp.json())
        print("   message:", resp.json().get("detail"))
    check("empty year means J2000",
          requests.get(f"{BASE}/api/targets", params={"year": ""}).json().get("epoch") == "J2000")

    # Preset -> frames. The mock images are centred near WISE 0855 (2026 position).
    w = wise
    rf = requests.get(f"{BASE}/api/frames", params={"ra": w["ra_deg"], "dec": w["dec_deg"]})
    check("WISE 0855 preset (year 2026) finds the 12 mock frames",
          rf.status_code == 200 and rf.json().get("frame_count") == 12)
    b = next(t for t in d26["targets"] if t["id"] == "barnard")
    rb = requests.get(f"{BASE}/api/frames", params={"ra": b["ra_deg"], "dec": b["dec_deg"]})
    check("Barnard's Star preset gives 404 on mock data (the mock sky only covers WISE 0855)",
          rb.status_code == 404)

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")