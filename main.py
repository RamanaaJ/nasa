# main.py
# The web server (FastAPI). Start it with:   uvicorn main:app --reload
# Then open  http://127.0.0.1:8000/docs  to try the endpoints in your browser.
#
# Jobs:
#   GET /api/targets?year=..                                 the 5 preset targets (JSON)
#   GET /api/frames?ra=..&dec=..&fov=..&mode=..&stretch=..   list of frames (JSON)
#   GET /api/frames/{index}/image?...                        one frame as a PNG picture
#   everything else                                          files from the static/ folder
#
# Backend 11: every setting in the address is checked by params.py first.
# A bad value gives a clear message (HTTP 400) instead of a crash.
#
# main.py only connects the other files. The real work is done elsewhere:
#   params.py -> checks the address,  data_mock.py -> frames,
#   cache.py -> saves them,  processing.py -> PNG.

from pathlib import Path
from urllib.parse import urlencode
import math                      

import numpy as np
from astropy.wcs.utils import proj_plane_pixel_scales
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

import cache
import config
import data_mock
import params
import processing
import targets  

app = FastAPI(title="SPHEREx Sky Viewer")

STATIC_DIR = Path(__file__).parent / "static"

# Text shown in the /docs page for the settings
RA_HELP = "Right ascension. Degrees (133.8) or hours (08h55m10.8s, 08:55:10.8)."
DEC_HELP = "Declination. Degrees (-7.2) or -07d14m42s, -07:14:42."
FOV_HELP = f"Field of view in arcminutes, {config.MIN_FOV_ARCMIN:g} to {config.MAX_FOV_ARCMIN:g}. Default {config.DEFAULT_FOV_ARCMIN:g}."
STRETCH_HELP = "Brightness stretch: " + ", ".join(processing.STRETCH_MODES) + f". Default {params.DEFAULT_STRETCH}."
MODE_HELP = "How frames are combined: " + ", ".join(params.READY_MODES) + f". Default {params.DEFAULT_MODE}."
YEAR_HELP = "Optional year, for example 2026.0. Positions are moved to that year using proper motion. Empty = J2000."

def check_request(ra, dec, fov, stretch, mode):
    """Check the settings from the address. Bad input becomes a clear HTTP 400."""
    try:
        return params.validate_request(ra, dec, fov, stretch, mode)
    except ValueError as err:               # RequestError and CoordinateError are ValueErrors
        raise HTTPException(status_code=400, detail=str(err))


def frames_for(p):
    """Get the frames for one request: from the cache, or from the data source."""
    if not config.USE_MOCK:
        # data_irsa.py does not exist yet (TODO Backend 25)
        raise HTTPException(
            status_code=501,
            detail="Real SPHEREx data is not connected yet. Set USE_MOCK = True in config.py.")
    try:
        frames = cache.get_or_load(p.ra, p.dec, p.fov, data_mock.get_frames)
    except FileNotFoundError as err:        # mock files were never created
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    if not frames:
        raise HTTPException(status_code=404, detail="No images cover this sky position.")
    return frames


def describe_frame(index, frame, p):
    """Turn one frame into a small dictionary that can be sent as JSON."""
    height, width = frame["image"].shape
    wcs = frame["wcs"]

    # Pixel scale: how many arcseconds one pixel covers (mean of the two axes)
    pixel_scale_arcsec = float(np.mean(proj_plane_pixel_scales(wcs))) * 3600.0
    # Sky position of the middle of this cutout (pixel numbers start at 0)
    centre_ra, centre_dec = wcs.pixel_to_world_values((width - 1) / 2, (height - 1) / 2)

    # The link repeats every setting, in plain numbers, so it works on its own
    query = urlencode({"ra": p.ra, "dec": p.dec, "fov": p.fov, "mode": p.mode, "stretch": p.stretch})
    return {
        "index": index,
        "image_url": f"/api/frames/{index}/image?{query}",
        "obs_time": frame["obs_time"].isoformat(),
        "detector": int(frame["detector"]),
        "wavelength_um": float(frame["wavelength_um"]),
        "width_px": int(width),
        "height_px": int(height),
        "pixel_scale_arcsec": pixel_scale_arcsec,
        "center_ra_deg": float(centre_ra),
        "center_dec_deg": float(centre_dec),
    }


@app.get("/api/frames")
def list_frames(
    ra: str = Query(..., description=RA_HELP),
    dec: str = Query(..., description=DEC_HELP),
    fov: str | None = Query(None, description=FOV_HELP),
    stretch: str | None = Query(None, description=STRETCH_HELP),
    mode: str | None = Query(None, description=MODE_HELP),
):
    """The frame list: one entry per image, sorted by date."""
    p = check_request(ra, dec, fov, stretch, mode)
    frames = frames_for(p)
    return {
        "source": cache.current_release(),
        "ra_deg": p.ra,
        "dec_deg": p.dec,
        "fov_arcmin": p.fov,
        "stretch": p.stretch,
        "mode": p.mode,
        "frame_count": len(frames),
        "frames": [describe_frame(i, f, p) for i, f in enumerate(frames)],
    }


@app.get("/api/frames/{index}/image")
def frame_image(
    index: int,
    ra: str = Query(..., description=RA_HELP),
    dec: str = Query(..., description=DEC_HELP),
    fov: str | None = Query(None, description=FOV_HELP),
    stretch: str | None = Query(None, description=STRETCH_HELP),
    mode: str | None = Query(None, description=MODE_HELP),
):
    """One frame as a PNG picture. `index` is the number from the frame list."""
    p = check_request(ra, dec, fov, stretch, mode)
    frames = frames_for(p)                      # instant when it is already cached
    if index < 0 or index >= len(frames):
        raise HTTPException(status_code=404,
                            detail=f"There is no frame {index}. This request has {len(frames)} frames.")
    grey = processing.stretch_image(frames[index]["image"], mode=p.stretch)
    return Response(content=processing.image_to_png_bytes(grey), media_type="image/png")

@app.get("/api/targets")
def list_targets(year: str | None = Query(None, description=YEAR_HELP)):
    """The 5 preset targets, for the page's preset buttons."""
    epoch = None
    if year is not None and year.strip():
        try:
            epoch = float(year.strip())
        except ValueError:
            raise HTTPException(status_code=400,
                                detail=f"The year '{year}' is not a number. Use for example year=2026.")
        if not (math.isfinite(epoch) and 1900 <= epoch <= 2100):
            raise HTTPException(status_code=400,
                                detail="The year must be between 1900 and 2100.")
    items = targets.target_list(epoch)
    return {
        "epoch": "J2000" if epoch is None else epoch,
        "count": len(items),
        "targets": items,
    }

# Serve the web page files. This MUST stay last, because it matches every other address.
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")