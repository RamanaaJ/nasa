# processing.py
# Part B: turns a frame into a picture.
#   1. cutout_frame()    cut a small patch around an RA/Dec using the WCS
#   2. stretch_image()   turn raw pixel values into 0-255 grey levels
#   3. image_to_png_bytes()  turn grey levels into PNG file bytes
#   4. frame_to_png()    does all three in one call
#   5. match_backgrounds() / shared_limits()   (Backend 17) same background and
#      same brightness scale in every frame
#   6. difference_frames() / stretch_difference()   (Backend 18)
#   7. stack_frames()    (Backend 19) add or average frames to cut noise
# This file never downloads data and never reads files.
# A "frame" is a dictionary described in FRAME_FORMAT.md.

import io
from datetime import timedelta

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.nddata import Cutout2D, NoOverlapError
from PIL import Image

STRETCH_MODES = ("linear", "sqrt", "log", "asinh")

# Strength of the asinh stretch. Bigger = faint things get brighter.
# 10 is a starting guess; retune on real data (TODO after-data #15).
ASINH_SCALE = 10.0


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


def stretch_image(image, mode="sqrt", low_pct=1.0, high_pct=99.5, limits=None):
    """Turn raw pixel values into a uint8 array (0 = black, 255 = white).

    low_pct / high_pct: pixels below / above these percentiles become
    black / white. NaN pixels become black.
    limits: None = work out the black and white points from this image alone.
            A pair (vmin, vmax) = use these instead, so several frames can
            share one brightness scale (see shared_limits).
    """
    if mode not in STRETCH_MODES:
        raise ValueError(f"Unknown stretch '{mode}'. Use one of {STRETCH_MODES}.")

    finite = np.isfinite(image)
    if not finite.any():                      # nothing usable: all black
        return np.zeros(image.shape, dtype=np.uint8)

    if limits is None:
        vmin, vmax = np.percentile(image[finite], [low_pct, high_pct])
    else:
        vmin, vmax = limits
    if vmax <= vmin:                          # flat image: all black
        return np.zeros(image.shape, dtype=np.uint8)

    # Scale to the range 0 to 1, clipping anything outside it
    scaled = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
    scaled = np.where(finite, scaled, 0.0)    # NaN -> black

    if mode == "sqrt":
        scaled = np.sqrt(scaled)
    elif mode == "log":
        scaled = np.log10(1.0 + 1000.0 * scaled) / np.log10(1001.0)
    elif mode == "asinh":
        # Divide by asinh(ASINH_SCALE) so 0 stays 0 and 1 stays 1
        scaled = np.arcsinh(ASINH_SCALE * scaled) / np.arcsinh(ASINH_SCALE)

    return np.round(scaled * 255).astype(np.uint8)


def estimate_background(image):
    """The background level of one image: the median of its finite pixels.

    The median is hardly moved by a few bright stars or one small moving dot.
    Returns None if the image has no usable pixels.
    (Flags are not used yet. Real flag meanings come after the data arrives.)
    """
    values = image[np.isfinite(image)]
    if values.size == 0:
        return None
    return float(np.median(values))


def match_backgrounds(frames):
    """Return NEW frames whose backgrounds all sit at the same level.

    Each image is shifted up or down (a plain subtraction) so its background
    equals the median of all the frames' backgrounds. Stars keep their
    contrast, NaN pixels stay NaN, and the original frames are not changed.
    Frames with no usable pixels are returned unchanged.
    Only an offset is removed. Differences in scale (brightness ratio)
    between frames are NOT corrected.
    """
    levels = [estimate_background(f["image"]) for f in frames]
    usable = [lv for lv in levels if lv is not None]
    if not usable:
        return list(frames)
    target = float(np.median(usable))

    matched = []
    for frame, level in zip(frames, levels):
        new_frame = dict(frame)               # copy, so the original is untouched
        if level is not None:
            new_frame["image"] = frame["image"] - (level - target)
        matched.append(new_frame)
    return matched


def shared_limits(frames, low_pct=1.0, high_pct=99.5):
    """Black and white points worked out from ALL frames together.

    Returns (vmin, vmax) for stretch_image(limits=...), or None if there are
    no usable pixels. Using one pair for every frame means the same pixel
    value gets the same grey in every frame.
    """
    parts = [f["image"][np.isfinite(f["image"])] for f in frames]
    parts = [p for p in parts if p.size > 0]
    if not parts:
        return None
    vmin, vmax = np.percentile(np.concatenate(parts), [low_pct, high_pct])
    return float(vmin), float(vmax)


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


# ---------- Backend 18: difference imaging ----------

# Ways to pick the frame that is subtracted
DIFFERENCE_REFERENCES = ("first", "previous")


def difference_frames(frames, reference="first"):
    """Return NEW frames where each image has a reference image subtracted.

    reference="first":    every frame minus frame 0
    reference="previous": every frame minus the frame before it
    Frame 0 has nothing earlier, so it is subtracted from itself (all zeros).
    NaN stays NaN. Variances add (noise from both images). Flags are combined.
    All frames must have the same pixel size (true for mock data).
    The original frames are not changed.
    """
    if reference not in DIFFERENCE_REFERENCES:
        raise ValueError(f"Unknown reference '{reference}'. Use one of {DIFFERENCE_REFERENCES}.")
    if not frames:
        return []
    shape = frames[0]["image"].shape
    if any(f["image"].shape != shape for f in frames):
        raise ValueError("The frames have different sizes, so they cannot be subtracted.")

    result = []
    for i, frame in enumerate(frames):
        ref = frames[0] if reference == "first" else frames[max(i - 1, 0)]
        new_frame = dict(frame)               # copy, so the original is untouched
        new_frame["image"] = frame["image"] - ref["image"]
        if frame.get("variance") is not None and ref.get("variance") is not None:
            new_frame["variance"] = frame["variance"] + ref["variance"]
        if frame.get("flags") is not None and ref.get("flags") is not None:
            new_frame["flags"] = np.bitwise_or(frame["flags"], ref["flags"])
        result.append(new_frame)
    return result


def shared_difference_limit(frames, high_pct=99.5):
    """One brightness limit for ALL difference frames (so they share a scale).

    Returns a number (the 99.5th percentile of |difference|), or None if every
    frame is empty or all zeros. All-zero frames (the reference frame) are
    skipped so they do not pull the limit down.
    """
    parts = []
    for f in frames:
        values = np.abs(f["image"][np.isfinite(f["image"])])
        if values.size > 0 and values.max() > 0:
            parts.append(values)
    if not parts:
        return None
    limit = float(np.percentile(np.concatenate(parts), high_pct))
    return limit if limit > 0 else None


def _curve(a, mode):
    """Apply a stretch curve to numbers between 0 and 1 (same curves as stretch_image)."""
    if mode == "sqrt":
        return np.sqrt(a)
    if mode == "log":
        return np.log10(1.0 + 1000.0 * a) / np.log10(1001.0)
    if mode == "asinh":
        return np.arcsinh(ASINH_SCALE * a) / np.arcsinh(ASINH_SCALE)
    return a                                   # linear


def stretch_difference(image, mode="sqrt", limit=None):
    """Turn a difference image into uint8 grey levels.

    0 -> mid grey (about 128), +limit -> white, -limit -> black. The stretch
    curve is applied to the size of the difference and the sign is kept, so
    brighter and dimmer are treated the same way. NaN pixels are black.
    limit None: no usable scale, so the whole picture is mid grey.
    """
    if mode not in STRETCH_MODES:
        raise ValueError(f"Unknown stretch '{mode}'. Use one of {STRETCH_MODES}.")
    if limit is None or not limit > 0:
        grey = np.full(image.shape, 128, dtype=np.uint8)
        grey[~np.isfinite(image)] = 0
        return grey

    finite = np.isfinite(image)
    safe = np.where(finite, image, 0.0)
    scaled = np.clip(safe / limit, -1.0, 1.0)
    signed = np.sign(scaled) * _curve(np.abs(scaled), mode)      # -1 .. +1
    grey = np.round((signed + 1.0) / 2.0 * 255).astype(np.uint8)
    grey[~finite] = 0
    return grey


# ---------- Backend 19: stacking ----------

# combine: "mean" = average the frames, "sum" = plain addition
STACK_COMBINE = ("mean", "sum")
# group: "detector" = one stack per detector, "all" = one stack of everything
STACK_GROUPS = ("detector", "all")


def _stack_one_group(group, combine, detector_value):
    """Combine the frames of ONE group into one new frame."""
    n = len(group)
    cube = np.stack([f["image"] for f in group])          # shape (n, height, width)
    finite = np.isfinite(cube)
    count = finite.sum(axis=0)                            # usable frames per pixel
    total = np.where(finite, cube, 0.0).sum(axis=0)
    has_data = count > 0

    # A pixel with no usable value in any frame stays NaN
    image = np.full(total.shape, np.nan)
    if combine == "mean":
        image[has_data] = total[has_data] / count[has_data]
    else:
        image[has_data] = total[has_data]

    new_frame = dict(group[0])                            # copy, keeps the first frame's WCS
    new_frame["image"] = image
    new_frame["detector"] = detector_value
    new_frame["n_stacked"] = n
    new_frame["wavelength_um"] = float(np.mean([f["wavelength_um"] for f in group]))

    # Mean observation time: the first time plus the average gap
    t0 = group[0]["obs_time"]
    new_frame["obs_time"] = t0 + sum((f["obs_time"] - t0 for f in group), timedelta()) / n

    # Noise: variances of added images add up. A mean divides by count squared.
    if all(f.get("variance") is not None for f in group):
        vcube = np.stack([f["variance"] for f in group])
        vtotal = np.where(np.isfinite(vcube), vcube, 0.0).sum(axis=0)
        variance = np.full(vtotal.shape, np.nan)
        if combine == "mean":
            variance[has_data] = vtotal[has_data] / count[has_data] ** 2
        else:
            variance[has_data] = vtotal[has_data]
        new_frame["variance"] = variance

    # A pixel is flagged if it was flagged in ANY of the frames
    if all(f.get("flags") is not None for f in group):
        new_frame["flags"] = np.bitwise_or.reduce(np.stack([f["flags"] for f in group]), axis=0)

    names = [str(f.get("source_file", "?")) for f in group]
    shown = ", ".join(names[:3]) + (", ..." if len(names) > 3 else "")
    new_frame["source_file"] = f"stack of {n}: {shown}"
    return new_frame


def stack_frames(frames, combine="mean", group="detector"):
    """Return NEW frames made by adding or averaging the given frames.

    combine: "mean" (average) or "sum" (plain addition).
    group:   "detector" = one stacked frame for each detector number,
             "all" = a single stacked frame from every frame (detector = 0).
    Each frame needs image, obs_time and wavelength_um (see FRAME_FORMAT.md).
    The result is sorted by (mean) observation time. NaN pixels are skipped,
    so a pixel that is NaN in only some frames still gets a value from the
    others (a sum of fewer frames is therefore a little smaller).
    n_stacked says how many frames went in. The wavelength is the mean of the
    inputs. Variances are combined, flags are OR-ed.
    All frames must have the same pixel size. The originals are not changed.
    """
    if combine not in STACK_COMBINE:
        raise ValueError(f"Unknown combine '{combine}'. Use one of {STACK_COMBINE}.")
    if group not in STACK_GROUPS:
        raise ValueError(f"Unknown group '{group}'. Use one of {STACK_GROUPS}.")
    if not frames:
        return []
    shape = frames[0]["image"].shape
    if any(f["image"].shape != shape for f in frames):
        raise ValueError("The frames have different sizes, so they cannot be stacked.")

    groups = {}
    for frame in frames:
        key = frame.get("detector") if group == "detector" else "all"
        groups.setdefault(key, []).append(frame)

    result = [_stack_one_group(members, combine, key if group == "detector" else 0)
              for key, members in groups.items()]
    result.sort(key=lambda f: f["obs_time"])
    return result