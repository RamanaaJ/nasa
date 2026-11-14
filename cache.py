# cache.py
# Backend 8: saves cutouts on disk so a repeat request is instant.
#
# A "cutout set" is the list of frames (see FRAME_FORMAT.md) for one request.
# Each request is identified by four things: RA, Dec, FOV and the release.
# Same four values -> same file in cache/cutouts/.
#
# This file does not download anything and does not make pictures.
# It only saves and loads lists of frames. Later, the Frames endpoint
# (Backend 9) will call get_or_load() with the data source's get_frames.
#
# Run  python cache.py        to see what is in the cache
# Run  python cache.py clear  to empty it

import pickle
import re
import sys
import threading
from pathlib import Path

import config

# Where cached files go. Folder is inside cache/, which is already in .gitignore.
CUTOUT_DIR = config.CACHE_DIR / "cutouts"

# The web server answers several requests at the same time (the page asks for
# 12 images at once). This lock makes sure only one request at a time does the
# slow "load and save" work, so we never download or write the same thing twice.
_load_lock = threading.Lock()

# Rounding used when building the file name. Two requests that differ by less
# than this count as the same request.
RA_DEC_DECIMALS = 5     # 0.00001 degrees = about 0.04 arcsec
FOV_DECIMALS = 3        # 0.001 arcmin


def current_release():
    """Name used in the cache key for the data source we are using now.

    Mock data and real data must never share cache files, so mock gets its
    own name. For real data the key is config.RELEASE_NAME, so switching to
    a newer release automatically starts a fresh cache.
    """
    return "mock" if config.USE_MOCK else config.RELEASE_NAME


def make_key(ra_deg, dec_deg, fov_arcmin, release=None):
    """Return the cache key (also the file name without '.pkl')."""
    if release is None:
        release = current_release()
    for value in (ra_deg, dec_deg, fov_arcmin):
        if value != value:                       # NaN is the only number not equal to itself
            raise ValueError("RA, Dec and FOV must be real numbers.")

    # round(...) + 0.0 turns -0.0 into 0.0 so both spellings give the same key
    ra = round(float(ra_deg), RA_DEC_DECIMALS) + 0.0
    dec = round(float(dec_deg), RA_DEC_DECIMALS) + 0.0
    fov = round(float(fov_arcmin), FOV_DECIMALS) + 0.0

    # Keep only safe characters from the release name, so it is a valid file name
    safe_release = re.sub(r"[^A-Za-z0-9_.-]", "_", str(release))
    return f"{safe_release}_ra{ra:.{RA_DEC_DECIMALS}f}_dec{dec:.{RA_DEC_DECIMALS}f}_fov{fov:.{FOV_DECIMALS}f}"


def _path(ra_deg, dec_deg, fov_arcmin, release, cache_dir):
    folder = Path(cache_dir) if cache_dir is not None else CUTOUT_DIR
    return folder / (make_key(ra_deg, dec_deg, fov_arcmin, release) + ".pkl")


def get(ra_deg, dec_deg, fov_arcmin, release=None, cache_dir=None):
    """Return the saved list of frames, or None if this request is not cached."""
    path = _path(ra_deg, dec_deg, fov_arcmin, release, cache_dir)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        # Half-written or damaged file: delete it and act as if it was never cached
        path.unlink(missing_ok=True)
        return None


def save(frames, ra_deg, dec_deg, fov_arcmin, release=None, cache_dir=None):
    """Save a list of frames. Returns the path of the file written.

    An empty list is NOT saved: "no images" might change when new data
    arrives, and we don't want to remember it forever.
    """
    if not frames:
        return None
    path = _path(ra_deg, dec_deg, fov_arcmin, release, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file first, then rename. If the program stops
    # half-way, the real cache file is never left broken.
    temp = path.with_suffix(".tmp")
    with open(temp, "wb") as f:
        pickle.dump(frames, f, protocol=pickle.HIGHEST_PROTOCOL)
    temp.replace(path)
    return path


def get_or_load(ra_deg, dec_deg, fov_arcmin, loader, release=None, cache_dir=None):
    """Return the frames from the cache, or call loader() and cache the result.

    loader: a function that takes (ra_deg, dec_deg, fov_arcmin) and returns a
            list of frames, like get_frames in FRAME_FORMAT.md.
    """
    frames = get(ra_deg, dec_deg, fov_arcmin, release, cache_dir)
    if frames is not None:
        return frames
    with _load_lock:
        # Another request may have finished the same job while we waited
        frames = get(ra_deg, dec_deg, fov_arcmin, release, cache_dir)
        if frames is not None:
            return frames
        frames = loader(ra_deg, dec_deg, fov_arcmin)
        save(frames, ra_deg, dec_deg, fov_arcmin, release, cache_dir)
        return frames


def cache_info(cache_dir=None):
    """Return (number_of_files, total_size_in_bytes)."""
    folder = Path(cache_dir) if cache_dir is not None else CUTOUT_DIR
    files = list(folder.glob("*.pkl")) if folder.exists() else []
    return len(files), sum(p.stat().st_size for p in files)


def clear_cache(cache_dir=None):
    """Delete every cached cutout file. Returns how many were deleted.

    Use this after you re-run data_mock.py, because old cached cutouts
    would still show the old mock images.
    """
    folder = Path(cache_dir) if cache_dir is not None else CUTOUT_DIR
    count = 0
    if folder.exists():
        for p in folder.glob("*.pkl"):
            p.unlink()
            count += 1
    return count


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        print("Deleted", clear_cache(), "cached file(s) from", CUTOUT_DIR)
    else:
        n, size = cache_info()
        print("Cache folder:", CUTOUT_DIR)
        print(f"{n} file(s), {size / 1024:.1f} KB")
        print("Current release key:", current_release())