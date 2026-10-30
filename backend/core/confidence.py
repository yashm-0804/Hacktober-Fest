"""Confidence scoring for one read medicine (DATA-3). Deterministic; no LLM calls."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from core.match import _alpha, _match_key, normalise_query, numbers

LASA_WINDOW = 12.0  # a different-salt candidate within this many points is a look-alike rival


def _salt_names(c: dict) -> str:
    return c.get("salt_key") or "+".join(s.get("salt", "") for s in c.get("salts", []))


def _name_only(text: str | None) -> str:
    """Brand letters only: form words, digits and strength units stripped ("Dolo 650 Tablet" -> "dolo")."""
    return _alpha(_match_key(normalise_query(text or "")))


def _name_sim(query: str, cand: dict) -> float:
    """Name-only similarity of the read text to a candidate, so a shared "650" can't make a look-alike."""
    other = _name_only(cand.get("base_name") or cand.get("name"))
    if not query or not other:
        return 0.0
    # Plain edit similarity: WRatio's partial matching made "Doloral P" a look-alike of "Dolo" (substring).
    return float(fuzz.ratio(query, other))


def _band(v: float) -> str:
    return "HIGH" if v >= 0.85 else "MEDIUM" if v >= 0.6 else "LOW"


def score(read: dict, cands: list[dict], fit: str | None = None) -> dict:
    """read: one item from llm.read_prescription()["medicines"] (keys: raw_text, brand_or_drug, strength, unsure, ...).
    cands: output of match.candidates(). fit: "yes" | "no" | "unclear" | None for cands[0].

    Returns {"value": float 0-1, "band": "HIGH"|"MEDIUM"|"LOW",
             "breakdown": {"match": float, "gap_penalty": float, "unsure_penalty": float,
                           "strength_penalty": float, "fit_adjust": float},
             "reasons": [str],            # human-readable, shown in UI
             "lasa_rival": dict | None}   # a different-salt look-alike candidate, if any
    """
    read = read or {}
    bd = {"match": 0.0, "gap_penalty": 0.0, "unsure_penalty": 0.0, "strength_penalty": 0.0, "fit_adjust": 0.0}
    if not cands:
        return {"value": 0.0, "band": "LOW", "breakdown": bd,
                "reasons": ["No matching brand found in the medicine database — a doctor must confirm."],
                "lasa_rival": None}

    top = cands[0]
    reasons = []
    bd["match"] = float(top.get("score", 0)) / 100
    reasons.append(f"Best match: {top.get('name')} ({_salt_names(top)}) — name match {top.get('score', 0):.0f}/100")

    unsure = bool(read.get("unsure"))
    if unsure:
        bd["unsure_penalty"] = -0.2
        reasons.append("The handwriting reader marked this item as unsure (−0.20)")

    read_strength = read.get("strength") or ""
    want = numbers(read_strength)
    if want:
        have = numbers(top.get("name")).union(*(numbers(s.get("strength")) for s in top.get("salts", [])))
        if not want <= have:
            bd["strength_penalty"] = -0.15
            strengths = ", ".join(s.get("strength", "") for s in top.get("salts", []) if s.get("strength")) or "none listed"
            reasons.append(f"Read strength '{read_strength}' is not in {top.get('name')} ({strengths}) (−0.15)")

    fit = (fit or "").lower() or None
    if fit == "yes":
        bd["fit_adjust"] = 0.1
        reasons.append("Fits the patient's condition (+0.10)")
    elif fit == "no":
        bd["fit_adjust"] = -0.2
        reasons.append("Does not fit the patient's condition (−0.20)")

    # LASA: closest different-salt candidate within the window
    # A rival must be close on the fuzzy score AND on name-only similarity (digits/strength stripped
    # from both sides), so "Dolo 650" vs "Spirodin 650" is not a look-alike just because of "650".
    rival = None
    top_key, top_score = top.get("salt_key"), float(top.get("score", 0))
    written_name = re.sub(r"\([^)]*\)", " ", read.get("brand_or_drug") or read.get("raw_text") or "")  # drop "(Lorazepam)"
    query = _name_only(written_name) or _name_only(top.get("base_name") or top.get("name"))
    top_sim = _name_sim(query, top)
    for c in cands[1:]:
        if c.get("salt_key") == top_key or top_score - float(c.get("score", 0)) > LASA_WINDOW:
            continue
        if top_sim - _name_sim(query, c) <= LASA_WINDOW:
            rival = c
            break
    if rival:
        bd["gap_penalty"] = -0.15
        gap = top_score - float(rival.get("score", 0))
        reasons.append(f"Look-alike: {top.get('name')} ({_salt_names(top)}) vs {rival.get('name')} "
                       f"({_salt_names(rival)}) — {gap:.0f} points apart (−0.15, capped at MEDIUM)")

    value = max(0.0, min(1.0, sum(bd.values())))
    band = _band(value)
    if band == "HIGH" and bd["fit_adjust"] > 0 and _band(value - bd["fit_adjust"]) != "HIGH":
        band = "MEDIUM"  # a model's "fits" may confirm, never promote: HIGH must stand on the reading alone

    # Written-name check: fuzzy scores reward one shared word ("B-plex fort" ~ "B Cillin CV Forte", an
    # antibiotic). HIGH needs the brand as written to look like the match's brand (its leading letters).
    top_alpha = _name_only(top.get("base_name") or top.get("name"))
    written = max(fuzz.ratio(query, top_alpha[:len(query) + 2]), fuzz.ratio(query, top_alpha)) if query else 0.0
    if written < 65:
        band = "LOW"
        reasons.append(f"What was read ('{read.get('brand_or_drug')}') does not look like {top.get('name')} "
                       f"({written:.0f}/100) — sent to a doctor (LOW)")
    elif written < 80 and band == "HIGH":
        band = "MEDIUM"
        reasons.append(f"What was read only partly looks like {top.get('name')} ({written:.0f}/100) — please confirm")
    if rival:
        if fit == "no" or unsure:
            band = "LOW"
            reasons.append("Look-alike plus " + ("a poor condition fit" if fit == "no" else "an unsure read")
                           + " — sent to a doctor (LOW)")
        elif band == "HIGH":
            band = "MEDIUM"
    return {"value": round(value, 3), "band": band, "breakdown": bd, "reasons": reasons, "lasa_rival": rival,
            "written_similarity": round(written / 100, 2)}
