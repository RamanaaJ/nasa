# data_practice.py
# Task 23: a SECOND fake sky for the practice game.
# 12 FITS files with 4 moving dots at different speeds, plus fixed stars.
# Run it with:  python data_practice.py
#
# The files look exactly like the mock files (same parts, same header names),
# so data_mock.load_mock_frame() can read them. But they do NOT contain the
# true dot positions. The answers are written to a separate file,
# data/practice/answers.json, which is NOT served to the web page.
#
# This file is not connected to main.py yet (the game page comes later).

import json
import math
from datetime import timedelta

import numpy as np
from astropy.io import fits

import config
import data_mock as dm                   # reuse the helpers and settings of the mock data
from processing import cutout_frame

OUT_DIR = config.PRACTICE_DIR
ANSWERS_FILE = OUT_DIR / "answers.json"  # same file practice_check.py reads

# An arbitrary EMPTY patch of fake sky. It is not a real target and is far from
# the normal mock sky (WISE 0855), so the two never overlap.
PRACTICE_RA = 150.0
PRACTICE_DEC = 2.0
SEED = 7                                 # different noise from the mock data

# The hidden movers. Positions are in PIXELS of the full 100 x 100 image,
# velocity is pixels per frame. Speeds are slow, medium, fast, very fast.
# (All numbers are my own choices. Retune them when the game is built.)
# The tracks avoid the fixed stars so a mover never hides inside one.
MOVERS = [
    {"id": "A", "label": "slow",      "start": (10.0, 85.0), "velocity": (0.6, -0.2), "amplitude": 150.0},
    {"id": "B", "label": "medium",    "start": (12.0, 10.0), "velocity": (1.5, 0.8),  "amplitude": 120.0},
    {"id": "C", "label": "fast",      "start": (90.0, 20.0), "velocity": (-3.0, 0.5), "amplitude": 100.0},
    {"id": "D", "label": "very fast", "start": (95.0, 95.0), "velocity": (-4.5, -1.5), "amplitude": 90.0},
]


def generate_practice_frames():
    """Write the FITS files and the answers file into OUT_DIR."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wcs = dm.make_wcs(PRACTICE_RA, PRACTICE_DEC)

    # Dead pixels: the same places in every frame (as in the mock data)
    bad_xy = dm.random_pixels_off_dot_track(dm.N_BAD_PIXELS, np.random.default_rng(SEED + 1000))

    answers = []
    for m in MOVERS:
        speed = math.hypot(*m["velocity"])
        answers.append({
            "id": m["id"], "label": m["label"],
            "speed_pix_per_frame": round(speed, 3),
            "speed_arcsec_per_day": round(speed * dm.PIXEL_SCALE_ARCSEC / dm.DAYS_BETWEEN, 3),
            "positions": [],
        })

    for i in range(dm.N_FRAMES):
        obs_time = dm.START_DATE + timedelta(days=dm.DAYS_BETWEEN * i)
        detector = i % 6 + 1
        wavelength = dm.WAVE_MIN_UM + i * (dm.WAVE_MAX_UM - dm.WAVE_MIN_UM) / (dm.N_FRAMES - 1)

        rng = np.random.default_rng(SEED + i)
        image = rng.normal(loc=10.0, scale=1.0, size=(dm.IMAGE_SIZE, dm.IMAGE_SIZE))
        for (sx, sy, amp) in dm.STATIC_STARS:
            dm.add_blob(image, sx, sy, amp, 1.5)

        for m, ans in zip(MOVERS, answers):
            x = m["start"][0] + m["velocity"][0] * i
            y = m["start"][1] + m["velocity"][1] * i
            dm.add_blob(image, x, y, m["amplitude"], dm.DOT_SIGMA_PIX)
            ra, dec = wcs.wcs_pix2world(x, y, 0)          # 0 = pixels counted from 0
            ans["positions"].append({"frame": i, "obs_time": obs_time.isoformat(),
                                     "x": round(x, 3), "y": round(y, 3),
                                     "ra_deg": float(ra), "dec_deg": float(dec)})

        flags, variance = dm.make_flags_and_variance(image, bad_xy, rng)

        hdu = fits.PrimaryHDU(data=image.astype(np.float32), header=wcs.to_header())
        hdu.header["DATE-OBS"] = (obs_time.isoformat(), "Observation date/time (UTC)")
        hdu.header["DETECTOR"] = (detector, "Detector number 1-6 (mock)")
        hdu.header["WAVE_UM"] = (round(wavelength, 4), "Band centre, microns (mock)")
        hdu.header["PRACTICE"] = (True, "Fake practice-game data")
        flags_hdu = fits.ImageHDU(data=flags, name="FLAGS")
        flags_hdu.header["FLAG_1"] = "bad pixel (mock)"
        flags_hdu.header["FLAG_2"] = "cosmic ray (mock)"
        flags_hdu.header["FLAG_4"] = "contaminated (mock)"
        var_hdu = fits.ImageHDU(data=variance.astype(np.float32), name="VARIANCE")

        path = OUT_DIR / f"practice_{i:02d}.fits"
        fits.HDUList([hdu, flags_hdu, var_hdu]).writeto(path, overwrite=True)
        print("wrote", path.name)

    document = {
        "description": "Answers for the practice game. Positions are in the full 100x100 image; "
                       "ra_deg/dec_deg are the same spots on the sky. Do not serve this file.",
        "center_ra_deg": PRACTICE_RA,
        "center_dec_deg": PRACTICE_DEC,
        "pixel_scale_arcsec": dm.PIXEL_SCALE_ARCSEC,
        "n_frames": dm.N_FRAMES,
        "movers": answers,
    }
    ANSWERS_FILE.write_text(json.dumps(document, indent=1), encoding="utf-8")
    print("wrote", ANSWERS_FILE.name)


def get_frames(ra_deg, dec_deg, fov_arcmin):
    """Practice data source (same signature as data_mock.get_frames).

    Returns cutouts sorted by obs_time; an empty list if the position is not
    on the practice sky. Not connected to main.py yet.
    """
    if fov_arcmin <= 0:
        raise ValueError("Field of view must be greater than zero.")
    files = sorted(OUT_DIR.glob("practice_*.fits"))
    if not files:
        raise FileNotFoundError("No practice files found. Run: python data_practice.py")
    frames = []
    for path in files:
        frame = dm.load_mock_frame(path)
        try:
            frames.append(cutout_frame(frame, ra_deg, dec_deg, fov_arcmin))
        except ValueError:
            continue
    frames.sort(key=lambda f: f["obs_time"])
    return frames


if __name__ == "__main__":
    generate_practice_frames()