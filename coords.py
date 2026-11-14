# coords.py
# Backend 10: turns text typed by a person into RA and Dec in DEGREES.
#
# It understands:
#   133.8189 -7.2470                    plain degrees (space or comma between them)
#   08h55m10.8s -07d14m42s              sexagesimal with unit letters
#   08:55:10.8 -07:14:42                sexagesimal with colons
#   08 55 10.8 -07 14 42                sexagesimal with spaces
#
# Rules (the usual astronomy convention):
#   - A plain number (133.8189) is DEGREES.
#   - Sexagesimal RA without a unit letter (08:55:10.8) is HOURS.
#     Put a "d" after the first number if you mean degrees (133d49m08s).
#   - Declination is always degrees.
#
# Anything it cannot understand raises CoordinateError with a friendly message.
# CoordinateError is a kind of ValueError, so code that catches ValueError
# also catches it.
#
# This file does no downloading and needs no astropy.
# Try it:   python coords.py "08h55m10.8s -07d14m42s"

import math
import re
import sys


class CoordinateError(ValueError):
    """The text could not be understood. The message is safe to show to a user."""


EXAMPLES = "Examples: 133.8189 -7.2470   or   08h55m10.8s -07d14m42s   or   08:55:10.8, -07:14:42"

# One coordinate: optional sign, then 1 to 3 numbers, each may be followed by
# its unit letter (h or d, m, s). Colons are turned into spaces before matching.
_NUMBER = r"\d+(?:\.\d*)?|\.\d+"
_ONE_COORDINATE = re.compile(
    rf"""^
    (?P<sign>[+-])?\s*
    (?P<a>{_NUMBER})\s*(?P<ua>[hd])?\s*
    (?:(?P<b>{_NUMBER})\s*(?P<ub>m)?\s*
       (?:(?P<c>{_NUMBER})\s*(?P<uc>s)?\s*)?
    )?
    $""",
    re.VERBOSE,
)


def _normalize(text):
    """Lower-case, and replace fancy symbols by plain letters."""
    t = text.strip().lower()
    for fancy, plain in (("°", "d"), ("º", "d"), ("′", "m"), ("’", "m"), ("'", "m"),
                         ("″", "s"), ("”", "s"), ('"', "s"),
                         ("−", "-"), ("–", "-"), ("degrees", "d"), ("degree", "d"), ("deg", "d")):
        t = t.replace(fancy, plain)
    t = t.replace(":", " ")
    return re.sub(r"\s+", " ", t).strip()


def _angle_parts(original, what):
    """Read one coordinate text. Returns (sign, total, unit) where total is the
    value as a positive number (hours or degrees) and unit is 'h', 'd' or None
    (None = no unit letter was typed)."""
    m = _ONE_COORDINATE.match(_normalize(original))
    if not m:
        raise CoordinateError(f"I couldn't read '{original.strip()}' as a {what}. {EXAMPLES}")

    sign = -1.0 if m["sign"] == "-" else 1.0
    a, b, c = (float(x) if x is not None else None for x in (m["a"], m["b"], m["c"]))

    # Only the LAST number may have decimals: 08 55.5 is fine, 08.5 55 is not.
    if b is not None and a != int(a):
        raise CoordinateError(f"In '{original.strip()}' only the last number may have decimals.")
    if c is not None and b != int(b):
        raise CoordinateError(f"In '{original.strip()}' only the last number may have decimals.")
    if b is not None and not 0 <= b < 60:
        raise CoordinateError(f"Minutes must be from 0 to 59 (got {b:g} in '{original.strip()}').")
    if c is not None and not 0 <= c < 60:
        raise CoordinateError(f"Seconds must be from 0 to 59.99 (got {c:g} in '{original.strip()}').")

    total = a + (b or 0.0) / 60.0 + (c or 0.0) / 3600.0
    return sign, total, m["ua"], (b is not None)


def parse_ra(text):
    """Right ascension -> degrees (0 to 360).

    Accepts a number (degrees) or text such as '133.8', '8.92h', '08h55m10.8s',
    '08:55:10.8' (hours) or '133d47m43s' (degrees).
    """
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        value = float(text)                       # a plain number means degrees
        if not math.isfinite(value) or not 0 <= value <= 360:
            raise CoordinateError(f"RA must be between 0 and 360 degrees (got {text}).")
        return value
    if not isinstance(text, str) or not text.strip():
        raise CoordinateError(f"Please type a right ascension (RA). {EXAMPLES}")

    sign, total, unit, is_sexagesimal = _angle_parts(text, "right ascension (RA)")
    if sign < 0 and total != 0:
        raise CoordinateError(
            f"RA can't be negative ('{text.strip()}'). Use 0 to 360 degrees, for example 355 instead of -5.")

    in_hours = unit == "h" or (unit is None and is_sexagesimal)
    if in_hours:
        if total >= 24:
            raise CoordinateError(f"RA in hours must be less than 24 (got {total:g}). "
                                  f"If you meant degrees, write it as {total:g}d.")
        return total * 15.0

    if total > 360:
        raise CoordinateError(f"RA must be between 0 and 360 degrees (got {total:g}).")
    return total


def parse_dec(text):
    """Declination -> degrees (-90 to +90).

    Accepts a number or text such as '-7.247', '-07d14m42s', '-07:14:42'.
    """
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        value = float(text)                       # a plain number means degrees
        if not math.isfinite(value) or not -90 <= value <= 90:
            raise CoordinateError(f"Dec must be between -90 and +90 degrees (got {text}).")
        return value
    if not isinstance(text, str) or not text.strip():
        raise CoordinateError(f"Please type a declination (Dec). {EXAMPLES}")

    sign, total, unit, _ = _angle_parts(text, "declination (Dec)")
    if unit == "h":
        raise CoordinateError("Declination is measured in degrees, not hours (use d, not h).")
    if total > 90:
        raise CoordinateError(f"Dec must be between -90 and +90 degrees (got {sign * total:g}).")
    return sign * total


def _split_pair(t):
    """Cut text like '08h55m10.8s -07d14m42s' into its RA part and Dec part."""
    # 1. A comma, semicolon or slash is the clearest separator.
    for sep in (",", ";", "/"):
        if sep in t:
            parts = [p.strip() for p in t.split(sep)]
            if len(parts) != 2 or not all(parts):
                raise CoordinateError(f"I expected exactly two parts (RA and Dec) around the '{sep}'. {EXAMPLES}")
            return parts

    # 2. Otherwise the Dec usually starts with a + or - sign.
    for i, ch in enumerate(t):
        if ch in "+-" and i > 0 and t[:i].strip():
            return [t[:i].strip(), t[i:].strip()]

    # 3. No sign: split the numbers into two equal halves (2, 4 or 6 numbers).
    starts = [m.start() for m in re.finditer(_NUMBER, _normalize(t))]
    n = len(starts)
    if n in (2, 4, 6):
        cut = starts[n // 2]
        norm = _normalize(t)
        return [norm[:cut].strip(), norm[cut:].strip()]
    if n == 0:
        raise CoordinateError(f"I couldn't find any numbers in '{t}'. {EXAMPLES}")
    if n == 1:
        raise CoordinateError(f"I found only one number. Please give both RA and Dec. {EXAMPLES}")
    raise CoordinateError(
        f"I couldn't tell where RA ends and Dec begins. Put a comma between them. {EXAMPLES}")


def parse_coordinates(text):
    """Text with both RA and Dec -> (ra_deg, dec_deg). Raises CoordinateError."""
    if not isinstance(text, str) or not text.strip():
        raise CoordinateError(f"Please type the coordinates. {EXAMPLES}")
    ra_text, dec_text = _split_pair(_normalize(text))
    return parse_ra(ra_text), parse_dec(dec_text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:  python coords.py \"08h55m10.8s -07d14m42s\"")
        print(EXAMPLES)
    else:
        try:
            ra, dec = parse_coordinates(" ".join(sys.argv[1:]))
            print(f"RA  = {ra:.6f} degrees")
            print(f"Dec = {dec:+.6f} degrees")
        except CoordinateError as err:
            print("Problem:", err)