# try_real_query.py
# Backend 26: ONE real query by hand, for WISE 0855. Not part of the server.
# It follows IRSA's "Download a collection of SPHEREx Spectral Image cutouts"
# tutorial: a TAP query for the images covering a position, then cutout downloads.
#
# Needs the internet and astroquery (already in requirements.txt).
# The query can take 10-30 seconds. Run it with:  python try_real_query.py
# It writes docs/real_query_report.txt and cache/test_png/real_first_cutout.png.

import http.client
import time
import urllib.error
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.utils.data import conf
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astroquery.ipac.irsa import Irsa

import processing
import targets
import pyvo
from astropy.table import Table

conf.remote_timeout = 120     # the tutorial raises astropy's default timeout this way

TARGET_ID = "wise0855"
FOV_ARCMIN = 6.0
N_DOWNLOADS = 3               # how many cutouts to download
REPORT = Path(__file__).parent / "docs" / "real_query_report.txt"
OUT_PNG = Path(__file__).parent / "cache" / "test_png" / "real_first_cutout.png"

lines = []


def say(text=""):
    """Print a line and remember it for the report file."""
    print(text)
    lines.append(str(text))


def open_with_retries(url, tries=3):
    """Download one cutout into memory. Retries the transient errors the tutorial mentions."""
    for attempt in range(tries):
        try:
            with fits.open(url, memmap=False, cache=False) as hdul:
                for hdu in hdul:
                    hdu.data                      # read every extension before the file closes
            return hdul
        except (TimeoutError, urllib.error.HTTPError, http.client.IncompleteRead,
                http.client.RemoteDisconnected) as err:
            say(f"   transient error ({type(err).__name__}), try {attempt + 1} of {tries}")
            if attempt == tries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def describe(hdul, coord, full):
    """Print what is inside one cutout. full=True prints every detail."""
    header = hdul["IMAGE"].header
    data = hdul["IMAGE"].data
    spatial = WCS(header)
    x, y = spatial.world_to_pixel(coord)
    scale = float(np.mean(proj_plane_pixel_scales(spatial))) * 3600
    text = (f"shape {data.shape}, DETECTOR={header.get('DETECTOR')}, BUNIT={header.get('BUNIT')}, "
            f"pixel scale {scale:.2f} arcsec, target at pixel ({float(x):.1f}, {float(y):.1f})")
    try:
        spectral = WCS(header, fobj=hdul, key="W")
        spectral.sip = None                       # the tutorial turns SIP off for this WCS
        wavelength, _bandwidth = spectral.pixel_to_world(x, y)
        text += f", wavelength {wavelength.to(u.um).value:.4f} um"
    except Exception as err:
        text += f", wavelength FAILED ({type(err).__name__}: {err})"
    say("   " + text)
    if not full:
        return

    say("   --- full details of this first cutout ---")
    for item in hdul.info(output=False):
        say("   extension: " + str(item))
    finite = np.isfinite(data)
    say(f"   IMAGE: {100 * (1 - finite.mean()):.1f}% NaN, "
        f"min {np.nanmin(data):.4g}, median {np.nanmedian(data):.4g}, max {np.nanmax(data):.4g}")
    say("   header cards whose name has DATE, MJD, TIME, OBS or VERSION in it:")
    for name, hdr in (("PRIMARY", hdul[0].header), ("IMAGE", header)):
        for key in hdr:
            if any(s in key.upper() for s in ("DATE", "MJD", "TIME", "OBS", "VERSION")):
                say(f"      {name}: {key} = {hdr[key]!r}")
    try:
        flags_header = hdul["FLAGS"].header
        say("   flag bits (bit number, name, description):")
        for key in flags_header["MSKN*"]:
            bit = key[4:]
            say(f"      {int(bit):2d}  {flags_header[key]:<13} {flags_header.get('MSKD' + bit)}")
    except Exception as err:
        say(f"   could not read the flag table ({type(err).__name__}: {err})")

    grey = processing.stretch_image(np.array(data, dtype=float))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_PNG.write_bytes(processing.image_to_png_bytes(grey))
    say(f"   saved a picture of this cutout: {OUT_PNG}")

ROUTE = "sia"      # "sia" (fast, about a day behind) or "tap" (IRSA's TAP was too slow on 2026-11-15)


def search_sia(coord, size_deg):
    """The SIA search from IRSA's intro tutorial. Returns a table with the same
    3 columns as the TAP query, or None. Collection names are from the tutorial."""
    t0 = time.time()
    try:
        found = Irsa.query_sia(pos=(coord, 1 * u.arcsec), collection=["spherex_dr1", "spherex_qr3"])
    except Exception as err:
        say(f"   SIA FAILED after {time.time() - t0:.1f} s: {type(err).__name__}: {err}")
        return None
    say(f"   SIA answered in {time.time() - t0:.1f} s with {len(found)} images. Columns: {found.colnames}")
    if len(found) == 0:
        return None
    found.sort("t_min")
    ra, dec = coord.ra.deg, coord.dec.deg
    table = Table()
    # INFERENCE: the cutout link is the SIA link plus ?center=..&size=.. (see the tutorials' URLs)
    table["uri"] = [f"{url}?center={ra},{dec}d&size={size_deg}" for url in found["access_url"]]
    table["time_bounds_lower"] = found["t_min"]
    table["energy_bandpassname"] = found["energy_bandpassname"]
    return table


def run_query(query, coord, size_deg):
    """Returns a table with columns uri, time_bounds_lower, energy_bandpassname, or None."""
    if ROUTE == "sia":
        return search_sia(coord, size_deg)
    t0 = time.time()
    try:
        # One asynchronous TAP job (the address comes from IRSA's PSF tutorial).
        # Be patient: press Ctrl+C if it takes more than about 10 minutes.
        service = pyvo.dal.TAPService("https://irsa.ipac.caltech.edu/TAP")
        table = service.run_async(query).to_table()
        say(f"   async TAP worked after {time.time() - t0:.1f} s")
        return table
    except Exception as err:
        say(f"   async TAP FAILED after {time.time() - t0:.1f} s: {type(err).__name__}: {err}")
        return None

def main():
    ra, dec = targets.position_at_epoch(TARGET_ID, 2026.0)
    ra %= 360.0
    coord = SkyCoord(ra * u.deg, dec * u.deg)
    size_deg = FOV_ARCMIN / 60
    say(f"Target {TARGET_ID} at 2026.0: RA {ra:.6f}, Dec {dec:+.6f} degrees, cutout {FOV_ARCMIN} arcmin = {size_deg} deg")

    query = f"""
SELECT
    'https://irsa.ipac.caltech.edu/' || a.uri || '?center={ra},{dec}d&size={size_deg}' AS uri,
    p.time_bounds_lower,
    p.energy_bandpassname
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
ORDER BY p.time_bounds_lower
"""
    say("\nTAP query:" + query)
    t0 = time.time()
    table = run_query(query, coord, size_deg)
    if table is None:
        say("No result. Try again later, or send me this report.")
        return
    say(f"Query took {time.time() - t0:.1f} s and found {len(table)} images. Columns: {table.colnames}")
    if len(table) == 0:
        say("Nothing found.")
        return

    names, counts = np.unique(np.array(table["energy_bandpassname"]).astype(str), return_counts=True)
    say("Images per bandpass: " + ", ".join(f"{n}: {c}" for n, c in zip(names, counts)))
    for label, value in (("first", table["time_bounds_lower"][0]), ("last", table["time_bounds_lower"][-1])):
        say(f"time_bounds_lower, {label}: raw value {value!r}")
        try:
            say(f"      IF this is an MJD, it means {Time(float(value), format='mjd').isot}")
        except Exception as err:
            say(f"      could not read it as an MJD ({type(err).__name__})")
    say("First link: " + str(table["uri"][0]))

    for i in range(min(N_DOWNLOADS, len(table))):
        say(f"\nCutout {i}: {table['energy_bandpassname'][i]}")
        t0 = time.time()
        try:
            hdul = open_with_retries(str(table["uri"][i]))
        except Exception as err:
            say(f"   download FAILED: {type(err).__name__}: {err}")
            continue
        say(f"   downloaded in {time.time() - t0:.1f} s")
        describe(hdul, coord, full=(i == 0))


main()
REPORT.parent.mkdir(exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nReport saved to {REPORT}. Open the PNG and write what you see in docs/DATA_NOTES.md.")