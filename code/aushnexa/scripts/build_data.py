"""Build data/medicines.csv.gz from the junioralive/Indian-Medicine-Dataset (MIT).

Usage: python scripts/build_data.py [path/to/updated_indian_medicine_data.csv]
Source: https://github.com/junioralive/Indian-Medicine-Dataset
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT.parent / "_data_src" / "Indian-Medicine-Dataset" / "DATA" / "updated_indian_medicine_data.csv"
OUT = ROOT / "data" / "medicines.csv.gz"

# Dosage-form words stripped from brand names so "Dolo 650 Tablet" matches "Dolo 650".
FORM_WORDS = r"\b(tablets?|tab|capsules?|cap|syrup|syp|suspension|susp|oral|drops?|injection|inj|sachet|cream|gel|ointment|solution|spray|inhaler|powder|lotion|strip|dt|sr|er|xr|mr|cr|od|infusion|vial|respules|eye|ear|nasal|mouth ?wash|for|of)\b"

COMPONENT = re.compile(r"^\s*(.+?)\s*\(([^)]*)\)\s*$")


def parse_salts(*parts: str) -> list[dict]:
    salts = []
    for part in parts:
        if not isinstance(part, str) or not part.strip():
            continue
        for chunk in part.split("+"):
            m = COMPONENT.match(chunk)
            if m:
                salts.append({"salt": m.group(1).strip().lower(), "strength": m.group(2).strip().lower()})
            elif chunk.strip():
                salts.append({"salt": chunk.strip().lower(), "strength": ""})
    return salts


def base_name(name: str) -> str:
    s = re.sub(FORM_WORDS, " ", name.lower())
    return re.sub(r"\s+", " ", s).strip()


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    df = df[df["Is_discontinued"].str.upper() != "TRUE"]
    df = df[df["type"].str.lower() == "allopathy"]
    out = pd.DataFrame({
        "name": df["name"].str.strip(),
        "base_name": df["name"].map(base_name),
        "price": pd.to_numeric(df["price"], errors="coerce"),
        "pack": df["pack_size_label"],
        "manufacturer": df["manufacturer_name"],
        "salts": [json.dumps(parse_salts(a, b)) for a, b in zip(df["short_composition1"], df["short_composition2"])],
        "desc": df["medicine_desc"].str.slice(0, 300),
    })
    out = out[out["base_name"] != ""].drop_duplicates("name")
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False, compression="gzip")
    print(f"{len(out)} medicines -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
