# params.py
# Backend 11: checks the settings that arrive in a web address (URL), such as
#   /api/frames?ra=133.8&dec=-7.2&fov=6&mode=normal&stretch=sqrt
# One function, validate_request(), turns the raw text into clean numbers or
# raises RequestError with a friendly message.
#
# It needs no web server and no astropy, so it is easy to test.
# (It imports processing.py only to learn which stretch names exist.)

from dataclasses import dataclass
import math

import config
import coords
import processing

# Modes are the ways the frames can be combined. Only "normal" is built so far.
# "difference" is Backend 18 and "stack" is Backend 19 in TODO_LIST.md.
ALL_MODES = ("normal", "difference", "stack")
READY_MODES = ("normal",)          # add a name here when its feature is built
DEFAULT_MODE = "normal"
DEFAULT_STRETCH = "sqrt"


class RequestError(ValueError):
    """Something in the web address is wrong. The message is safe to show to a user."""


@dataclass(frozen=True)
class Params:
    """The cleaned-up settings of one request."""
    ra: float          # degrees, 0 to 360
    dec: float         # degrees, -90 to +90
    fov: float         # arcminutes, between the limits in config.py
    stretch: str       # one of processing.STRETCH_MODES
    mode: str          # one of READY_MODES


def _blank(value):
    """True for None or an empty / spaces-only string (means 'not given')."""
    return value is None or (isinstance(value, str) and not value.strip())


def parse_fov(value):
    """Field of view in arcminutes. Empty means the default from config.py."""
    if _blank(value):
        return float(config.DEFAULT_FOV_ARCMIN)
    try:
        fov = float(str(value).strip())
    except ValueError:
        raise RequestError(f"The field of view '{value}' is not a number. "
                           f"Use arcminutes, for example fov=6.")
    if not math.isfinite(fov):
        raise RequestError(f"The field of view '{value}' is not a usable number.")
    if not config.MIN_FOV_ARCMIN <= fov <= config.MAX_FOV_ARCMIN:
        raise RequestError(
            f"The field of view must be between {config.MIN_FOV_ARCMIN:g} and "
            f"{config.MAX_FOV_ARCMIN:g} arcminutes (you asked for {fov:g}).")
    return fov


def parse_stretch(value):
    if _blank(value):
        return DEFAULT_STRETCH
    stretch = str(value).strip().lower()
    if stretch not in processing.STRETCH_MODES:
        raise RequestError(f"Unknown stretch '{str(value).strip()}'. "
                           f"Choose one of: {', '.join(processing.STRETCH_MODES)}.")
    return stretch


def parse_mode(value):
    if _blank(value):
        return DEFAULT_MODE
    mode = str(value).strip().lower()
    if mode not in ALL_MODES:
        raise RequestError(f"Unknown mode '{str(value).strip()}'. Choose one of: {', '.join(ALL_MODES)}.")
    if mode not in READY_MODES:
        raise RequestError(f"The '{mode}' mode is not available yet. Available now: {', '.join(READY_MODES)}.")
    return mode


def validate_request(ra, dec, fov=None, stretch=None, mode=None):
    """Check all settings and return a Params. Raises RequestError (or
    coords.CoordinateError for a bad RA/Dec). Both are ValueErrors."""
    if _blank(ra) or _blank(dec):
        raise RequestError("Please give both ra and dec, for example ra=133.8&dec=-7.2.")
    return Params(
        ra=coords.parse_ra(ra),
        dec=coords.parse_dec(dec),
        fov=parse_fov(fov),
        stretch=parse_stretch(stretch),
        mode=parse_mode(mode),
    )