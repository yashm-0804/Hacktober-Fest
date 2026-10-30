"""Deterministic safety checks (SAFE-1..4). No LLM calls.

A "resolved med" is: {"label": str, "salts": [{"salt": str, "strength": str}], "freq": str}
  (may also carry "price" (pack price, ₹) and "pack" (e.g. "strip of 15 tablets"))
An alert is: {"severity": "HIGH"|"REVIEW"|"INFO", "type": "DUPLICATE"|"ALLERGY"|"CROSS_REACTIVITY"|"LASA",
              "title": str, "detail": str, "meds": [int]}   # indices into the meds list
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from core.match import norm_salt, parse_strength, salt_key, same_strength

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _allergy_data() -> dict:
    return json.loads((ROOT / "data" / "allergy_classes.json").read_text())


@lru_cache(maxsize=1)
def _jan_data() -> dict:
    return json.loads((ROOT / "data" / "jan_aushadhi.json").read_text())


def _salts(med: dict) -> list[tuple[str, str]]:
    return [(norm_salt(s.get("salt", "")), (s.get("strength") or "").strip())
            for s in (med or {}).get("salts", []) if s.get("salt")]


def _fmt_mg(v: float) -> str:
    return f"{int(v)}" if v == int(v) else f"{v:g}"


def _has_word(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) is not None


# ---------------------------------------------------------------- SAFE-1
def duplicates(meds: list[dict]) -> list[dict]:
    """Same salt in 2+ meds -> HIGH DUPLICATE, with the combined per-dose mg when parseable."""
    seen: dict[str, list[tuple[int, str]]] = {}
    for i, med in enumerate(meds or []):
        for salt, strength in _salts(med):
            entries = seen.setdefault(salt, [])
            if all(j != i for j, _ in entries):
                entries.append((i, strength))
    alerts = []
    for salt, entries in seen.items():
        if len(entries) < 2:
            continue
        idx = [i for i, _ in entries]
        parts = [f"{meds[i].get('label', f'medicine {i + 1}')} ({st or 'strength unknown'})" for i, st in entries]
        detail = f"{salt.capitalize()} in " + ", ".join(parts[:-1]) + f" and {parts[-1]}"
        parsed = [parse_strength(st) for _, st in entries]
        if all(p and p[1] == "mg" for p in parsed):
            detail += f" = {_fmt_mg(sum(p[0] for p in parsed))} mg per combined dose"
        detail += ". Taking these together doubles up the same medicine; ask your doctor which one to keep."
        alerts.append({"severity": "HIGH", "type": "DUPLICATE",
                       "title": f"Duplicate {salt} in {len(idx)} medicines",
                       "detail": detail, "meds": idx})
    return alerts


def _allergy_profile(allergies: list[str]) -> tuple[set[str], dict[str, str]]:
    """-> (allergic classes, {directly named salt: original allergy text})."""
    data = _allergy_data()["classes"]
    classes, named = set(), {}
    for raw in allergies or []:
        text = norm_salt(str(raw))
        if not text:
            continue
        for cls, spec in data.items():
            if any(_has_word(text, w) for w in [cls, *spec.get("aliases", [])]):
                classes.add(cls)
            for kw in spec.get("salts", []) + spec.get("caution_salts", []):
                kw_n = norm_salt(kw)
                if kw_n != cls and _has_word(text, kw_n):
                    named[kw_n] = str(raw)
        # any other free-text salt name, e.g. "metformin"
        if len(text) >= 4 and not any(_has_word(text, c) for c in classes):
            named.setdefault(text, str(raw))
    return classes, named


def _class_of(salt: str) -> list[tuple[str, bool]]:
    """-> [(class, is_caution)] whose keywords appear in the salt name."""
    out = []
    for cls, spec in _allergy_data()["classes"].items():
        if any(_has_word(salt, norm_salt(k)) for k in spec.get("salts", [])):
            out.append((cls, False))
        elif any(_has_word(salt, norm_salt(k)) for k in spec.get("caution_salts", [])):
            out.append((cls, True))
    return out


def allergy(meds: list[dict], allergies: list[str]) -> list[dict]:
    """HIGH ALLERGY for a salt in an allergic class or a directly named salt; REVIEW for caution salts,
    same-class relatives of a named salt, and penicillin -> cephalosporin cross-reactivity."""
    data = _allergy_data()
    classes, named = _allergy_profile(allergies)
    if not classes and not named:
        return []
    # a directly named salt implies caution for the rest of its class
    named_classes = {cls: s for s in named for cls, caution in _class_of(s) if not caution}
    cross = [(c["allergy"], c["class"], c["note"]) for c in data.get("cross_reactivity", [])]
    alerts = []
    for i, med in enumerate(meds or []):
        label = med.get("label", f"medicine {i + 1}")
        for salt, _st in _salts(med):
            hit = None
            direct = next((s for s in named if s == salt or _has_word(salt, s)), None)
            memberships = _class_of(salt)
            if direct:
                hit = ("HIGH", "ALLERGY", f"Allergy: {label} contains {salt}",
                       f"You reported an allergy to '{named[direct]}'. {label} contains {salt}. Do not take it; ask your doctor for an alternative.")
            if not hit:
                for cls, caution in memberships:
                    if cls in classes:
                        lab = data["classes"][cls].get("label", cls)
                        if caution:
                            hit = ("REVIEW", "ALLERGY", f"Caution: {salt} with {lab} allergy",
                                   f"{label} contains {salt}, a non-antibiotic sulfonamide-type drug. Cross-reaction with a {lab} allergy is uncommon but possible; confirm with doctor.")
                        else:
                            hit = ("HIGH", "ALLERGY", f"{lab[0].upper() + lab[1:]} allergy: {label} contains {salt}",
                                   f"{salt.capitalize()} is in the {lab} group. You reported a {lab} allergy. Do not take it; ask your doctor for an alternative.")
                        break
            if not hit:
                for cls, caution in memberships:
                    if not caution and cls in named_classes:
                        lab = data["classes"][cls].get("label", cls)
                        hit = ("REVIEW", "CROSS_REACTIVITY", f"Same class as your {named_classes[cls]} allergy: {salt}",
                               f"{label} contains {salt}, which is in the same {lab} class as {named_classes[cls]}; confirm with doctor.")
                        break
            if not hit:
                allergic_to = classes | set(named_classes)
                for src, dst, note in cross:
                    if src in allergic_to and any(cls == dst and not c for cls, c in memberships):
                        hit = ("REVIEW", "CROSS_REACTIVITY", f"{src.capitalize()} allergy and {salt} ({dst})",
                               f"{label} contains {salt}, a {dst}. With a {src} allergy there is {note}.")
                        break
            if hit:
                sev, typ, title, detail = hit
                alerts.append({"severity": sev, "type": typ, "title": title, "detail": detail, "meds": [i]})
    return alerts


# ---------------------------------------------------------------- SAFE-2
def _describe(med: dict) -> str:
    return " + ".join(f"{s} {st}".strip() for s, st in _salts(med)) or "unknown composition"


def strip_check(strip: dict, meds: list[dict]) -> dict:
    """strip: {"label": str, "salts": [...]} (resolved strip). Returns {"status": "MATCH"|"MISMATCH"|"NOT_PRESCRIBED", "detail": str, "med_index": int | None}."""
    s_salts = dict(_salts(strip))
    if not s_salts:
        return {"status": "NOT_PRESCRIBED", "detail": "Could not identify the medicine on the strip.", "med_index": None}
    strip_desc = _describe(strip)
    best = None  # (rank, index, status, detail); lower rank is better
    for i, med in enumerate(meds or []):
        m_salts = dict(_salts(med))
        label = med.get("label", f"medicine {i + 1}")
        if set(m_salts) == set(s_salts):
            ok = all(not s_salts[s] or not m_salts[s] or same_strength(s_salts[s], m_salts[s]) for s in s_salts)
            if ok:
                cand = (0, i, "MATCH", f"Strip ({strip_desc}) matches prescribed {label} ({_describe(med)}).")
            else:
                cand = (1, i, "MISMATCH", f"Prescribed {label} ({_describe(med)}) but strip is {strip_desc}.")
        elif set(m_salts) & set(s_salts):
            cand = (2, i, "MISMATCH", f"Prescribed {label} ({_describe(med)}) but strip is {strip_desc}.")
        else:
            continue
        if best is None or cand[0] < best[0]:
            best = cand
    if best is None:
        return {"status": "NOT_PRESCRIBED",
                "detail": f"The strip ({strip_desc}) is not on this prescription. Check with your pharmacist or doctor.",
                "med_index": None}
    return {"status": best[2], "detail": best[3], "med_index": best[1]}


# ---------------------------------------------------------------- SAFE-3
def jan_aushadhi(med: dict) -> dict | None:
    """Returns {"generic_name": str, "price": float, "pack": str, "indicative": True, "source": str, "units": int} or None."""
    salts = _salts(med)
    if not salts:
        return None
    key = salt_key([{"salt": s} for s, _ in salts])
    strengths = dict(salts)
    data = _jan_data()
    for k, entry in data["entries"].items():
        ekey, estr = k.split("|")
        if ekey != key:
            continue
        exp = dict(zip(ekey.split("+"), estr.split("+")))
        if all(not strengths.get(s) or same_strength(strengths[s], exp[s]) for s in exp):
            return {"generic_name": entry["generic_name"], "price": float(entry["price"]), "pack": entry["pack"],
                    "indicative": True, "source": data["source"], "units": int(entry.get("units", 10))}
    return None


def pack_count(pack: str | None) -> int | None:
    """'strip of 15 tablets' -> 15; '10 tablets' -> 10; 'bottle of 60 ml' -> None (not unit doses)."""
    m = re.search(r"(\d+)\s*(tablets?|capsules?|tabs?|caps?|tablet|capsule)?", str(pack or ""), re.I)
    if not m or re.search(r"\d+\s*(ml|gm|g)\b", str(pack or ""), re.I):
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def monthly_savings(meds: list[dict], brand_prices: list[float | None]) -> float:
    """₹ saved over 30 days by switching each med to its Jan Aushadhi generic.

    Brand per-unit price = med["price"] / pack_count(med["pack"]) when available; otherwise
    brand_prices[i] (divided by the pack count when the med has a pack, else taken as per-unit).
    Units/day = len(schedule(med["freq"])) or 1.
    """
    total = 0.0
    prices = list(brand_prices or [])
    for i, med in enumerate(meds or []):
        generic = jan_aushadhi(med)
        if not generic:
            continue
        count = pack_count(med.get("pack"))
        price = med.get("price")
        if price in (None, "") and i < len(prices):
            price = prices[i]
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        brand_unit = price / count if count else price
        generic_unit = generic["price"] / generic["units"]
        per_day = len(schedule(med.get("freq") or "")) or 1
        diff = brand_unit - generic_unit
        if diff > 0:
            total += diff * per_day * 30
    return round(total, 2)


# ---------------------------------------------------------------- SAFE-4
_SCHEDULES = [
    (r"qid|qds|four times", ["Morning", "Afternoon", "Evening", "Night"]),
    (r"tds|tid|thrice|three times", ["Morning", "Afternoon", "Night"]),
    (r"bd|bid|twice", ["Morning", "Night"]),
    (r"od|qd|once daily|once a day", ["Morning"]),
    (r"hs|at bedtime|bedtime", ["Bedtime"]),
    (r"sos|prn|as needed", ["As needed"]),
]


def schedule(freq: str) -> list[str]:
    """e.g. "TDS" -> ["Morning", "Afternoon", "Night"]; unknown -> []."""
    f = str(freq or "").lower()
    if not f.strip():
        return []
    m = re.search(r"\b([0-2])\s*-\s*([0-2])\s*-\s*([0-2])\b", f)  # Indian "1-0-1" notation
    if m:
        slots = [s for s, n in zip(["Morning", "Afternoon", "Night"], m.groups()) if n != "0"]
        if slots:
            return slots
    for pat, slots in _SCHEDULES:
        if re.search(r"\b(" + pat + r")\b", f):
            return list(slots)
    return []
