# data_irsa.py
# Backend 25: SKELETON of the real data source (IRSA / SPHEREx).
# Nothing here downloads anything yet. Every function says what it WILL do
# and raises NotImplementedError. Later only the insides change:
# get_frames() keeps the signature of data_mock.get_frames and returns
# frames in the FRAME_FORMAT.md format.
#
# Facts marked (tutorial) come from IRSA's SPHEREx tutorial notebooks
# ("Introduction to SPHEREx Spectral Images" and "Download a collection of
# SPHEREx Spectral Image cutouts ..."). Facts marked (UNVERIFIED) have not
# been checked yet: see docs/DATA_NOTES.md.
#
# Real code is written in the "after the data" part of TODO_LIST.md
# (#2 search, #3 download, #4 read). Nothing here is connected to main.py.

# The keys every frame must have (see FRAME_FORMAT.md). The contract test
# (after-data #6) will compare real frames against this list.
FRAME_KEYS = ("image", "wcs", "obs_time", "wavelength_um", "detector",
              "flags", "variance", "source_file")


def _not_written(name, step):
    raise NotImplementedError(
        f"data_irsa.{name}() is not written yet (TODO after-data #{step}). "
        f"Set USE_MOCK = True in config.py to use the mock data.")


def search_images(ra_deg, dec_deg, fov_arcmin):
    """WILL ask IRSA which SPHEREx images cover this position.

    Returns a list of dictionaries sorted by observation time, each with:
      cutout_url    link that returns a cutout of that image (tutorial: the
                    TAP query builds it from a.uri + '?center=RA,DECd&size=...')
      obs_time_raw  the archive's time value (tutorial: p.time_bounds_lower;
                    unit and format UNVERIFIED, probably MJD)
      bandpass      e.g. 'SPHEREx-D2' (tutorial: p.energy_bandpassname)
    Live query, no list of files is kept (see Backend 27).
    Needs the network. A slow answer must raise TimeoutError so main.py can
    turn it into HTTP 504.
    """
    _not_written("search_images", 2)


def download_cutout(cutout_url):
    """WILL download one cutout and return it as an astropy HDUList held in memory.

    Tutorial: reading can exceed astropy's default timeout (they set
    astropy.utils.data.conf.remote_timeout = 120), and a few downloads fail
    with transient errors (TimeoutError, urllib.error.HTTPError,
    http.client.IncompleteRead, http.client.RemoteDisconnected), so this needs
    retries (TODO after-data #10). Raises TimeoutError if it keeps failing.
    """
    _not_written("download_cutout", 3)


def read_cutout(hdulist, source_url, obs_time):
    """WILL turn one downloaded cutout into a frame dictionary (FRAME_FORMAT.md).

    Planned mapping:
      image          <- extension IMAGE (surface brightness, MJy/sr)      (tutorial)
      wcs            <- WCS(IMAGE header), the sky WCS of the cutout       (tutorial)
      obs_time       <- passed in from the search (UTC datetime); which header
                        card holds the observation time is UNVERIFIED
      wavelength_um  <- spectral WCS (key "W") at the cutout centre.       (tutorial)
                        Wavelength varies across a detector, so this is the
                        centre-pixel value.
      detector       <- IMAGE header card DETECTOR                         (tutorial)
      flags          <- extension FLAGS; bit meanings are in its header
                        (MSKNnnnn name, MSKDnnnn description)              (tutorial)
      variance       <- extension VARIANCE (MJy^2/sr^2)                    (tutorial)
      source_file    <- source_url
    Not used for now: ZODI, EPSF, WCS-WAVE.
    """
    _not_written("read_cutout", 4)


def get_frames(ra_deg, dec_deg, fov_arcmin):
    """The real data source. Same signature as data_mock.get_frames.

    WILL: search_images -> download_cutout -> read_cutout for each hit, drop
    downloads that failed, sort by obs_time and return the list (empty if no
    image covers the position). Capping the count (config.MAX_FRAMES) comes
    in after-data #8.
    """
    if fov_arcmin <= 0:
        raise ValueError("Field of view must be greater than zero.")
    _not_written("get_frames", "2-4")