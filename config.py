# config.py
# Central settings for the SPHEREx Sky Viewer.
# Other files do:  import config   and then use  config.USE_MOCK  etc.
# This file only holds settings. It never downloads or reads data.

from pathlib import Path

# ---------- Data source switch ----------
# True  = use the fake FITS files in data/mock/ (data_mock.py)
# False = use real SPHEREx data from IRSA (data_irsa.py, written later)
USE_MOCK = True

# ---------- Real data release ----------
# Name of the SPHEREx data release / collection to query.
# PLACEHOLDER: "spherex_qr2" comes from our own TODO_LIST.md (Backend after-data #2).
# It has NOT been verified against IRSA yet. Check it when the real data layer is built.
# Switching to a newer release should only need this one line to change.
RELEASE_NAME = "spherex_qr2"

# ---------- Field of view ----------
# All field-of-view values in this project use ARCMINUTES (see FRAME_FORMAT.md).
# Minimum and maximum limits come later (TODO Backend 7).
DEFAULT_FOV_ARCMIN = 6.0   # matches the FOV used in test_processing.py

# ---------- Limits ----------
# Most frames returned for one request. 50 is a starting guess; retune on real data.
MAX_FRAMES = 50

# ---------- Folders ----------
BASE_DIR = Path(__file__).parent
MOCK_DIR = BASE_DIR / "data" / "mock"   # where data_mock.py writes the fake files
CACHE_DIR = BASE_DIR / "cache"          # used by the cache step later (Backend 8)


if __name__ == "__main__":
    # Quick self-test: run  python config.py
    print("USE_MOCK           :", USE_MOCK)
    print("RELEASE_NAME       :", RELEASE_NAME, "(unverified placeholder)")
    print("DEFAULT_FOV_ARCMIN :", DEFAULT_FOV_ARCMIN)
    print("MAX_FRAMES         :", MAX_FRAMES)
    print("MOCK_DIR           :", MOCK_DIR, "| exists:", MOCK_DIR.exists())
    print("CACHE_DIR          :", CACHE_DIR)