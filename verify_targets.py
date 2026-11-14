# verify_targets.py
# One-off helper: asks SIMBAD for the exact position and proper motion
# of our 5 test targets, then prints them so we can copy them into targets.py.
# It does NOT change any other file.

from astroquery.simbad import Simbad

# Names SIMBAD should recognise. If one fails, we try the next one in its list.
# (These are my best guesses at SIMBAD names. The script will tell us which work.)
TARGET_NAMES = {
    "WISE 0855":      ["WISE J085510.83-071442.5", "WISE 0855-0714"],
    "Barnard's Star": ["Barnard's star", "GJ 699"],
    "Epsilon Indi B": ["eps Ind B", "eps Ind Ba", "eps Ind"],
    "RW Aurigae":     ["RW Aur"],
    "R Draconis":     ["R Dra"],
}

# Ask SIMBAD to also return proper motion (if this name is wrong, we print the error).
try:
    Simbad.add_votable_fields("pmra", "pmdec")
except Exception as err:
    print("Could not add proper-motion fields:", err)
    print("Continuing with the default columns only.\n")

for label, names in TARGET_NAMES.items():
    print("=" * 60)
    print(label)
    found = False
    for name in names:
        try:
            result = Simbad.query_object(name)
        except Exception as err:
            print(f"  '{name}': query failed ({err})")
            continue
        if result is None or len(result) == 0:
            print(f"  '{name}': no match")
            continue
        print(f"  '{name}': match found. Columns and values:")
        print(result)          # print the whole table so nothing is hidden
        found = True
        break                  # stop at the first name that works
    if not found:
        print("  NOT FOUND under any name. We will need to fix this by hand.")