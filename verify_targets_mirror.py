# verify_targets_mirror.py
# Asks a SIMBAD MIRROR (because Strasbourg is down) for the exact
# position and proper motion of our 5 targets. It changes no other file.

import pyvo

# Mirror addresses come from the CDS homepage notice.
MIRRORS = [
    "https://simbad.cfa.harvard.edu/simbad/sim-tap/",   # Harvard
    "https://simbad.idia.ac.za/simbad/sim-tap/",        # South Africa
]

# Names to try for each target (SIMBAD may know them under any of these).
TARGET_NAMES = {
    "WISE 0855":      ["WISE J085510.83-071442.5", "WISE 0855-0714"],
    "Barnard's Star": ["Barnard's star", "GJ 699"],
    "Epsilon Indi B": ["eps Ind B", "eps Ind Ba", "eps Ind"],
    "RW Aurigae":     ["RW Aur"],
    "R Draconis":     ["R Dra"],
}

def connect():
    """Return the first mirror that answers."""
    for url in MIRRORS:
        try:
            service = pyvo.dal.TAPService(url)
            service.run_sync("SELECT TOP 1 main_id FROM basic")  # tiny test query
            print("Connected to:", url, "\n")
            return service
        except Exception as err:
            print("Mirror failed:", url, "->", err)
    return None

service = connect()
if service is None:
    print("No mirror answered. Use the manual browser route instead.")
    raise SystemExit

for label, names in TARGET_NAMES.items():
    print("=" * 60)
    print(label)
    found = False
    for name in names:
        safe = name.replace("'", "''")          # ADQL needs ' doubled
        query = (
            "SELECT main_id, ra, dec, pmra, pmdec "
            "FROM basic JOIN ident ON oidref = oid "
            f"WHERE id = '{safe}'"
        )
        try:
            result = service.run_sync(query).to_table()
        except Exception as err:
            print(f"  '{name}': query failed ({err})")
            continue
        if len(result) == 0:
            print(f"  '{name}': no match")
            continue
        print(f"  '{name}': match found")
        print(result)
        found = True
        break
    if not found:
        print("  NOT FOUND under any name.")