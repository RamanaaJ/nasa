# processing.py
# Part B: turns a frame into a picture.
#   1. cutout_frame()    cut a small patch around an RA/Dec using the WCS
#   2. stretch_image()   turn raw pixel values into 0-255 grey levels
#   3. image_to_png_bytes()  turn grey levels into PNG file bytes
#   4. frame_to_png()    does all three in one call
# This file never downloads data and never reads files.
# A "frame" is a dictionary described in FRAME_FORMAT.md.

import io

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import Cutout2D, NoOverlapError
from PIL import Image

STRETCH_MODES = ("linear", "sqrt", "log")


def cutout_frame(frame, ra_deg, dec_deg, fov_arcmin):
    """Return a NEW frame containing only a square patch of sky.

    The patch is centred on (ra_deg, dec_deg) and is fov_arcmin wide.
    Parts of the patch that fall outside the image are filled with NaN
    (image, variance) or 0 (flags).
    Raises ValueError if the position is completely outside the image.
    """
    if fov_arcmin <= 0:
        raise ValueError("Field of view must be greater than zero.")

    position = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame="icrs")
    size = fov_arcmin * u.arcmin
    wcs = frame["wcs"]

    def cut(array, fill):
        # Cutout2D does the pixel maths for us, using the WCS.
        return Cutout2D(array, position, size, wcs=wcs,
                        mode="partial", fill_value=fill)

    try:
        cut_image = cut(frame["image"], np.nan)
    except NoOverlapError:
        raise ValueError("This sky position is outside the image.")

    new_frame = dict(frame)                  # copy, so the original is untouched
    new_frame["image"] = cut_image.data.copy()
    new_frame["wcs"] = cut_image.wcs         # the WCS of the smaller patch

    # Flags and variance sit on the same pixel grid, so cut them the same way.
    if frame.get("flags") is not None:
        new_frame["flags"] = cut(frame["flags"], 0).data.copy()
    if frame.get("variance") is not None:
        new_frame["variance"] = cut(frame["variance"], np.nan).data.copy()

    return new_frame


def stretch_image(image, mode="sqrt", low_pct=1.0, high_pct=99.5):
    """Turn raw pixel values into a uint8 array (0 = black, 255 = white).

    low_pct / high_pct: pixels below / above these percentiles become
    black / white. NaN pixels become black.
    """
    if mode not in STRETCH_MODES:
        raise ValueError(f"Unknown stretch '{mode}'. Use one of {STRETCH_MODES}.")

    finite = np.isfinite(image)
    if not finite.any():                      # nothing usable: all black
        return np.zeros(image.shape, dtype=np.uint8)

    vmin, vmax = np.percentile(image[finite], [low_pct, high_pct])
    if vmax <= vmin:                          # flat image: all black
        return np.zeros(image.shape, dtype=np.uint8)

    # Scale to the range 0 to 1, clipping anything outside it
    scaled = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
    scaled = np.where(finite, scaled, 0.0)    # NaN -> black

    if mode == "sqrt":
        scaled = np.sqrt(scaled)
    elif mode == "log":
        scaled = np.log10(1.0 + 1000.0 * scaled) / np.log10(1001.0)

    return np.round(scaled * 255).astype(np.uint8)


def image_to_png_bytes(grey, target_size=400):
    """Turn a uint8 grey array into PNG bytes (the contents of a .png file).

    - Flipped vertically so north is up (FITS stores the bottom row first).
    - Enlarged by a whole-number factor to about target_size pixels, using
      'nearest' scaling so each data pixel stays a sharp square.
    """
    height, width = grey.shape
    picture = Image.fromarray(np.ascontiguousarray(np.flipud(grey)))

    factor = max(1, target_size // max(height, width))
    if factor > 1:
        picture = picture.resize((width * factor, height * factor),
                                 Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    picture.save(buffer, format="PNG")
    return buffer.getvalue()


def frame_to_png(frame, ra_deg, dec_deg, fov_arcmin, stretch="sqrt"):
    """Cut, stretch and convert in one go. Returns PNG bytes."""
    patch = cutout_frame(frame, ra_deg, dec_deg, fov_arcmin)
    grey = stretch_image(patch["image"], mode=stretch)
    return image_to_png_bytes(grey)