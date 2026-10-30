"""Brand -> salt candidate matching over data/medicines.csv.gz (DATA-2).

Contract (fixed, other sections depend on it): see `candidates()`.
Also exports small salt/strength helpers reused by confidence.py and safety.py.
"""
from __future__ import annotations

import bisect
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "medicines.csv.gz"

# Same dosage-form words as scripts/build_data.py so queries normalise like base_name.
FORM_WORDS = r"\b(tablets?|tab|capsules?|cap|syrup|syp|suspension|susp|oral|drops?|injection|inj|sachet|cream|gel|ointment|solution|spray|inhaler|powder|lotion|strip|dt|sr|er|xr|mr|cr|od|infusion|vial|respules|eye|ear|nasal|mouth ?wash|for|of)\b"

# Spelling variants -> one canonical salt name.
SALT_SYNONYMS = {
    "amoxycillin": "amoxicillin",
    "acetaminophen": "paracetamol",
    "paracetamol ip": "paracetamol",
    "cephalexin": "cefalexin",
    "acetylsalicylic acid": "aspirin",
    "levocetrizine": "levocetirizine",
    "cetrizine": "cetirizine",
    "clavulanate": "clavulanic acid",
    "potassium clavulanate": "clavulanic acid",
    "sulphamethoxazole": "sulfamethoxazole",
    "sulphasalazine": "sulfasalazine",
    "frusemide": "furosemide",
    "glibenclamide": "glyburide",
    "albuterol": "salbutamol",
    "dicycloverine": "dicyclomine",
}

_NUM_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|µg|ug|gm|g|ml|iu|%)?", re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")


def normalise_query(name: str) -> str:
    """Lowercase and strip form words exactly like build_data.base_name."""
    s = re.sub(FORM_WORDS, " ", (name or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def norm_salt(salt: str) -> str:
    s = re.sub(r"\s+", " ", (salt or "").lower().strip())
    if s in SALT_SYNONYMS:
        return SALT_SYNONYMS[s]
    # word-level synonyms, e.g. "amoxycillin trihydrate" -> "amoxicillin trihydrate"
    words = [SALT_SYNONYMS.get(w, w) for w in s.split(" ")]
    return " ".join(words)


def salt_key(salts: list[dict]) -> str:
    return "+".join(sorted({norm_salt(s.get("salt", "")) for s in salts if s.get("salt")}))


def parse_strength(strength: str | None) -> tuple[float, str] | None:
    """'650mg' / '650 mg' -> (650.0, 'mg'); '1 g' -> (1000.0, 'mg'); unparseable -> None."""
    if not strength:
        return None
    m = _NUM_UNIT.search(str(strength))
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("g", "gm"):
        val, unit = val * 1000, "mg"
    elif unit in ("µg", "ug"):
        unit = "mcg"
    return (round(val, 4), unit)


def same_strength(a: str | None, b: str | None) -> bool:
    pa, pb = parse_strength(a), parse_strength(b)
    if pa is None or pb is None:
        return False
    if pa[0] != pb[0]:
        return False
    return pa[1] == pb[1] or not pa[1] or not pb[1]


def numbers(text: str | None) -> set[str]:
    """Numbers in a string, normalised ('650.0' -> '650')."""
    out = set()
    for n in _NUM.findall(str(text or "")):
        f = float(n)
        out.add(str(int(f)) if f == int(f) else str(f))
    return out


def _match_key(s: str) -> str:
    """base_name with punctuation flattened, so "glycomet-gp 1" matches "glycomet gp 1"."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9.%]+", " ", s.lower())).strip()


def _alpha(s: str) -> str:
    """Letters only, e.g. "glycomet gp 1 pr" -> "glycomet gp pr"; drops unit tokens like mg/ml."""
    words = [w for w in re.sub(r"[^a-z]+", " ", s).split() if w not in ("mg", "ml", "mcg", "gm", "g", "w", "v", "iu")]
    return " ".join(words)


@lru_cache(maxsize=1)
def _load():
    df = pd.read_csv(DATA, keep_default_na=False)
    df = df.assign(_key=df["base_name"].map(_match_key))
    df = df.assign(_len=df["_key"].str.len()).sort_values("_len", kind="stable").reset_index(drop=True)
    return {
        "names": df["name"].tolist(), "bases": df["base_name"].tolist(), "keys": df["_key"].tolist(),
        "lens": df["_len"].tolist(),
        "prices": pd.to_numeric(df["price"], errors="coerce").fillna(0.0).tolist(),
        "packs": df["pack"].tolist(), "descs": df["desc"].tolist(), "salts": df["salts"].tolist(),
    }


def _search(q: str, d: dict, limit: int) -> dict[int, float]:
    """WRatio over names not much shorter than the query (short names otherwise get a free
    partial-match 90, e.g. "om" inside "combiflam"). Returns {row index: score}."""
    lo = bisect.bisect_left(d["lens"], int(len(q) / 1.5 + 0.999))
    keys = d["keys"][lo:]
    if not keys:
        return {}
    # WRatio is symmetric; passing the names as cdist *rows* lets workers=-1 split them across cores
    sc = process.cdist(keys, [q], scorer=fuzz.WRatio, processor=None, dtype=np.float32, workers=-1)[:, 0]
    top = np.argpartition(-sc, min(limit, len(sc) - 1))[:limit]
    return {lo + int(i): float(sc[i]) for i in top}


@lru_cache(maxsize=4096)
def _row_salts(raw: str) -> tuple:
    try:
        return tuple((s.get("salt", ""), s.get("strength", "")) for s in json.loads(raw))
    except (ValueError, TypeError):
        return ()


# Read form -> words that appear in matching product names ("SYP CALPOL" should prefer Calpol suspension).
FORM_FAMILIES = {
    "syrup": ("syrup", "suspension", "solution", "liquid", "elixir"),
    "tablet": ("tablet",), "capsule": ("capsule",),
    "injection": ("injection", "infusion", "vial"),
    "drops": ("drop",), "cream": ("cream", "gel", "ointment", "lotion"),
    "inhaler": ("inhaler", "respules", "rotacap"),
}
FORM_ALIASES = {"syp": "syrup", "syr": "syrup", "suspension": "syrup", "susp": "syrup", "tab": "tablet",
                "cap": "capsule", "inj": "injection", "drop": "drops", "eye drops": "drops", "gel": "cream",
                "ointment": "cream", "respules": "inhaler"}


def _form_words(form: str | None) -> tuple[str, ...]:
    f = (form or "").strip().lower()
    return FORM_FAMILIES.get(FORM_ALIASES.get(f, f), ())


def candidates(name: str, strength: str | None = None, k: int = 3, form: str | None = None) -> list[dict]:
    """Top-k real brands for a (possibly misread) name, best first.

    Each candidate: {"name": str, "base_name": str, "salts": [{"salt": str, "strength": str}],
                     "salt_key": str,   # sorted salt names joined by "+", e.g. "ibuprofen+paracetamol"
                     "price": float, "pack": str, "desc": str, "score": float (0-100)}
    Candidates sharing a salt_key are de-duplicated (keep the best-scoring row).
    """
    # "ATIVAN (Lorazepam)": the bracketed generic would otherwise drag in other lorazepam brands.
    q = _match_key(normalise_query(re.sub(r"\([^)]*\)", " ", name or ""))) or _match_key(normalise_query(name))
    if not q:
        return []
    d = _load()
    form_words = _form_words(form)
    q_brand = q.split()[0]
    q_words = set(re.findall(r"[a-z]+", q)) - {"mg", "mcg", "ml", "gm", "g", "iu"}
    want = numbers(strength)
    hits = _search(q, d, 200)
    extra = sorted(want - numbers(q))
    if extra:
        # also try the read strength as part of the name ("Dolo" + "650mg" -> "dolo 650")
        for idx, sc in _search(f"{q} {extra[0]}", d, 200).items():
            hits[idx] = max(sc, hits.get(idx, 0.0))
    alpha_q = _alpha(q)
    scored = []
    for idx, sc in hits.items():
        if alpha_q:
            # WRatio gives 85.5 to any name sharing one token ("650", "1", "duo"); the letters of the
            # name must support the score, else "Dolo 650" ~ "Spirodin 650" looks like a look-alike.
            sc = min(sc, fuzz.WRatio(alpha_q, _alpha(d["keys"][idx])))
        salts = [{"salt": s, "strength": st} for s, st in _row_salts(d["salts"][idx])]
        if want:
            have = numbers(d["names"][idx]).union(*(numbers(s["strength"]) for s in salts))
            if want & have:
                sc += 5  # ranked uncapped so a strength match beats an exact name without it
        if d["keys"][idx].split()[:1] == [q_brand]:
            sc += 5  # same brand word as written ("levolin" -> Levolin, not Levolink)
        if form_words and any(w in d["names"][idx].lower() for w in form_words):
            sc += 4  # same dosage form as written (syrup vs tablet of the same brand)
        words = set(re.findall(r"[a-z]+", d["keys"][idx]))
        same_brand = d["keys"][idx].split()[:1] == [q_brand]
        scored.append((sc, idx, salts, same_brand, len(words - q_words), len(q_words - words)))
    # The written brand word wins first; then products missing none of the written words; then score;
    # then fewer unwritten extra words ("telma h" -> Telma H, not Telma-AM H); then edit ratio.
    # Ranking only (scores untouched, so look-alike detection is unchanged): a written word the product lacks
    # ("telma h 40" vs Telma 40) ranks it below one that has every written word.
    scored.sort(key=lambda t: (not t[3], t[5], -t[0], t[4], -fuzz.ratio(q, d["keys"][t[1]]), d["lens"][t[1]], t[1]))
    seen, out = set(), []
    for sc, idx, salts, _same, _extra, _missing in scored:
        key = salt_key(salts)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"name": d["names"][idx], "base_name": d["bases"][idx], "salts": salts, "salt_key": key,
                    "price": float(d["prices"][idx]), "pack": d["packs"][idx], "desc": d["descs"][idx],
                    "score": round(min(100.0, sc), 1)})
        if len(out) >= k:
            break
    return out
