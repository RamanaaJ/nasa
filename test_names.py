# test_names.py
# Tests names.py. Run it with:  python test_names.py
# No server, no data files and no internet are needed: the online service
# is replaced by small fake functions.

import names
from names import NameSearchError
from targets import TARGETS, position_at_epoch

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fails(*args, **kwargs):
    """True if resolve_name raises NameSearchError. Prints the message."""
    try:
        names.resolve_name(*args, **kwargs)
    except NameSearchError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


def must_not_be_called(name):
    raise AssertionError("the online lookup should not have been used")


print("--- Test 1: all 5 local targets, several spellings ---")
spellings = {
    "wise0855": ["WISE 0855", "wise0855", "wise 0855-0714", "WISE J085510.83-071442.5"],
    "barnard": ["Barnard's Star", "barnards star", "BARNARD STAR", "GJ 699", "Barnard’s Star"],
    "epsindib": ["Epsilon Indi B", "eps Ind B", "epsilon indi b"],
    "rwaur": ["RW Aurigae", "rw aur", "RW  Aur"],
    "rdra": ["R Draconis", "r dra"],
}
for tid, texts in spellings.items():
    for text in texts:
        r = names.resolve_name(text, online_lookup=must_not_be_called)
        check(f"'{text}' -> {tid}", r.target_id == tid and r.source == "local")

print("\n--- Test 2: the numbers ---")
r = names.resolve_name("Barnard's Star", online_lookup=must_not_be_called)
check("J2000 position comes straight from targets.py",
      r.ra == TARGETS["barnard"]["ra_deg"] and r.dec == TARGETS["barnard"]["dec_deg"])
r = names.resolve_name("WISE 0855", year=2026.0, online_lookup=must_not_be_called)
ra26, dec26 = position_at_epoch("wise0855", 2026.0)
check("year=2026.0 gives the proper-motion position", abs(r.ra - ra26) < 1e-9 and abs(r.dec - dec26) < 1e-9)
check("2026 position differs from J2000 (WISE 0855 moves a lot)",
      abs(r.ra - TARGETS["wise0855"]["ra_deg"]) > 0.01)
check("label comes from targets.py", names.resolve_name("r dra").label == "R Draconis")
check("every target label finds itself",
      all(names.resolve_name(t["label"], online_lookup=must_not_be_called).target_id == tid
          for tid, t in TARGETS.items()))

print("\n--- Test 3: online lookup (faked) ---")
calls = []


def fake_lookup(name):
    calls.append(name)
    return 279.2347, 38.7837


r = names.resolve_name("  Some Other Star  ", online_lookup=fake_lookup)
check("unknown name goes to the online lookup", calls == ["Some Other Star"])
check("online result has the right numbers and source",
      r.source == "online" and r.target_id is None and abs(r.ra - 279.2347) < 1e-9)
check("online result keeps the typed name as label", r.label == "Some Other Star")

print("\n--- Test 4: failures are friendly ---")


def broken_lookup(name):
    raise ConnectionError("pretend CDS is down")


check("online service down -> NameSearchError", fails("Some Other Star", online_lookup=broken_lookup))
check("allow_online=False -> NameSearchError", fails("Some Other Star", allow_online=False, online_lookup=must_not_be_called))
check("empty text", fails(""))
check("only spaces", fails("   "))
check("None", fails(None))
check("a number is not a name", fails(123))
check("bad year", fails("WISE 0855", year="soon"))
check("lookup gives NaN", fails("x", online_lookup=lambda n: (float("nan"), 0.0)))
check("lookup gives RA 400", fails("x", online_lookup=lambda n: (400.0, 0.0)))
check("lookup gives Dec 95", fails("x", online_lookup=lambda n: (10.0, 95.0)))
check("NameSearchError is a ValueError", issubclass(NameSearchError, ValueError))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")