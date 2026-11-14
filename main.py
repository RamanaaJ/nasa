# main.py
# The web server (FastAPI). Start it with:   uvicorn main:app --reload
# Then open  http://127.0.0.1:8000/docs  to try the endpoints in your browser.
#
# Backend 9 gives it three jobs:
#   GET /api/frames?ra=..&dec=..&fov=..   list of frames (JSON) with image links
#   GET /api/frames/{index}/image?...     one frame as a PNG picture
#   everything else                       files from the static/ folder
#
# main.py only connects the other files. The real work is done elsewhere:
#   data_mock.py -> frames,  cache.py -> saves them,  processing.py -> PNG.

from pathlib import Path
from urllib.parse import urlencode

import numpy as np
from astropy.wcs.utils import proj_plane_pixel_scales
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

import cache
import config
import data_mock
import processing

app = FastAPI(title="SPHEREx Sky Viewer")

STATIC_DIR = Path(__file__).parent / "static"


def frames_for(ra, dec, fov):
    """Get the frames for one request: from the cache, or from the data source."""
    if not config.USE_MOCK:
        # data_irsa.py does not exist yet (TODO Backend 25)
        raise HTTPException(
            status_code=501,
            detail="Real SPHEREx data is not connected yet. Set USE_MOCK = True in config.py.")
    try:
        frames = cache.get_or_load(ra, dec, fov, data_mock.get_frames)
    except FileNotFoundError as err:        # mock files were never created
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:               # e.g. bad field of view
        raise HTTPException(status_code=400, detail=str(err))
    if not frames:
        raise HTTPException(status_code=404, detail="No images cover this sky position.")
    return frames


def check_stretch(stretch):
    if stretch not in processing.STRETCH_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stretch '{stretch}'. Use one of {list(processing.STRETCH_MODES)}.")


def describe_frame(index, frame, ra, dec, fov, stretch):
    """Turn one frame into a small dictionary that can be sent as JSON."""
    height, width = frame["image"].shape
    wcs = frame["wcs"]

    # Pixel scale: how many arcseconds one pixel covers (mean of the two axes)
    pixel_scale_arcsec = float(np.mean(proj_plane_pixel_scales(wcs))) * 3600.0
    # Sky position of the middle of this cutout (pixel numbers start at 0)
    centre_ra, centre_dec = wcs.pixel_to_world_values((width - 1) / 2, (height - 1) / 2)

    query = urlencode({"ra": ra, "dec": dec, "fov": fov, "stretch": stretch})
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
    ra: float = Query(..., ge=0, le=360, description="Right ascension in degrees"),
    dec: float = Query(..., ge=-90, le=90, description="Declination in degrees"),
    fov: float = Query(config.DEFAULT_FOV_ARCMIN, ge=config.MIN_FOV_ARCMIN,
                       le=config.MAX_FOV_ARCMIN, description="Field of view in arcminutes"),
    stretch: str = Query("sqrt", description="linear, sqrt or log (used in the image links)"),
):
    """The frame list: one entry per image, sorted by date."""
    check_stretch(stretch)
    frames = frames_for(ra, dec, fov)
    return {
        "source": cache.current_release(),
        "ra_deg": ra,
        "dec_deg": dec,
        "fov_arcmin": fov,
        "stretch": stretch,
        "frame_count": len(frames),
        "frames": [describe_frame(i, f, ra, dec, fov, stretch) for i, f in enumerate(frames)],
    }


@app.get("/api/frames/{index}/image")
def frame_image(
    index: int,
    ra: float = Query(..., ge=0, le=360),
    dec: float = Query(..., ge=-90, le=90),
    fov: float = Query(config.DEFAULT_FOV_ARCMIN, ge=config.MIN_FOV_ARCMIN,
                       le=config.MAX_FOV_ARCMIN),
    stretch: str = Query("sqrt"),
):
    """One frame as a PNG picture. `index` is the number from the frame list."""
    check_stretch(stretch)
    frames = frames_for(ra, dec, fov)           # instant when it is already cached
    if index < 0 or index >= len(frames):
        raise HTTPException(status_code=404,
                            detail=f"There is no frame {index}. This request has {len(frames)} frames.")
    grey = processing.stretch_image(frames[index]["image"], mode=stretch)
    return Response(content=processing.image_to_png_bytes(grey), media_type="image/png")


# Serve the web page files. This MUST stay last, because it matches every other address.
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")