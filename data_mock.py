# data_mock.py
# Makes 12 fake SPHEREx-like FITS images with one moving dot.
# Run it with:  python data_mock.py
# It only WRITES files into data/mock/. It never makes PNGs or pictures.

import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from targets import TARGETS, position_at_epoch

# ---------- Settings you can change ----------
OUT_DIR = Path(__file__).parent / "data" / "mock"   # where files are saved
N_FRAMES = 12                    # how many fake images
IMAGE_SIZE = 100                 # image is 100 x 100 pixels
PIXEL_SCALE_ARCSEC = 6.2         # ASSUMPTION: arcseconds per pixel (verify later)
START_DATE = datetime(2026, 1, 1)
DAYS_BETWEEN = 30                # days between frames
SPEED_BOOST = 10                 # dot moves 10x faster than the real object
WAVE_MIN_UM, WAVE_MAX_UM = 0.75, 5.0   # ASSUMPTION: mock wavelength range (microns)
DOT_AMPLITUDE = 200.0            # dot is the brightest thing in the image
DOT_SIGMA_PIX = 1.2              # dot size
SEED = 42                        # makes the noise the same every run

# Fixed stars as (x, y, brightness) in pixel coordinates. They never move.
STATIC_STARS = [
    (20, 25, 80), (75, 30, 60), (30, 75, 50),
    (80, 80, 70), (60, 15, 40), (15, 60, 55),
]


def dot_sky_position(days_since_start):
    """Return (ra_deg, dec_deg) of the moving dot, a number of days after START_DATE.

    Starts at WISE 0855's 2026.0 position and moves with its real
    proper motion multiplied by SPEED_BOOST.
    """
    t = TARGETS["wise0855"]
    ra0, dec0 = position_at_epoch("wise0855", 2026.0)
    years = days_since_start / 365.25
    # mas/yr -> degrees: divide by 3,600,000
    d_dec = t["pmdec_mas_yr"] * SPEED_BOOST * years / 3_600_000
    # pmra already includes cos(Dec), so divide it out to get a change in RA
    d_ra = (t["pmra_mas_yr"] * SPEED_BOOST * years / 3_600_000
            / math.cos(math.radians(dec0)))
    return ra0 + d_ra, dec0 + d_dec


def make_wcs(ra_center, dec_center):
    """Build the WCS: the rule that links pixel positions to RA/Dec."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]            # standard sky projection
    w.wcs.crval = [ra_center, dec_center]             # sky position of the reference pixel
    w.wcs.crpix = [(IMAGE_SIZE + 1) / 2, (IMAGE_SIZE + 1) / 2]  # reference pixel (image centre)
    scale_deg = PIXEL_SCALE_ARCSEC / 3600.0
    w.wcs.cdelt = [-scale_deg, scale_deg]             # RA grows to the left, as on a sky map
    w.wcs.cunit = ["deg", "deg"]
    return w


def add_blob(image, x, y, amplitude, sigma):
    """Add a round fuzzy spot (a 'Gaussian') to the image at pixel (x, y)."""
    yy, xx = np.mgrid[0:IMAGE_SIZE, 0:IMAGE_SIZE]
    image += amplitude * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma ** 2))


def generate_mock_frames():
    """Write N_FRAMES FITS files into OUT_DIR."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Centre the image on where the dot is halfway through, so it stays in view.
    mid_days = DAYS_BETWEEN * (N_FRAMES - 1) / 2
    ra_c, dec_c = dot_sky_position(mid_days)
    wcs = make_wcs(ra_c, dec_c)

    for i in range(N_FRAMES):
        days = DAYS_BETWEEN * i
        obs_time = START_DATE + timedelta(days=days)
        detector = i % 6 + 1                                   # 1,2,...,6,1,2,...
        wavelength = WAVE_MIN_UM + i * (WAVE_MAX_UM - WAVE_MIN_UM) / (N_FRAMES - 1)

        # Background noise (different each frame, but repeatable)
        rng = np.random.default_rng(SEED + i)
        image = rng.normal(loc=10.0, scale=1.0, size=(IMAGE_SIZE, IMAGE_SIZE))

        # Fixed stars
        for (sx, sy, amp) in STATIC_STARS:
            add_blob(image, sx, sy, amp, 1.5)

        # Moving dot: sky position -> pixel position using the WCS
        ra, dec = dot_sky_position(days)
        dot_x, dot_y = wcs.wcs_world2pix(ra, dec, 0)           # 0 = pixels counted from 0
        add_blob(image, float(dot_x), float(dot_y), DOT_AMPLITUDE, DOT_SIGMA_PIX)

        # Build the FITS file: pixel data + header
        hdu = fits.PrimaryHDU(data=image.astype(np.float32), header=wcs.to_header())
        hdu.header["DATE-OBS"] = (obs_time.isoformat(), "Observation date/time (UTC)")
        hdu.header["DETECTOR"] = (detector, "Detector number 1-6 (mock)")
        hdu.header["WAVE_UM"] = (round(wavelength, 4), "Band centre, microns (mock)")
        hdu.header["MOCK"] = (True, "Fake data for testing")
        hdu.header["DOTX"] = (float(dot_x), "TRUE dot x pixel (for testing)")
        hdu.header["DOTY"] = (float(dot_y), "TRUE dot y pixel (for testing)")

        path = OUT_DIR / f"mock_{i:02d}.fits"
        hdu.writeto(path, overwrite=True)
        print("wrote", path.name)


if __name__ == "__main__":
    generate_mock_frames()