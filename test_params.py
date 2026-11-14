# test_params.py
# Tests params.py. Run it with:  python test_params.py
# No server and no data files are needed.

import config
import params
from params import RequestError

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def fails(**kwargs):
    """True if validate_request raises a ValueError. Prints the message."""
    try:
        params.validate_request(**kwargs)
    except ValueError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


print("--- Test 1: good requests ---")
p = params.validate_request("133.8189", "-7.247", "6", "log", "normal")
check("plain numbers", (p.ra, p.dec, p.fov, p.stretch, p.mode) == (133.8189, -7.247, 6.0, "log", "normal"))
p = params.validate_request("08h55m10.8s", "-07d14m42s")
check("sexagesimal RA and Dec", abs(p.ra - 133.795) < 1e-6 and abs(p.dec + 7.245) < 1e-6)
check("defaults: fov from config, stretch sqrt, mode normal",
      p.fov == config.DEFAULT_FOV_ARCMIN and p.stretch == "sqrt" and p.mode == "normal")
p = params.validate_request(" 10 ", " 20 ", "", "", "")
check("empty fov / stretch / mode mean defaults", p.fov == config.DEFAULT_FOV_ARCMIN and p.stretch == "sqrt")
p = params.validate_request(10, 20, 6, "SQRT", "Normal")
check("numbers instead of text, and capital letters", p.ra == 10.0 and p.stretch == "sqrt" and p.mode == "normal")
check("limits themselves are allowed",
      params.validate_request("0", "-90", str(config.MIN_FOV_ARCMIN)).fov == config.MIN_FOV_ARCMIN
      and params.validate_request("360", "90", str(config.MAX_FOV_ARCMIN)).fov == config.MAX_FOV_ARCMIN)
try:
    p.ra = 1.0
    check("the result cannot be changed by accident", False)
except Exception:
    check("the result cannot be changed by accident", True)

print("\n--- Test 2: bad coordinates ---")
check("RA 400", fails(ra="400", dec="0"))
check("RA -5", fails(ra="-5", dec="0"))
check("Dec 95", fails(ra="10", dec="95"))
check("Dec -95", fails(ra="10", dec="-95"))
check("RA is words", fails(ra="abc", dec="0"))
check("RA missing", fails(ra=None, dec="0"))
check("Dec missing", fails(ra="10", dec=""))
check("RA 25 hours", fails(ra="25h", dec="0"))

print("\n--- Test 3: bad field of view ---")
check("fov below the minimum", fails(ra="10", dec="0", fov="0.5"))
check("fov zero", fails(ra="10", dec="0", fov="0"))
check("fov negative", fails(ra="10", dec="0", fov="-6"))
check("fov above the maximum", fails(ra="10", dec="0", fov="100"))
check("fov is words", fails(ra="10", dec="0", fov="big"))
check("fov is nan", fails(ra="10", dec="0", fov="nan"))
check("fov is inf", fails(ra="10", dec="0", fov="inf"))

print("\n--- Test 4: bad stretch and mode ---")
check("unknown stretch", fails(ra="10", dec="0", stretch="banana"))
check("unknown mode", fails(ra="10", dec="0", mode="banana"))
check("'difference' is accepted", params.validate_request("10", "0", mode="difference").mode == "difference")
check("'stack' is accepted", params.validate_request("10", "0", mode="stack").mode == "stack")

print("\n--- Test 5: error types ---")
try:
    params.validate_request("400", "0")
except ValueError:
    check("bad RA is a ValueError (main.py catches ValueError)", True)
check("RequestError is a ValueError", issubclass(RequestError, ValueError))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")