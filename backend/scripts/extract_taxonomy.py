"""Extract controlled vocabularies (countries, sector/sub-sector taxonomy) from the
DEP extraction protocol workbook's 'Lists' sheet into a JSON file the scorer/prompt
builder can load without needing pandas/openpyxl at request time.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "docs" / "DEP extraction protocol for IE v4- Admin panel.xlsx"
OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "taxonomy.json"

# Corrections applied on top of the workbook. The workbook is the authoritative
# source, so anything here is a defect in it that we cannot fix at source, and
# each entry should be deleted once DEP corrects the protocol.
#
#   "Housing contruction" -- misspelt in the Lists sheet (verified: the typo
#   appears once in the workbook XML and the correct spelling not at all). The
#   reference database spells it correctly in 12 records, so leaving the typo in
#   the option list made those 12 unscoreable and made propose_gt_fixes offer to
#   rewrite them ONTO the typo.
OPTION_CORRECTIONS = {
    "Housing contruction": "Housing construction",
}

df = pd.ExcelFile(XLSX).parse("Lists", header=None)
header = df.iloc[2].tolist()

countries = [v for v in df.iloc[3:, 2].tolist() if isinstance(v, str) and v.strip()]

# WB_Sectors block starts at the column labeled "WB_Sectors"; the following 11
# columns (one per sector) each contain that sector's sub-sector list underneath it.
sector_col = header.index("WB_Sectors")
sector_names = [h.strip("_").replace("_", " ") for h in header[sector_col + 1: sector_col + 12]]
sub_sectors = {}
for offset, name in enumerate(sector_names):
    col = sector_col + 1 + offset
    values = [v for v in df.iloc[3:, col].tolist() if isinstance(v, str) and v.strip()]
    sub_sectors[name] = [OPTION_CORRECTIONS.get(v, v) for v in values]

taxonomy = {
    "countries": countries,
    "sectors": sector_names,
    "sub_sectors_by_sector": sub_sectors,
}

# Keys this script does not derive must survive a regeneration. `sector_definitions`
# is hand-maintained and prompts.py feeds it into the sector_name options block, so
# overwriting the file without it silently degrades the production prompt.
if OUT.exists():
    existing = json.loads(OUT.read_text(encoding='utf-8'))
    for key, value in existing.items():
        if key not in taxonomy:
            taxonomy[key] = value
            print(f'  preserved hand-maintained key: {key}')

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"  countries: {len(countries)}")
print(f"  sectors: {sector_names}")
for k, v in sub_sectors.items():
    print(f"  {k}: {len(v)} sub-sectors")
