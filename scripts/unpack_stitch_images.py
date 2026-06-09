"""
Stitch ZIP'lerinden persona PNG'lerini çıkarıp demo/assets/personas/'a kopyalar.
Çalıştır: python scripts/unpack_stitch_images.py
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from persona_math.persona_library import PERSONA_LIBRARY

REPO_ROOT = Path(__file__).parent.parent
OUT_DIR = REPO_ROOT / "demo/assets/personas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

lib_ids = set(PERSONA_LIBRARY)

# Manual overrides: folder stem prefix → persona_id
# (for cases where auto-matching fails due to aliases, encoding, or compound names)
MANUAL = {
    "achilles_ancient": "achilles_char",
    "achilles_the": "achilles_char",
    "achilles": "achilles_char",
    "albertus_magnus": "albert_the_great",
    "carl_gustav_jung": "carl_jung",
    "data_star_trek": "data_android",       # if exists; will be skipped if not
    "edmond_dant": "edmond_dantes",          # covers edmond_dant_s (é encoding)
    "frankenstein_s_monster": "frankenstein_monster",
    "george_orwell": "george_orwell_writer",
    "gottfried_wilhelm_leibniz": "leibniz",
    "gotthold_ephraim_lessing": "gotthold_lessing",
    "harry_s": "harry_truman",               # covers harry_s._truman
    "henry_v_medieval": "henry_v_england",
    "henry_v_": "henry_v_england",
    "hercule_poirot": "hercule_poirot",      # may not exist, will be skipped
    "johann_sebastian_bach": "bach",
    "ludwig_van_beethoven": "beethoven",
    "medea_ancient": "medea_char",
    "medea_": "medea_char",
    "morpheus_stoic": "morpheus_matrix",
    "niccol": "niccolo_paganini",            # covers niccol_paganini (ò encoding)
    "octavia_e": "octavia_butler",
    "odysseus_strategic": "odysseus_char",
    "odysseus_": "odysseus_char",
    "pompey_the_great": "pompey_magnus",
    "prometheus_defiant": "prometheus_myth",
    "prometheus_": "prometheus_myth",
    "quetzalc": "quetzalcoatl",              # covers quetzalc_atl (encoding)
    "richard_i_lionheart": "richard_lionheart",
    "richard_i_": "richard_lionheart",
    "salvador_dal": "salvador_dali",         # covers salvador_dal_ (í encoding)
    "sherlock_holmes": "sherlock_holmes_char",
    "siddhartha_gautama": "buddha",
    "sir_john_falstaff": "falstaff",
    "timon_of_phlius": "timon_of_phlius",    # may not exist, will be skipped
    "pyrrhus_of_epirus": "pyrrhus_of_epirus",  # may not exist, will be skipped
    "wolfg": "mozart",                        # covers wolfgang_amadeus_mozart
    "yuval_noah_harari": "yuval_harari",
}


def find_persona_id(stem: str) -> str | None:
    """Match a folder stem to a persona_id."""
    # 1. Check manual overrides by prefix
    for prefix, pid in MANUAL.items():
        if stem.startswith(prefix):
            return pid if pid in lib_ids else None

    # 2. Try progressively shorter underscore-split prefixes
    words = stem.split("_")
    for n in range(len(words), 0, -1):
        candidate = "_".join(words[:n])
        if candidate in lib_ids:
            return candidate

    # 3. Try after stripping dots (b.f. → bf)
    norm = re.sub(r"[^a-z0-9_]", "", stem.replace(".", ""))
    words2 = [w for w in norm.split("_") if w]
    for n in range(len(words2), 0, -1):
        candidate = "_".join(words2[:n])
        if candidate in lib_ids:
            return candidate

    return None


def extract_stem(zip_entry: str) -> str | None:
    """Pull the meaningful name out of a ZIP entry path."""
    parts = zip_entry.rstrip("/").split("/")
    folder = parts[-2] if len(parts) >= 2 else parts[0]
    prefix = "digital_portrait_of_"
    if folder.startswith(prefix):
        return folder[len(prefix):]
    return None


matched, skipped_generic, unmatched = [], [], []

for zip_path in sorted(REPO_ROOT.glob("stitch_iconic_figures_part_*.zip")):
    with zipfile.ZipFile(zip_path) as zf:
        for entry in zf.namelist():
            if not entry.lower().endswith("/screen.png"):
                continue
            stem = extract_stem(entry)
            if stem is None:
                continue

            # Skip obviously generic descriptions
            if stem.startswith(("a_dark_", "a_stern_", "a_wise_", "a_", "an_")):
                skipped_generic.append((zip_path.name, stem))
                continue

            pid = find_persona_id(stem)
            if pid is None:
                unmatched.append((zip_path.name, stem))
                continue

            dest = OUT_DIR / f"{pid}.png"
            if not dest.exists():
                with zf.open(entry) as src:
                    shutil.copyfileobj(src, dest.open("wb"))
            matched.append(pid)

print(f"Copied  : {len(matched)}")
print(f"Generic : {len(skipped_generic)}")
print(f"Unmatched ({len(unmatched)}):")
for z, s in sorted(unmatched):
    print(f"   {z}  →  {s}")
