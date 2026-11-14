# targets.py
# The 5 test targets, with positions checked against SIMBAD
# (Harvard mirror, queried on 2026-11-11).
#
# ra_deg / dec_deg : position in degrees at epoch J2000 (the year 2000)
# pmra_mas_yr      : proper motion in RA, milliarcseconds per year
#                    (SIMBAD's pmra already includes the cos(Dec) factor)
# pmdec_mas_yr     : proper motion in Dec, milliarcseconds per year
#
# This file only holds data and one tiny helper. It never downloads anything.

import math

TARGETS = {
    "wise0855": {
        "label": "WISE 0855",
        "simbad_name": "WISEA J085510.74-071442.5",
        "ra_deg": 133.81890825,
        "dec_deg": -7.247048,
        "pmra_mas_yr": -8123.7,
        "pmdec_mas_yr": 673.2,
        "note": "Very fast mover, extremely faint.",
    },
    "barnard": {
        "label": "Barnard's Star",
        "simbad_name": "NAME Barnard's star",
        "ra_deg": 269.4520769586187,
        "dec_deg": 4.693364966576667,
        "pmra_mas_yr": -801.551,
        "pmdec_mas_yr": 10362.394,
        "note": "Bright, fast proper motion (about 10 arcsec/year).",
    },
    "epsindib": {
        "label": "Epsilon Indi B",
        "simbad_name": "* eps Ind B",
        "ra_deg": 331.04414658852124,
        "dec_deg": -56.782844195116105,
        "pmra_mas_yr": 3981.977,
        "pmdec_mas_yr": -2466.832,
        "note": "Brown dwarf pair, about 6.7 arcmin from the bright star "
                "Eps Ind A. Use a wide field of view to see both.",
    },
    "rwaur": {
        "label": "RW Aurigae",
        "simbad_name": "V* RW Aur",
        "ra_deg": 76.95652603458333,
        "dec_deg": 30.401438173888888,
        "pmra_mas_yr": 7.23,
        "pmdec_mas_yr": -20.33,
        "note": "Variable star. Tests brightness changes, not motion.",
    },
    "rdra": {
        "label": "R Draconis",
        "simbad_name": "V* R Dra",
        "ra_deg": 248.16761083295,
        "dec_deg": 66.75497941722,
        "pmra_mas_yr": -20.643,
        "pmdec_mas_yr": 6.149,
        "note": "Mira-type variable. Brightness changes by a lot.",
    },
}


def position_at_epoch(target_id, year):
    """Return (ra_deg, dec_deg) of a target in a given year, e.g. 2026.0.

    Simple straight-line motion from the year 2000. This is good enough
    for choosing where to cut an image. It ignores parallax and other
    small effects.
    """
    t = TARGETS[target_id]
    years = year - 2000.0
    # mas/yr -> degrees: divide by 3,600,000 (3600 arcsec * 1000 mas)
    d_dec = t["pmdec_mas_yr"] * years / 3_600_000
    # pmra already includes cos(Dec), so divide it out to get a change in RA
    d_ra = t["pmra_mas_yr"] * years / 3_600_000 / math.cos(math.radians(t["dec_deg"]))
    return t["ra_deg"] + d_ra, t["dec_deg"] + d_dec


if __name__ == "__main__":
    # Quick self-test: run  python targets.py
    for tid, t in TARGETS.items():
        ra, dec = position_at_epoch(tid, 2026.0)
        print(f"{t['label']:16s} J2000: {t['ra_deg']:.5f} {t['dec_deg']:+.5f}"
              f"   2026.0: {ra:.5f} {dec:+.5f}")