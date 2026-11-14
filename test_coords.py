# test_coords.py
# Tests coords.py. Run it with:  python test_coords.py
# No server and no data files are needed.

import coords
from coords import CoordinateError

problems = 0


def check(label, ok):
    global problems
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        problems += 1


def close(pair, ra, dec, tol=1e-6):
    return abs(pair[0] - ra) < tol and abs(pair[1] - dec) < tol


def fails(func, *args):
    """True if the call raises CoordinateError. Prints the message."""
    try:
        func(*args)
    except CoordinateError as err:
        print(f"        message: {err}")
        return True
    print("        NO ERROR RAISED")
    return False


# WISE 0855 from the project brief: 08h55m10.831s  -07d14m42.53s
WISE_RA = (8 + 55 / 60 + 10.831 / 3600) * 15      # = 133.79513...
WISE_DEC = -(7 + 14 / 60 + 42.53 / 3600)          # = -7.24514...

print("--- Test 1: plain degrees ---")
check("space", close(coords.parse_coordinates("133.8189 -7.2470"), 133.8189, -7.2470))
check("comma", close(coords.parse_coordinates("133.8189, -7.2470"), 133.8189, -7.2470))
check("comma, no space", close(coords.parse_coordinates("133.8189,-7.2470"), 133.8189, -7.2470))
check("plus sign on Dec", close(coords.parse_coordinates("269.452 +4.6934"), 269.452, 4.6934))
check("integers", close(coords.parse_coordinates("10 20"), 10, 20))
check("extra spaces and tabs", close(coords.parse_coordinates("  133.8189 \t  -7.2470  "), 133.8189, -7.2470))
check("semicolon", close(coords.parse_coordinates("133.8189; -7.2470"), 133.8189, -7.2470))

print("\n--- Test 2: sexagesimal (hours for RA) ---")
check("unit letters", close(coords.parse_coordinates("08h55m10.831s -07d14m42.53s"), WISE_RA, WISE_DEC))
check("colons", close(coords.parse_coordinates("08:55:10.831 -07:14:42.53"), WISE_RA, WISE_DEC))
check("spaces only", close(coords.parse_coordinates("08 55 10.831 -07 14 42.53"), WISE_RA, WISE_DEC))
check("comma and colons", close(coords.parse_coordinates("08:55:10.831, -07:14:42.53"), WISE_RA, WISE_DEC))
check("spaces between the parts", close(coords.parse_coordinates("08h 55m 10.831s   -07d 14m 42.53s"), WISE_RA, WISE_DEC))
check("capital letters", close(coords.parse_coordinates("08H55M10.831S -07D14M42.53S"), WISE_RA, WISE_DEC))
check("fancy symbols (minus, degree, prime marks)",
      close(coords.parse_coordinates("08h55m10.831s −07°14′42.53″"), WISE_RA, WISE_DEC))
check("Barnard's Star", close(coords.parse_coordinates("17h57m48.5s +04d41m36s"), 269.45208, 4.69333, 1e-4))
check("no sign on Dec, six numbers", close(coords.parse_coordinates("08 55 10.8 07 14 42"), 133.795, 7.245, 1e-4))
check("only hours and minutes", close(coords.parse_coordinates("08h55m -07d14m"), (8 + 55 / 60) * 15, -(7 + 14 / 60)))
check("small negative Dec keeps its sign (-00d14m42s)",
      close(coords.parse_coordinates("10h -00d14m42s"), 150, -(14 / 60 + 42 / 3600)))

print("\n--- Test 3: one coordinate at a time ---")
check("RA in decimal hours", abs(coords.parse_ra("8.9h") - 133.5) < 1e-9)
check("RA plain number = degrees", abs(coords.parse_ra("133.5") - 133.5) < 1e-9)
check("RA given as a Python number", abs(coords.parse_ra(133.5) - 133.5) < 1e-9)
check("RA in degrees with d/m/s", abs(coords.parse_ra("133d47m43s") - (133 + 47 / 60 + 43 / 3600)) < 1e-9)
check("RA sexagesimal with spaces = hours", abs(coords.parse_ra("08 55 10.831") - WISE_RA) < 1e-9)
check("RA 360 allowed", coords.parse_ra("360") == 360.0)
check("Dec decimal", abs(coords.parse_dec("-7.247") + 7.247) < 1e-9)
check("Dec given as a Python number", abs(coords.parse_dec(-7.247) + 7.247) < 1e-9)
check("Dec with d/m/s", abs(coords.parse_dec("-07d14m42.53s") - WISE_DEC) < 1e-9)
check("Dec +90 and -90 allowed", coords.parse_dec("90") == 90.0 and coords.parse_dec("-90") == -90.0)

print("\n--- Test 4: nonsense gets a friendly CoordinateError ---")
check("empty text", fails(coords.parse_coordinates, ""))
check("only spaces", fails(coords.parse_coordinates, "   "))
check("words", fails(coords.parse_coordinates, "hello world"))
check("None", fails(coords.parse_coordinates, None))
check("a single number", fails(coords.parse_coordinates, "133.8"))
check("five numbers, no sign or comma", fails(coords.parse_coordinates, "08 55 10.8 07 14"))
check("RA above 360", fails(coords.parse_coordinates, "400 10"))
check("Dec above 90", fails(coords.parse_coordinates, "10 95"))
check("Dec below -90", fails(coords.parse_coordinates, "10 -95"))
check("negative RA", fails(coords.parse_coordinates, "-5 10"))
check("RA hours 24 or more", fails(coords.parse_coordinates, "25h00m00s +10d"))
check("minutes 60 or more", fails(coords.parse_coordinates, "08h75m00s +10d"))
check("seconds 60 or more", fails(coords.parse_coordinates, "08h55m75s +10d"))
check("Dec given in hours", fails(coords.parse_coordinates, "10 7h"))
check("decimals in a middle number", fails(coords.parse_coordinates, "08.5 55 10 -07 14 42"))
check("three parts", fails(coords.parse_coordinates, "1, 2, 3"))
check("scientific notation is not accepted", fails(coords.parse_coordinates, "1e2 5"))
check("not-a-number input", fails(coords.parse_ra, float("nan")))
check("infinite input", fails(coords.parse_dec, float("inf")))
check("True is not a coordinate", fails(coords.parse_ra, True))
check("parse_ra on text with letters", fails(coords.parse_ra, "abc"))
check("CoordinateError is a ValueError", issubclass(CoordinateError, ValueError))

print("\nAll checks passed." if problems == 0 else f"\n{problems} check(s) FAILED.")