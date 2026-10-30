"""Safety Test Lab (TEST-1): 4 preset regimens built from REAL brands via match.candidates()."""
from __future__ import annotations

from core.match import candidates
from core.safety import allergy, duplicates


def _med(name: str, freq: str = "OD") -> dict:
    cands = candidates(name)
    if not cands:
        return {"label": name, "salts": [], "freq": freq}
    c = cands[0]
    return {"label": c["name"], "salts": c["salts"], "freq": freq, "price": c["price"], "pack": c["pack"]}


def _alerts(meds: list[dict], allergies: list[str]) -> list[dict]:
    return duplicates(meds) + allergy(meds, allergies)


def _summary(alerts: list[dict]) -> str:
    if not alerts:
        return "no DUPLICATE/ALLERGY alerts"
    return "; ".join(f"{a['severity']} {a['type']}: {a['title']}" for a in alerts)


CASES = [
    {"case": "Fever: Dolo 650 + Combiflam", "brands": [("Dolo 650", "TDS"), ("Combiflam", "BD")], "allergies": [],
     "expected": "HIGH DUPLICATE paracetamol",
     "check": lambda al: any(a["type"] == "DUPLICATE" and "paracetamol" in a["title"].lower() for a in al)},
    {"case": "Augmentin 625 Duo + penicillin allergy", "brands": [("Augmentin 625 Duo", "BD")], "allergies": ["penicillin"],
     "expected": "HIGH ALLERGY (amoxicillin is a penicillin)",
     "check": lambda al: any(a["type"] == "ALLERGY" and a["severity"] == "HIGH" for a in al)},
    {"case": "Telma H + sulfa allergy", "brands": [("Telma H", "OD")], "allergies": ["sulfa"],
     "expected": "ALLERGY caution (hydrochlorothiazide)",
     "check": lambda al: any(a["type"] == "ALLERGY" and "hydrochlorothiazide" in a["title"].lower() for a in al)},
    {"case": "Clean: Atorva 20 + Ecosprin 75 + Glycomet-GP 1", "brands": [("Atorva 20", "HS"), ("Ecosprin 75", "OD"), ("Glycomet-GP 1", "BD")],
     "allergies": [], "expected": "no DUPLICATE/ALLERGY alerts",
     "check": lambda al: not any(a["type"] in ("DUPLICATE", "ALLERGY") for a in al)},
]


def run_cases() -> list[dict]:
    """-> [{"case", "expected", "got", "passed"}] for the 4 preset cases."""
    results = []
    for c in CASES:
        try:
            meds = [_med(n, f) for n, f in c["brands"]]
            al = _alerts(meds, c["allergies"])
            got = f"[{', '.join(m['label'] for m in meds)}] → {_summary(al)}"
            passed = bool(c["check"](al))
        except Exception as e:  # a crash is a failed case, not a crashed page
            got, passed = f"error: {e}", False
        results.append({"case": c["case"], "expected": c["expected"], "got": got, "passed": passed})
    return results
