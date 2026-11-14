# names.py
# Backend 12: turns a NAME typed by a person into RA and Dec in DEGREES.
#
# Order of work:
#   1. Check our 5 local targets (targets.py). This works offline.
#   2. If the name is not one of them, ask astropy's online name lookup
#      (SkyCoord.from_name). That service is run by CDS, which has been
#      down recently (see PROGRESS.md), so it can fail.
#   3. If both fail, raise NameSearchError with a friendly message.
#
# NameSearchError is a kind of ValueError, like CoordinateError, so code
# that catches ValueError also catches it.
#
# This file does not touch the web server, the cache or the frames.
# It only answers: "what are the coordinates of this name?"
#
# Try it:   python names.py "Barnard's Star"
#           python names.py "wise 0855"
#           python names.py "Vega"          (needs internet and CDS)

import math
import re
import sys
from dataclasses import dataclass

from targets import TARGETS, position_at_epoch


class NameSearchError(ValueError):
    """The name could not be resolved. The message is safe to show to a user."""


# Extra spellings for each local target (the key is the id used in targets.py).
# The label from targets.py is added automatically.
# Spaces, capitals, hyphens and apostrophes do not matter when matching,
# so "Barnard's Star", "barnards star" and "BARNARDS-STAR" are all the same.
EXTRA_NAMES = {
    "wise0855": ["WISE 0855", "WISE 0855-0714", "WISE J085510.83-071442.5",
                 "WISEA J085510.74-071442.5"],
    "barnard": ["Barnard's star", "Barnards star", "Barnard star", "GJ 699"],
    "epsindib": ["eps Ind B", "eps Indi B", "epsilon Ind B", "eps Ind Ba"],
    "rwaur": ["RW Aur", "RW Aurigae", "V* RW Aur"],
    "rdra": ["R Dra", "R Draconis", "V* R Dra"],
}


def _normalize(text):
    """Make a name easy to compare: lower case, only letters and digits.

    "Barnard's Star" -> "barnardsstar"      "WISE 0855-0714" -> "wise08550714"
    """
    t = str(text).lower()
    return re.sub(r"[^a-z0-9]", "", t)


def _build_local_table():
    """Make a dictionary: normalized name -> target id."""
    table = {}
    for tid, target in TARGETS.items():
        for name in [target["label"], *EXTRA_NAMES.get(tid, [])]:
            key = _normalize(name)
            # Two different targets must never share a spelling
            if key in table and table[key] != tid:
                raise RuntimeError(f"Name '{name}' belongs to two targets.")
            table[key] = tid
    return table


_LOCAL_TABLE = _build_local_table()


@dataclass(frozen=True)
class NameResult:
    """The answer of a name search."""
    ra: float            # degrees, 0 to 360
    dec: float           # degrees, -90 to +90
    label: str           # name to show a person
    source: str          # "local" (our 5 targets) or "online"
    target_id: str | None   # id in targets.py for local results, else None


def _online_lookup(name):
    """Ask astropy's name resolver. Returns (ra_deg, dec_deg).

    Raises an exception if the service is down or the name is unknown.
    (astropy is imported here so this file works without it for local names.)
    """
    from astropy.coordinates import SkyCoord
    sky = SkyCoord.from_name(name)
    icrs = sky.icrs
    return float(icrs.ra.deg), float(icrs.dec.deg)


def resolve_local(text, year=None):
    """Look in our 5 targets only. Returns a NameResult, or None if not found.

    year: if given (e.g. 2026.0), the position is moved to that year using
          the target's proper motion (position_at_epoch). If None, the
          J2000 position is returned.
    """
    tid = _LOCAL_TABLE.get(_normalize(text))
    if tid is None:
        return None
    target = TARGETS[tid]
    if year is None:
        ra, dec = target["ra_deg"], target["dec_deg"]
    else:
        ra, dec = position_at_epoch(tid, year)
    return NameResult(ra=ra % 360.0, dec=dec, label=target["label"],
                      source="local", target_id=tid)


def resolve_name(text, year=None, allow_online=True, online_lookup=None):
    """Name text -> NameResult. Raises NameSearchError.

    year:          only used for local targets (see resolve_local).
                   Online results are always the position the service gives.
    allow_online:  False = local targets only.
    online_lookup: a function name -> (ra_deg, dec_deg). Used by tests to
                   pretend to be the online service. Normally leave it None.
    """
    if not isinstance(text, str) or not text.strip():
        raise NameSearchError("Please type a name, for example: Barnard's Star")
    name = text.strip()

    if year is not None:
        if isinstance(year, bool) or not isinstance(year, (int, float)) or not math.isfinite(year):
            raise NameSearchError("The year must be a number, for example 2026.0.")

    local = resolve_local(name, year)
    if local is not None:
        return local

    if not allow_online:
        raise NameSearchError(
            f"'{name}' is not one of the built-in targets "
            f"({', '.join(t['label'] for t in TARGETS.values())}). "
            f"Type the coordinates instead.")

    lookup = online_lookup or _online_lookup
    try:
        ra, dec = lookup(name)
    except Exception as err:
        # We cannot tell "unknown name" from "service down" for sure,
        # so the message covers both.
        raise NameSearchError(
            f"I couldn't find '{name}'. Check the spelling, or type the "
            f"coordinates instead. (The online name lookup is run by CDS, "
            f"which may be down right now. Error type: {type(err).__name__}.) "
            f"The built-in targets always work: "
            f"{', '.join(t['label'] for t in TARGETS.values())}.") from err

    # Never trust the outside world: check the numbers
    if not (math.isfinite(ra) and math.isfinite(dec)
            and 0 <= ra <= 360 and -90 <= dec <= 90):
        raise NameSearchError(
            f"The name lookup gave unusable coordinates for '{name}'. "
            f"Type the coordinates instead.")
    return NameResult(ra=float(ra), dec=float(dec), label=name,
                      source="online", target_id=None)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage:  python names.py "Barnard\'s Star"')
    else:
        try:
            r = resolve_name(" ".join(sys.argv[1:]))
            print(f"{r.label}  ({r.source})")
            print(f"RA  = {r.ra:.6f} degrees")
            print(f"Dec = {r.dec:+.6f} degrees")
        except NameSearchError as err:
            print("Problem:", err)