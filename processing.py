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
#   8. find_moving_dot() (Backend 20) work out the moving dot's position in
#      each frame, so the page can draw a motion trail through them
#   9. colour_picture() / rgb_to_png_bytes()   (Backend 21) three wavelengths
#      become the red, green and blue channels of one colour picture
# This file never downloads data and never reads files.
# A "frame" is a dictionary described in FRAME_FORMAT.md.

import io
import warnings
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


def _png_factor(height, width, target_size=400):
    """Whole-number enlargement used by image_to_png_bytes (1 = not enlarged)."""
    return max(1, target_size // max(height, width))


def image_to_png_bytes(grey, target_size=400):
    """Turn a uint8 grey array into PNG bytes (the contents of a .png file).

    - Flipped vertically so north is up (FITS stores the bottom row first).
    - Enlarged by a whole-number factor to about target_size pixels, using
      'nearest' scaling so each data pixel stays a sharp square.
    """
    height, width = grey.shape
    picture = Image.fromarray(np.ascontiguousarray(np.flipud(grey)))

    factor = _png_factor(height, width, target_size)
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


# ---------- Backend 20: motion trail data ----------

# A spot counts as "found" only if it stands out from the noise by this many
# times. 5 is a starting guess; retune on real data (after-data #15).
TRAIL_MIN_SNR = 5.0
# The position is refined using the pixels this close to the brightest one
TRAIL_CENTROID_HALF = 3
# Largest signal-to-noise we report (keeps the number JSON-friendly)
TRAIL_SNR_CAP = 9999.0


def pixel_to_png_position(x, y, height, width, target_size=400):
    """Where a data pixel ends up in the PNG made by image_to_png_bytes().

    x, y: pixel position in the frame image, counted from 0. y counts from
          the BOTTOM row (the FITS way). The PNG is flipped so north is up
          and is enlarged by a whole-number factor, so this undoes both.
    Returns (png_x, png_y) measured from the top-left corner of the PNG,
    in PNG pixels. The page can draw a circle or line point there.
    """
    factor = _png_factor(height, width, target_size)
    return (x + 0.5) * factor, (height - 1 - y + 0.5) * factor


def find_moving_dot(frames, min_snr=TRAIL_MIN_SNR):
    """Work out where the moving dot is in each frame. Returns a list with
    one dictionary per frame, in the same order as `frames`.

    How it works (simple version):
      1. The fixed sky is the MEDIAN of all frames. Fixed stars are in the
         same place every time, so they stay in the median. A moving dot is
         in a different place each time, so it does not.
      2. Each frame minus the fixed sky leaves (mostly) just the moving dot.
      3. The brightest leftover spot is the dot. Its position is refined
         with a small centroid (weighted average of the pixels around it).
      4. If the spot does not stand out from the noise by min_snr times,
         the frame is marked found=False.

    Each dictionary has:
      index       frame number in `frames`
      obs_time    the frame's observation time
      found       True if a dot was found
      x, y        pixel position (counted from 0, y from the bottom row),
                  or None if not found
      png_x, png_y  the same spot in the PNG picture (see pixel_to_png_position)
      ra_deg, dec_deg  sky position from the frame's WCS (None if no WCS)
      snr         how strongly the dot stands out (0.0 if nothing positive)

    Needs at least 3 frames of the same pixel size on the same pixel grid
    (true for the mock data; real pointings may need re-aligning first).
    A moving dot that stays within about one dot-width of the same pixels
    for half of the frames is partly removed by the median, so very slow
    movers are not found by this method.
    Flags are not used yet (real flag bits are not known).
    The original frames are not changed.
    """
    if not min_snr > 0:
        raise ValueError("min_snr must be greater than zero.")
    if len(frames) < 3:
        raise ValueError("At least 3 frames are needed to find a moving dot.")
    shape = frames[0]["image"].shape
    if any(f["image"].shape != shape for f in frames):
        raise ValueError("The frames have different sizes, so a trail cannot be worked out.")
    height, width = shape

    cube = np.stack([f["image"] for f in frames]).astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)   # all-NaN pixels
        fixed_sky = np.nanmedian(cube, axis=0)

    trail = []
    for i, frame in enumerate(frames):
        entry = {"index": i, "obs_time": frame.get("obs_time"), "found": False,
                 "x": None, "y": None, "png_x": None, "png_y": None,
                 "ra_deg": None, "dec_deg": None, "snr": 0.0}
        trail.append(entry)

        diff = frame["image"] - fixed_sky
        finite = np.isfinite(diff)
        if not finite.any():
            continue
        diff = diff - np.median(diff[finite])          # removes a constant background offset
        sigma = 1.4826 * float(np.median(np.abs(diff[finite])))   # noise size (robust)

        # The brightest leftover spot (NaN pixels are never chosen)
        peak_y, peak_x = np.unravel_index(np.argmax(np.where(finite, diff, -np.inf)), shape)
        peak = float(diff[peak_y, peak_x])
        if peak <= 0:
            continue
        snr = TRAIL_SNR_CAP if sigma <= 0 else min(peak / sigma, TRAIL_SNR_CAP)
        entry["snr"] = float(snr)
        if snr < min_snr:
            continue

        # Refine the position: weighted average of the bright pixels around the peak
        h = TRAIL_CENTROID_HALF
        y0, y1 = max(0, peak_y - h), min(height, peak_y + h + 1)
        x0, x1 = max(0, peak_x - h), min(width, peak_x + h + 1)
        window = np.where(finite[y0:y1, x0:x1], diff[y0:y1, x0:x1], 0.0)
        weights = np.where(window > 2 * sigma, window, 0.0)
        if weights.sum() > 0:
            yy, xx = np.mgrid[y0:y1, x0:x1]
            x = float((weights * xx).sum() / weights.sum())
            y = float((weights * yy).sum() / weights.sum())
        else:
            x, y = float(peak_x), float(peak_y)

        entry["found"] = True
        entry["x"], entry["y"] = x, y
        entry["png_x"], entry["png_y"] = pixel_to_png_position(x, y, height, width)
        wcs = frame.get("wcs")
        if wcs is not None:
            ra, dec = wcs.pixel_to_world_values(x, y)
            entry["ra_deg"], entry["dec_deg"] = float(ra) % 360.0, float(dec)
    return trail


# ---------- Backend 21: colour picture from 3 wavelengths ----------

def pick_colour_frames(frames):
    """Choose which 3 frames become red, green and blue.

    Longer wavelength = redder, like in a normal rainbow. So the frame with
    the LONGEST wavelength is red, the one in the middle is green and the
    one with the SHORTEST wavelength is blue.
    Returns (red_index, green_index, blue_index), numbers in `frames`.
    """
    if len(frames) < 3:
        raise ValueError("At least 3 frames are needed for a colour picture.")
    order = sorted(range(len(frames)), key=lambda i: frames[i]["wavelength_um"])
    if frames[order[0]]["wavelength_um"] == frames[order[-1]]["wavelength_um"]:
        raise ValueError("All frames have the same wavelength, so there are no colours to show.")
    return order[-1], order[len(order) // 2], order[0]


def colour_picture(frames, channels=None, mode="sqrt", shared_scale=False):
    """Make one colour picture: a uint8 array of shape (height, width, 3).

    channels:     (red_index, green_index, blue_index) = which frames to use.
                  None = choose automatically with pick_colour_frames().
    mode:         stretch curve, one of STRETCH_MODES.
    shared_scale: False = each colour is stretched on its own (every channel
                  uses its full brightness range; good for looking at shapes).
                  True = the 3 frames share one black/white point, so the
                  colour of a source shows its real brightness ratio.
    A source that does not move has the same place in all three frames and
    looks white or grey. A MOVING source is in a different place in each
    frame, so it shows up as separate red, green and blue dots.
    The original frames are not changed. All 3 frames must have the same
    pixel size (and, as for stacking, the same pixel grid).
    """
    if mode not in STRETCH_MODES:
        raise ValueError(f"Unknown stretch '{mode}'. Use one of {STRETCH_MODES}.")
    if channels is None:
        channels = pick_colour_frames(frames)
    else:
        channels = tuple(channels)
        if len(channels) != 3 or any(
                isinstance(i, bool) or not isinstance(i, (int, np.integer)) or not 0 <= i < len(frames)
                for i in channels):
            raise ValueError(f"channels must be three frame numbers from 0 to {len(frames) - 1}.")

    chosen = [frames[i] for i in channels]
    shape = chosen[0]["image"].shape
    if any(f["image"].shape != shape for f in chosen):
        raise ValueError("The frames have different sizes, so they cannot make one colour picture.")

    limits = shared_limits(chosen) if shared_scale else None
    planes = [stretch_image(f["image"], mode=mode, limits=limits) for f in chosen]
    return np.dstack(planes)                  # red, green, blue


def rgb_to_png_bytes(rgb, target_size=400):
    """Turn a (height, width, 3) uint8 colour array into PNG bytes.

    Same rules as image_to_png_bytes: flipped so north is up, enlarged by a
    whole-number factor with 'nearest' scaling. So pixel_to_png_position()
    works for colour pictures too.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("A colour array must have the shape (height, width, 3).")
    height, width, _ = rgb.shape
    picture = Image.fromarray(np.ascontiguousarray(np.flipud(rgb)))

    factor = _png_factor(height, width, target_size)
    if factor > 1:
        picture = picture.resize((width * factor, height * factor),
                                 Image.Resampling.NEAREST)

    buffer = io.BytesIO()
    picture.save(buffer, format="PNG")
    return buffer.getvalue()