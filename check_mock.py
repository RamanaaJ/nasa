# check_mock.py
# Reads the mock FITS files back and prints a summary so we can check them.

from pathlib import Path

import numpy as np
from astropy.io import fits

folder = Path(__file__).parent / "data" / "mock"
files = sorted(folder.glob("mock_*.fits"))
print(f"Found {len(files)} files in {folder}\n")

for f in files:
    with fits.open(f) as hdul:
        data = hdul[0].data
        hdr = hdul[0].header
        # np.argmax finds the brightest pixel (the moving dot should be it)
        y, x = np.unravel_index(np.argmax(data), data.shape)
        print(
            f.name,
            hdr["DATE-OBS"][:10],
            "det", hdr["DETECTOR"],
            f"wave {hdr['WAVE_UM']:.2f}um",
            "| brightest pixel (x,y) =", (int(x), int(y)),
            "| true dot =", (round(hdr["DOTX"], 1), round(hdr["DOTY"], 1)),
        )