"""AushNexa pipeline: Gemma reads, code decides.

analyze() runs the Gemma reads (in parallel threads), matches every read against
the brand dataset, makes ONE assess_context call for every (med, candidate) pair,
scores confidence and runs the deterministic safety checks. recheck() re-runs only
the code checks (no Gemma) after a doctor or patient resolution.
"""
from __future__ import annotations

import copy
import re
import time
from concurrent.futures import ThreadPoolExecutor

from core import confidence, llm, match, safety

FREQ_RE = re.compile(r"\b(OD|BD|BID|TDS|TID|QID|SOS|HS|STAT)\b", re.I)
STRENGTH_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|ml|iu|%)\b", re.I)
BARE_NUM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\b")
DURATION_RE = re.compile(r"(?:\bx\s*|\bfor\s+|×\s*)?(\d+)\s*(days?|weeks?|months?|d|wk|w)\b", re.I)
FORM_RE = re.compile(r"\b(tab(?:let)?s?|cap(?:sule)?s?|syr(?:up)?|inj(?:ection)?|drops?|cream|gel|ointment|susp(?:ension)?)\b\.?", re.I)
_FORM_NAMES = {"tab": "tablet", "cap": "capsule", "syr": "syrup", "inj": "injection", "drop": "drops",
               "cream": "cream", "gel": "gel", "ointment": "ointment", "susp": "suspension"}
FIT_BONUS = {"yes": 1, "unclear": 0, None: 0, "no": -1}


# ---------------------------------------------------------------- typed input

def _form(word: str | None) -> str | None:
    if not word:
        return None
    w = word.lower().rstrip(".")
    for k, v in _FORM_NAMES.items():
        if w.startswith(k):
            return v
    return None


def parse_line(line: str) -> dict | None:
    raw = line.strip().strip("-•*").strip()
    raw = re.sub(r"^\d+[.)]\s+", "", raw)  # "1. Dolo 650" / "2) Combiflam"
    if not raw:
        return None
    freq_m = FREQ_RE.search(raw)
    dur_m = DURATION_RE.search(raw)
    # Name = everything before the first frequency / duration token.
    cut = len(raw)
    for m in (freq_m, dur_m):
        if m:
            cut = min(cut, m.start())
    name_part = re.sub(r"\s+[x×]$", "", raw[:cut].strip(" ,;-"))
    form_m = FORM_RE.search(name_part)
    form = _form(form_m.group(1)) if form_m else None
    if form_m:  # "Tab Dolo 650" -> "Dolo 650"
        name_part = (name_part[:form_m.start()] + " " + name_part[form_m.end():]).strip()
    name_part = re.sub(r"\s+", " ", name_part).strip(" ,;-")
    sm = STRENGTH_UNIT_RE.search(name_part)
    if sm:
        strength = f"{sm.group(1)} {sm.group(2).lower()}"
    else:
        bm = BARE_NUM_RE.search(name_part)
        strength = bm.group(1) if bm else None
    return {
        "raw_text": raw,
        "brand_or_drug": name_part or raw,
        "form": form,
        "strength": strength,
        "dose_and_frequency": freq_m.group(1).upper() if freq_m else "",
        "duration": f"{dur_m.group(1)} {dur_m.group(2)}" if dur_m else "",
        "unsure": False,
    }


def parse_typed(text: str) -> list[dict]:
    """One medicine per line -> list of read dicts (same shape as llm.read_prescription items)."""
    out = []
    for line in (text or "").splitlines():
        r = parse_line(line)
        if r:
            out.append(r)
    return out


def freq_token(freq: str | None) -> str:
    m = FREQ_RE.search(freq or "")
    return m.group(1).upper() if m else ""


# ---------------------------------------------------------------- helpers

def _code_step(step: str, t0: float, error: str | None = None) -> dict:
    return {"step": step, "model": "code (deterministic)", "backend": "python",
            "seconds": round(time.time() - t0, 3), "cache_hit": False, "error": error}


def _fit_lookup(med: dict, cand_name: str | None) -> dict | None:
    if not cand_name:
        return None
    return (med.get("fits") or {}).get(cand_name)


def _resolved(med: dict) -> dict:
    """The medicine the safety checks use: the selected candidate, else the top candidate."""
    read = med["read"]
    chosen = med.get("selected") or (med["candidates"][0] if med.get("candidates") else None)
    if chosen:
        label, salts = chosen.get("name"), chosen.get("salts") or []
        price, pack = chosen.get("price"), chosen.get("pack")
    else:
        label, salts, price, pack = read.get("brand_or_drug") or read.get("raw_text"), [], None, None
    return {"index": med["index"], "label": label, "salts": salts,
            "freq": read.get("dose_and_frequency") or "", "price": price, "pack": pack,
            "status": med.get("status", "auto")}


def _status_for(band: str) -> str:
    return "auto" if band == "HIGH" else "needs_confirmation"


def _schedule(freq: str) -> list[str]:
    try:
        slots = safety.schedule(freq or "")
        if not slots and freq_token(freq):
            slots = safety.schedule(freq_token(freq))
        return list(slots or [])
    except Exception:  # noqa: BLE001 - never break the report on a schedule glitch
        return []


def _run_code_checks(case: dict) -> None:
    """Resolved meds, alerts, strip check, Jan Aushadhi, savings, schedule. Mutates case."""
    meds = case["meds"]
    t0 = time.time()
    resolved = [_resolved(m) for m in meds]
    alerts = []
    try:
        alerts += safety.duplicates(resolved) or []
        alerts += safety.allergy(resolved, case.get("allergies") or []) or []
    except Exception as e:  # noqa: BLE001
        case.setdefault("errors", []).append(f"safety: {e}")
    order = {"HIGH": 0, "REVIEW": 1, "INFO": 2}
    alerts.sort(key=lambda a: order.get(a.get("severity"), 3))
    case["resolved"] = resolved
    case["alerts"] = alerts

    strip_resolved = case.get("strip_resolved")
    case["strip"] = None
    if strip_resolved:
        try:
            case["strip"] = safety.strip_check(strip_resolved, resolved)
        except Exception as e:  # noqa: BLE001
            case["strip"] = {"status": "ERROR", "detail": str(e), "med_index": None}

    ja = []
    for m in resolved:
        try:
            g = safety.jan_aushadhi(m)
        except Exception:  # noqa: BLE001
            g = None
        ja.append({"index": m["index"], "brand": m["label"], "brand_price": m["price"],
                   "brand_pack": m["pack"], "generic": g})
    case["jan_aushadhi"] = ja
    try:
        case["savings"] = float(safety.monthly_savings(resolved, [m["price"] for m in resolved]) or 0.0)
    except Exception:  # noqa: BLE001
        case["savings"] = 0.0
    case["schedule"] = [{"index": m["index"], "label": m["label"], "freq": m["freq"], "slots": _schedule(m["freq"])}
                        for m in resolved]
    case.setdefault("_trace", []).append(_code_step("safety: duplicates, allergy, strip, Jan Aushadhi, schedule", t0))


# ---------------------------------------------------------------- analyze

def analyze(context: str, allergies, rx_image: bytes | None = None, rx_text: str | None = None,
            strip_image: bytes | None = None, on_step=None) -> dict:
    """Full pipeline. Returns a JSON-serialisable case dict. on_step(label) is an optional progress callback."""
    def step(label):
        if on_step:
            try:
                on_step(label)
            except Exception:  # noqa: BLE001
                pass

    t_start = time.time()
    if isinstance(allergies, str):
        allergies = [a.strip() for a in allergies.split(",") if a.strip()]
    allergies = list(allergies or [])
    case = {"context": context or "", "allergies": allergies, "input_mode": "typed" if rx_text else "photo",
            "meds": [], "errors": [], "_trace": [], "strip_read": None, "strip_resolved": None,
            "hindi_summary": ""}

    # 1. Reads, in parallel threads.
    step("Gemma 4 reading prescription…" if rx_image is not None and not rx_text else "Parsing typed prescription…")
    with ThreadPoolExecutor(max_workers=2) as ex:
        rx_future = strip_future = None
        if rx_text:
            t0 = time.time()
            reads = parse_typed(rx_text)
            case["_trace"].append(_code_step("parse_typed (typed prescription)", t0))
        elif rx_image is not None:
            rx_future = ex.submit(llm.read_prescription, rx_image)
            reads = []
        else:
            reads = []
        if strip_image is not None:
            step("Gemma 4 reading medicine strip…")
            strip_future = ex.submit(llm.read_strip, strip_image)
        if rx_future is not None:
            res = rx_future.result() or {}
            case["_trace"] += res.get("_trace") or []
            if res.get("error"):
                case["errors"].append(f"Prescription read failed: {res['error']}")
            reads = res.get("medicines") or []
        if strip_future is not None:
            sres = strip_future.result() or {}
            case["_trace"] += sres.get("_trace") or []
            if sres.get("error"):
                case["errors"].append(f"Strip read failed: {sres['error']}")
            else:
                case["strip_read"] = {k: v for k, v in sres.items() if k != "_trace"}

    # 2. Match every read against the brand dataset.
    step("Matching against 242k Indian brands…")
    t0 = time.time()
    for i, r in enumerate(reads):
        name = r.get("brand_or_drug") or r.get("raw_text") or ""
        try:
            cands = match.candidates(name, r.get("strength"), form=r.get("form")) or []
        except Exception as e:  # noqa: BLE001
            case["errors"].append(f"match {name!r}: {e}")
            cands = []
        case["meds"].append({"index": i, "read": r, "candidates": cands[:3], "fits": {}, "selected": None,
                             "status": "auto", "confidence": None})
    sr = case["strip_read"]
    if sr and (sr.get("brand_or_drug") or sr.get("raw_text")):
        try:
            sc = match.candidates(sr.get("brand_or_drug") or sr.get("raw_text"), sr.get("strength")) or []
        except Exception:  # noqa: BLE001
            sc = []
        top = sc[0] if sc else {}
        case["strip_resolved"] = {"label": top.get("name") or sr.get("brand_or_drug"), "salts": top.get("salts") or [],
                                  "strength": sr.get("strength"), "raw_text": sr.get("raw_text"),
                                  "brand_or_drug": sr.get("brand_or_drug")}
    case["_trace"].append(_code_step(f"match.candidates x{len(reads) + (1 if sr else 0)} (rapidfuzz)", t0))

    # 3. ONE Gemma call: does each candidate fit the patient's context? (+ Hindi summary)
    if case["meds"]:
        step("Gemma 4 checking fit with patient context…")
        payload = [{"index": m["index"], "raw_text": m["read"].get("raw_text", ""),
                    "candidates": [{"name": c.get("name"), "salts": c.get("salts"), "desc": c.get("desc", "")}
                                   for c in m["candidates"]]} for m in case["meds"]]
        ares = llm.assess_context(case["context"], payload) or {}
        case["_trace"] += ares.get("_trace") or []
        if ares.get("error"):
            case["errors"].append(f"Context check failed: {ares['error']}")
        for f in ares.get("fit") or []:
            try:
                med = case["meds"][int(f.get("index"))]
            except (TypeError, ValueError, IndexError):
                continue
            cname = f.get("candidate") or (med["candidates"][0]["name"] if med["candidates"] else None)
            if cname:
                med["fits"][cname] = {"fits": f.get("fits"), "reason": f.get("reason", "")}
        case["hindi_summary"] = ares.get("hindi_summary") or ""

    # 4. Confidence per med (code).
    step("Scoring confidence…")
    t0 = time.time()
    for m in case["meds"]:
        top = m["candidates"][0]["name"] if m["candidates"] else None
        fit = (_fit_lookup(m, top) or {}).get("fits")
        try:
            m["confidence"] = confidence.score(m["read"], m["candidates"], fit)
        except Exception as e:  # noqa: BLE001
            m["confidence"] = {"value": 0.0, "band": "LOW", "breakdown": {}, "reasons": [f"scoring error: {e}"],
                               "lasa_rival": None}
        if not m["candidates"]:
            m["confidence"]["band"] = "LOW"
            m["confidence"].setdefault("reasons", []).append("No matching brand found in the dataset")
        m["status"] = _status_for(m["confidence"].get("band"))
    case["_trace"].append(_code_step("confidence.score (fuzzy + gap + LASA + fit)", t0))

    # 5-8. Safety, strip, Jan Aushadhi, schedule (code).
    step("Running safety checks…")
    _run_code_checks(case)
    if not case["hindi_summary"] and case["meds"]:
        names = ", ".join(r["label"] or "?" for r in case["resolved"])
        case["hindi_summary"] = f"(English fallback) Your prescription has: {names}. Please confirm with your doctor."
    case["elapsed"] = round(time.time() - t_start, 2)
    step("Done")
    return case


# ---------------------------------------------------------------- doctor loop

def apply_resolution(case: dict, med_index: int, resolution: dict, by: str = "doctor") -> dict:
    """resolution: {"name": candidate name} or {"free_text": "Calcimax"}. Free text is re-matched via candidates().
    Returns an updated copy of the case (status confirmed_by_doctor / picked_by_patient). Call recheck() after."""
    case = copy.deepcopy(case)
    med = case["meds"][med_index]
    chosen = None
    name = (resolution or {}).get("name")
    free = (resolution or {}).get("free_text")
    if name:
        chosen = next((c for c in med["candidates"] if c.get("name") == name), None)
        if chosen is None:
            free = name
    if chosen is None and free:
        t0 = time.time()
        try:
            cands = match.candidates(free, med["read"].get("strength")) or []
        except Exception:  # noqa: BLE001
            cands = []
        case.setdefault("_trace", []).append(_code_step(f"match.candidates('{free}') for doctor's answer", t0))
        chosen = cands[0] if cands else {"name": free, "salts": [], "price": None, "pack": None, "desc": "",
                                         "score": 0.0, "salt_key": ""}
    if chosen is None:
        return case
    med["selected"] = chosen
    med["status"] = "confirmed_by_doctor" if by == "doctor" else "picked_by_patient"
    med["resolution"] = dict(resolution or {}, by=by)
    return case


def recheck(case: dict) -> dict:
    """Re-run only the code checks (no Gemma), reusing stored per-candidate fits."""
    case = copy.deepcopy(case)
    t0 = time.time()
    for m in case["meds"]:
        if m.get("status") in ("confirmed_by_doctor", "picked_by_patient"):
            continue  # a human decided; keep their choice
        top = m["candidates"][0]["name"] if m["candidates"] else None
        fit = (_fit_lookup(m, top) or {}).get("fits")
        try:
            m["confidence"] = confidence.score(m["read"], m["candidates"], fit)
        except Exception:  # noqa: BLE001
            pass
    case.setdefault("_trace", []).append(_code_step("recheck: confidence (no Gemma call)", t0))
    _run_code_checks(case)
    case["rechecked"] = True
    return case
