# test_update_design.py
# Tests the easy-update design (Backend 27): config label + live query builder.
# Run it with:  python test_update_design.py
# No server, no data files and no internet are needed.

import cache
import config
import data_irsa

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def refused(func, *args, **kwargs):
    """True if the call raises a ValueError. Prints the message."""
    try:
        func(*args, **kwargs)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


print("--- Test 1: the config ---")
check("RELEASE_NAME is a non-empty text", isinstance(config.RELEASE_NAME, str) and config.RELEASE_NAME != "")
check("it is no longer the superseded QR2 placeholder", "qr2" not in config.RELEASE_NAME.lower())
check("SIA collections are a tuple of names", all(isinstance(c, str) for c in config.SPHEREX_SIA_COLLECTIONS))

print("\n--- Test 2: changing the release is a one-line change ---")
saved_name, saved_mock = config.RELEASE_NAME, config.USE_MOCK
config.USE_MOCK = False
config.RELEASE_NAME = "release_one"
key_one = cache.make_key(133.8, -7.2, 6.0)
config.RELEASE_NAME = "release_two"
key_two = cache.make_key(133.8, -7.2, 6.0)
config.RELEASE_NAME, config.USE_MOCK = saved_name, saved_mock
check("a new release name gives a different cache key (fresh cache)", key_one != key_two)
check("mock data keeps its own key", cache.current_release() == "mock" if config.USE_MOCK else True)

print("\n--- Test 3: the live query text ---")
q = data_irsa.build_search_query(133.8, -7.2, 6.0)
check("it joins spherex.artifact and spherex.plane", "spherex.artifact" in q and "spherex.plane" in q)
check("it asks for images that contain the position",
      "CONTAINS(POINT('ICRS', 133.8, -7.2), p.poly)" in q)
check("a 6 arcmin FOV becomes size=0.1 (degrees)", "size=0.1" in q)
check("a 30 arcmin FOV becomes size=0.5", "size=0.5" in data_irsa.build_search_query(1, 2, 30.0))
check("the centre is in the link", "center=133.8,-7.2d" in q)
check("oldest first", "ORDER BY p.time_bounds_lower" in q)
check("no bandpass filter by default", "energy_bandpassname =" not in q)
check("a bandpass filter can be added",
      "AND p.energy_bandpassname = 'SPHEREx-D2'" in data_irsa.build_search_query(1, 2, 6, "SPHEREx-D2"))
check("the query does not contain the release label (it is live)", config.RELEASE_NAME not in q)

print("\n--- Test 4: bad input is refused (nothing odd reaches the query) ---")
check("bandpass with a quote and SQL", refused(data_irsa.build_search_query, 1, 2, 6, "x' OR 1=1 --"))
check("bandpass SPHEREx-D7", refused(data_irsa.build_search_query, 1, 2, 6, "SPHEREx-D7"))
check("RA 400", refused(data_irsa.build_search_query, 400, 2, 6))
check("Dec 95", refused(data_irsa.build_search_query, 1, 95, 6))
check("NaN RA", refused(data_irsa.build_search_query, float("nan"), 2, 6))
check("text instead of a number", refused(data_irsa.build_search_query, "1; DROP", 2, 6))
check("FOV 0", refused(data_irsa.build_search_query, 1, 2, 0))
check("FOV negative", refused(data_irsa.build_search_query, 1, 2, -6))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")