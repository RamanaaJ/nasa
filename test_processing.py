# test_processing.py
# Tests processing.py using the mock FITS files.
# Run it with:  python test_processing.py
# PNGs are saved in cache/test_png/ (the cache/ folder is already in .gitignore).

from datetime import datetime
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

import processing

MOCK_DIR = Path(__file__).parent / "data" / "mock"
OUT_DIR = Path(__file__).parent / "cache" / "test_png"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_mock_frame(path):
    """Build a frame dictionary (see FRAME_FORMAT.md) from one mock file.
    This is only a helper for this test. The real loader comes later."""
    with fits.open(path) as hdul:
        hdr = hdul[0].header
        return {
            "image": np.array(hdul[0].data, dtype=float),
            "wcs": WCS(hdr),
            "obs_time": datetime.fromisoformat(hdr["DATE-OBS"]),
            "wavelength_um": hdr["WAVE_UM"],
            "detector": hdr["DETECTOR"],
            "flags": np.array(hdul["FLAGS"].data),
            "variance": np.array(hdul["VARIANCE"].data, dtype=float),
            "source_file": path.name,
        }


frame0 = load_mock_frame(MOCK_DIR / "mock_00.fits")
frame11 = load_mock_frame(MOCK_DIR / "mock_11.fits")

# Centre of the mock images in sky coordinates (RA, Dec in degrees)
ra_c, dec_c = frame0["wcs"].wcs.crval
FOV = 6.0   # arcminutes. The full mock image is about 10.3 arcmin wide.

print("--- Test 1: cutouts follow the dot ---")
for name, frame in [("frame 0", frame0), ("frame 11", frame11)]:
    patch = processing.cutout_frame(frame, ra_c, dec_c, FOV)
    h, w = patch["image"].shape
    y, x = np.unravel_index(np.argmax(patch["image"]), patch["image"].shape)
    # Sky position of the middle of the patch, compared with what we asked for
    mid = patch["wcs"].pixel_to_world((w - 1) / 2, (h - 1) / 2)
    sep = mid.separation(SkyCoord(ra_c * u.deg, dec_c * u.deg)).arcsec
    print(f"{name}: patch {w}x{h} px | brightest (x,y) = ({x},{y}) "
          f"| centre is {sep:.1f} arcsec from requested | "
          f"flags/variance shapes match: "
          f"{patch['flags'].shape == patch['variance'].shape == patch['image'].shape}")

print("\n--- Test 2: the three stretches ---")
patch0 = processing.cutout_frame(frame0, ra_c, dec_c, FOV)
for mode in processing.STRETCH_MODES:
    grey = processing.stretch_image(patch0["image"], mode=mode)
    print(f"{mode}: dtype {grey.dtype}, min {grey.min()}, max {grey.max()}")
    png = processing.image_to_png_bytes(grey)
    (OUT_DIR / f"frame00_{mode}.png").write_bytes(png)

png11 = processing.frame_to_png(frame11, ra_c, dec_c, FOV, stretch="sqrt")
(OUT_DIR / "frame11_sqrt.png").write_bytes(png11)
print("PNG starts with the PNG signature:", png11[:8] == b"\x89PNG\r\n\x1a\n")

print("\n--- Test 3: patch hanging off the edge of the image ---")
edge = processing.cutout_frame(frame0, ra_c, dec_c + 4 / 60, FOV)   # 4 arcmin north
nan_count = int(np.isnan(edge["image"]).sum())
print("NaN pixels in patch:", nan_count, "(should be more than 0)")
edge_png = processing.frame_to_png(frame0, ra_c, dec_c + 4 / 60, FOV)
(OUT_DIR / "frame00_edge.png").write_bytes(edge_png)
print("Edge patch still made a PNG:", len(edge_png) > 0)

print("\n--- Test 4: position far outside the image ---")
try:
    processing.cutout_frame(frame0, ra_c + 5, dec_c, FOV)
    print("No error raised (this is WRONG)")
except ValueError as err:
    print("Got the expected friendly error:", err)

print("\nPNGs saved in", OUT_DIR)