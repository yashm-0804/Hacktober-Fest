"""Gemma 4 access (Gemini API or Ollama), section `ai` (AI-1..5).

Every function: never raises; returns {"error": str, "_trace": [...]} on failure.
"_trace" is a list of {"step": str, "model": str, "backend": str, "seconds": float, "cache_hit": bool, "error": str | None}.

Backend is read from os.environ["LLM_BACKEND"] ("gemini" | "ollama") at call time, so the UI can toggle it.
Images are downscaled to 1600 px JPEG before hashing/sending; parsed JSON is cached in cache/llm/.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import threading
import time
from pathlib import Path

from core import prompts

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "llm"

MAX_SIDE = 1600
JPEG_QUALITY = 85
CALL_TIMEOUT_S = 90          # per Gemini call
OLLAMA_TIMEOUT_S = 120       # per Ollama call
BACKOFF_S = (2, 5)           # sleep before attempt 2 and attempt 3
MAX_ATTEMPTS = 3
BUDGET_S = 150               # total wall-clock budget per function call
MIN_ATTEMPT_S = 10           # don't start an attempt with less than this left

_SEM = threading.Semaphore(2)  # at most 2 concurrent Gemma calls
_client_lock = threading.Lock()
_clients: dict = {}

CONFIRM_HI = "डॉक्टर या फार्मासिस्ट से पुष्टि करें।"


# ---------------------------------------------------------------- env

def _load_env(path: Path = ROOT / ".env") -> None:
    """Tiny .env parser: KEY=VALUE lines, # comments, optional quotes. Never overrides os.environ."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


_load_env()


def _backend(override: str | None = None) -> tuple[str, str]:
    b = (override or os.environ.get("LLM_BACKEND") or "gemini").strip().lower()
    if b == "ollama":
        return "ollama", os.environ.get("OLLAMA_MODEL") or "gemma4:e4b"
    return "gemini", os.environ.get("GEMMA_MODEL") or "gemma-4-26b-a4b-it"


def _limits(backend: str) -> tuple[float, float]:
    """(per-attempt timeout, total budget) in seconds. Env overrides (GEMMA_TIMEOUT_S, GEMMA_BUDGET_S) let
    scripts/warm_cache.py wait longer than the interactive UI; read at call time."""
    def num(name, default):
        try:
            return float(os.environ.get(name) or default)
        except ValueError:
            return float(default)
    per_call = num("GEMMA_TIMEOUT_S", OLLAMA_TIMEOUT_S if backend == "ollama" else CALL_TIMEOUT_S)
    return per_call, num("GEMMA_BUDGET_S", BUDGET_S)


def _fallback_enabled() -> bool:
    return os.environ.get("GEMMA_FALLBACK", "").strip().lower() == "ollama"


def backend_info() -> dict:
    """{"backend": "gemini"|"ollama", "model": str}"""
    b, m = _backend()
    return {"backend": b, "model": m}


# ---------------------------------------------------------------- helpers

_prep_memo: dict[str, bytes] = {}  # sha256(raw upload) -> prepped JPEG, so repeat calls skip the resize


def _prep_image(image: bytes) -> bytes:
    """Downscale to max side 1600 px, RGB JPEG q85. Raises on unreadable input (caller catches)."""
    from PIL import Image, ImageOps

    raw_key = hashlib.sha256(image).hexdigest()
    if raw_key in _prep_memo:
        return _prep_memo[raw_key]
    im = Image.open(io.BytesIO(image))
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=JPEG_QUALITY)
    if len(_prep_memo) > 64:
        _prep_memo.clear()
    _prep_memo[raw_key] = out.getvalue()
    return _prep_memo[raw_key]


def _cache_key(backend: str, model: str, prompt: str, image: bytes | None) -> str:
    h = hashlib.sha256()
    for part in (backend.encode(), model.encode(), prompt.encode("utf-8"), image or b""):
        h.update(len(part).to_bytes(8, "big"))  # length-prefix so field boundaries can't collide
        h.update(part)
    return h.hexdigest()


def _cache_get(key: str):
    try:
        return json.loads((CACHE_DIR / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache_put(key: str, value) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_DIR / f"{key}.{threading.get_ident()}.tmp"
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CACHE_DIR / f"{key}.json")
    except OSError:
        pass  # cache is best-effort


_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def extract_json(text: str):
    """Model text -> dict, or None. Strips ```json fences, then takes the outermost {...}.
    A bare top-level list is wrapped as {"items": [...]}."""
    if not text:
        return None
    m = _FENCE.search(text)
    body = (m.group(1) if m else text).strip()
    try:
        val = json.loads(body)
        if isinstance(val, dict):
            return val
        if isinstance(val, list):
            return {"items": val}
    except ValueError:
        pass
    start, end = body.find("{"), body.rfind("}")
    if start != -1 and end > start:
        try:
            val = json.loads(body[start:end + 1])
            if isinstance(val, dict):
                return val
        except ValueError:
            pass
    return None


class _Retryable(Exception):
    pass


def _short(e: Exception) -> str:
    s = f"{type(e).__name__}: {e}"
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        s = s.replace(key, "***")
    return s[:300]


# ---------------------------------------------------------------- backends

def _gemini_client(key: str):
    with _client_lock:
        c = _clients.get(key)
        if c is None:
            from google import genai
            c = _clients[key] = genai.Client(api_key=key)
        return c


def _gemini_call(model: str, prompt: str, image: bytes | None, timeout_s: float) -> str:
    from google.genai import errors, types

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    contents = ([types.Part.from_bytes(data=image, mime_type="image/jpeg")] if image else []) + [prompt]
    cfg = types.GenerateContentConfig(temperature=0, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
    try:
        resp = _gemini_client(key).models.generate_content(model=model, contents=contents, config=cfg)
    except errors.APIError as e:
        if e.code is not None and (e.code >= 500 or e.code == 429):
            raise _Retryable(_short(e)) from e
        raise
    except Exception as e:  # httpx timeouts / connection drops
        if "timeout" in type(e).__name__.lower() or "connect" in type(e).__name__.lower() \
                or "timed out" in str(e).lower():
            raise _Retryable(_short(e)) from e
        raise
    return resp.text or ""


def _ollama_call(model: str, prompt: str, image: bytes | None, timeout_s: float) -> str:
    import requests

    url = (os.environ.get("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
    msg = {"role": "user", "content": prompt}
    if image:
        msg["images"] = [base64.b64encode(image).decode()]
    body = {"model": model, "messages": [msg], "stream": False, "format": "json", "options": {"temperature": 0}}
    try:
        r = requests.post(f"{url}/api/chat", json=body, timeout=timeout_s)
    except requests.Timeout as e:
        raise _Retryable(_short(e)) from e
    except requests.ConnectionError as e:
        raise RuntimeError(f"Ollama not reachable at {url}") from e
    if r.status_code >= 500:
        raise _Retryable(f"Ollama HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {r.status_code}: {r.text[:200]}")
    return (r.json().get("message") or {}).get("content") or ""


_BACKENDS = {"gemini": _gemini_call, "ollama": _ollama_call}


# ---------------------------------------------------------------- core call

def _call(step: str, prompt: str, image: bytes | None = None, validate=None, image_prepped: bool = False,
          backend_override: str | None = None):
    """Returns (parsed_dict | None, trace, error | None). Never raises.

    With GEMMA_FALLBACK=ollama, a failed Gemini API call is retried once on the local open-weights model."""
    t_start = time.monotonic()
    backend, model = _backend(backend_override)
    trace: list[dict] = []

    def add(name, secs, hit, err):
        trace.append({"step": name, "model": model, "backend": backend,
                      "seconds": round(secs, 3), "cache_hit": hit, "error": err})

    try:
        if image is not None and not image_prepped:
            image = _prep_image(image)
    except Exception as e:
        add(step, time.monotonic() - t_start, False, f"unreadable image: {_short(e)}")
        return None, trace, "Could not read the image file."

    key = _cache_key(backend, model, prompt, image)
    hit = _cache_get(key)
    if isinstance(hit, dict):
        add(step, time.monotonic() - t_start, True, None)
        return hit, trace, None

    if backend == "gemini" and backend_override is None and _fallback_enabled():
        # This exact input already failed on the API once and was answered locally: reuse that answer
        # instead of waiting out another API timeout before falling back again.
        fb_backend, fb_model = _backend("ollama")
        fb_hit = _cache_get(_cache_key(fb_backend, fb_model, prompt, image))
        if isinstance(fb_hit, dict):
            trace.append({"step": f"{step} (local fallback)", "model": fb_model, "backend": fb_backend,
                          "seconds": round(time.monotonic() - t_start, 3), "cache_hit": True, "error": None})
            return fb_hit, trace, None

    fn = _BACKENDS[backend]
    per_call, budget = _limits(backend)
    last_err = "no attempt made"
    for attempt in range(MAX_ATTEMPTS):
        name = step if attempt == 0 else f"{step} (attempt {attempt + 1})"
        if attempt:
            wait = BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)]
            if budget - (time.monotonic() - t_start) - wait < MIN_ATTEMPT_S:
                break
            time.sleep(wait)
        remaining = budget - (time.monotonic() - t_start)
        if remaining < MIN_ATTEMPT_S:
            break
        t0 = time.monotonic()
        if not _SEM.acquire(timeout=remaining - MIN_ATTEMPT_S if remaining > MIN_ATTEMPT_S else 0):
            last_err = "too many concurrent Gemma calls (timed out waiting)"
            add(name, time.monotonic() - t0, False, last_err)
            break
        try:
            remaining = budget - (time.monotonic() - t_start)
            text = fn(model, prompt, image, max(MIN_ATTEMPT_S, min(per_call, remaining)))
        except _Retryable as e:
            last_err = str(e)
            add(name, time.monotonic() - t0, False, last_err)
            continue
        except Exception as e:  # non-retryable: bad key, 4xx, Ollama down, model missing
            last_err = _short(e)
            add(name, time.monotonic() - t0, False, last_err)
            break
        finally:
            _SEM.release()
        parsed = extract_json(text)
        if parsed is None or (validate is not None and not validate(parsed)):
            last_err = f"unparseable model output: {text[:160]!r}"
            add(name, time.monotonic() - t0, False, last_err)
            continue
        add(name, time.monotonic() - t0, False, None)
        _cache_put(key, parsed)
        return parsed, trace, None
    err = f"Gemma ({backend}/{model}) failed: {last_err}"
    if backend == "gemini" and backend_override is None and _fallback_enabled():
        parsed, fb_trace, fb_err = _call(f"{step} (local fallback)", prompt, image, validate,
                                         image_prepped=True, backend_override="ollama")
        return parsed, trace + fb_trace, (f"{err}; local fallback failed: {fb_err}" if fb_err else None)
    return None, trace, err


# ---------------------------------------------------------------- normalisers

def _s(v):
    """Coerce to stripped str or None."""
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("null", "none", "n/a") else None


def _b(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1")
    return bool(v)


def _meds_list(parsed: dict):
    meds = parsed.get("medicines", parsed.get("items"))
    return meds if isinstance(meds, list) else None


# ---------------------------------------------------------------- public API

def generate_json(prompt: str, step: str, image: bytes | None = None) -> dict:
    """Generic Gemma call for other modules (e.g. core/triage.py): same backend switch, cache, semaphore,
    retries, timeout, JSON extraction and _trace as the functions below. Never raises.
    Returns the model's parsed JSON object plus "_trace", or {"error": str, "_trace": [...]}.
    The prompt must ask for a JSON object; a bare JSON list comes back as {"items": [...]}."""
    try:
        parsed, trace, err = _call(str(step or "generate_json"), str(prompt or ""), image)
        if err:
            return {"error": err, "_trace": trace}
        out = dict(parsed)
        out["_trace"] = trace
        return out
    except Exception as e:
        return {"error": f"generate_json crashed: {_short(e)}", "_trace": []}


def read_prescription(image: bytes) -> dict:
    """{"medicines": [{"raw_text", "brand_or_drug", "form", "strength", "dose_and_frequency", "duration", "unsure": bool}], "_trace": [...]}"""
    try:
        parsed, trace, err = _call("read_prescription", prompts.PRESCRIPTION, image,
                                   validate=lambda p: _meds_list(p) is not None)
        if err:
            return {"error": err, "_trace": trace}
        meds = []
        for m in _meds_list(parsed):
            if not isinstance(m, dict):
                continue
            name, raw = _s(m.get("brand_or_drug")), _s(m.get("raw_text"))
            if not name and not raw:
                continue
            meds.append({"raw_text": raw or name, "brand_or_drug": name or raw, "form": _s(m.get("form")),
                         "strength": _s(m.get("strength")), "dose_and_frequency": _s(m.get("dose_and_frequency")),
                         "duration": _s(m.get("duration")), "unsure": _b(m.get("unsure"))})
        return {"medicines": meds, "_trace": trace}
    except Exception as e:  # belt and braces: never raise
        return {"error": f"read_prescription crashed: {_short(e)}", "_trace": []}


def read_strip(image: bytes) -> dict:
    """{"brand_or_drug": str, "strength": str | None, "raw_text": str, "_trace": [...]}"""
    try:
        parsed, trace, err = _call("read_strip", prompts.STRIP, image,
                                   validate=lambda p: "brand_or_drug" in p or "raw_text" in p)
        if err:
            return {"error": err, "_trace": trace}
        name, raw = _s(parsed.get("brand_or_drug")), _s(parsed.get("raw_text"))
        if not name:
            return {"error": "No medicine name found on the strip photo.", "raw_text": raw or "", "_trace": trace}
        return {"brand_or_drug": name, "strength": _s(parsed.get("strength")), "raw_text": raw or name, "_trace": trace}
    except Exception as e:
        return {"error": f"read_strip crashed: {_short(e)}", "_trace": []}


def read_report(image: bytes) -> dict:
    """{"conditions": [str], "summary": str, "_trace": [...]}"""
    try:
        parsed, trace, err = _call("read_report", prompts.REPORT, image,
                                   validate=lambda p: "conditions" in p or "summary" in p)
        if err:
            return {"error": err, "_trace": trace}
        conds = parsed.get("conditions") or []
        if isinstance(conds, str):
            conds = [conds]
        conds = [c for c in (_s(x) for x in conds if not isinstance(x, (dict, list))) if c]
        return {"conditions": conds, "summary": _s(parsed.get("summary")) or "", "_trace": trace}
    except Exception as e:
        return {"error": f"read_report crashed: {_short(e)}", "_trace": []}


def _salts_text(salts) -> str:
    if isinstance(salts, str):
        return salts
    out = []
    for s in salts or []:
        if isinstance(s, dict):
            out.append(" ".join(x for x in (str(s.get("salt") or ""), str(s.get("strength") or "")) if x).strip())
        else:
            out.append(str(s))
    return " + ".join(x for x in out if x)


def _english_fallback(meds: list[dict]) -> str:
    parts = ["Automatic Hindi summary is unavailable right now. This is not a diagnosis."]
    for m in meds:
        cands = m.get("candidates") or []
        if cands:
            c = cands[0]
            salts = _salts_text(c.get("salts"))
            parts.append(f"{c.get('name')}{f' ({salts})' if salts else ''}: take as written on the prescription "
                         f"({m.get('raw_text') or 'see prescription'}).")
    parts.append("Please confirm every medicine with your doctor or pharmacist.")
    return " ".join(parts)


def assess_context(context: str, meds: list[dict]) -> dict:
    """meds: [{"index": int, "raw_text": str, "candidates": [{"name", "salts", "desc"}]}]
    Returns {"fit": [{"index": int, "candidate": str (candidate name), "fits": "yes"|"no"|"unclear", "reason": str}],
             "hindi_summary": str, "_trace": [...]}
    One entry per (med, candidate) pair, so a doctor's correction never needs another Gemma call."""
    meds = [m for m in (meds or []) if isinstance(m, dict)]
    pairs = [(m.get("index"), str(c.get("name"))) for m in meds for c in (m.get("candidates") or []) if isinstance(c, dict)]

    def unclear(reason):
        return [{"index": i, "candidate": n, "fits": "unclear", "reason": reason} for i, n in pairs]

    try:
        compact = [{"index": m.get("index"), "prescription_text": m.get("raw_text"),
                    **({"dose_and_frequency": m["dose_and_frequency"]} if m.get("dose_and_frequency") else {}),
                    "candidates": [{"name": c.get("name"), "salts": _salts_text(c.get("salts")),
                                    **({"desc": str(c["desc"])[:200]} if c.get("desc") else {})}
                                   for c in (m.get("candidates") or []) if isinstance(c, dict)]}
                   for m in meds]
        prompt = prompts.ASSESS.format(context=(context or "(none given)").strip()[:2000],
                                       meds_json=json.dumps(compact, ensure_ascii=False, indent=1))
        parsed, trace, err = _call("assess_context", prompt,
                                   validate=lambda p: isinstance(p.get("fit"), list) and isinstance(p.get("hindi_summary"), str))
        if err:
            return {"fit": unclear("Gemma unavailable; not assessed."), "hindi_summary": _english_fallback(meds),
                    "error": err, "_trace": trace}
        got = {}
        for f in parsed.get("fit") or []:
            if not isinstance(f, dict):
                continue
            try:
                idx = int(f.get("index"))
            except (TypeError, ValueError):
                continue
            fits = str(f.get("fits") or "").strip().lower()
            got[(idx, str(f.get("candidate") or "").strip().casefold())] = (
                fits if fits in ("yes", "no", "unclear") else "unclear", _s(f.get("reason")) or "")
        fit = []
        for i, n in pairs:
            fits, reason = got.get((i, n.strip().casefold()), ("unclear", "Not assessed by the model."))
            fit.append({"index": i, "candidate": n, "fits": fits, "reason": reason})
        hindi = (parsed.get("hindi_summary") or "").strip()
        if not hindi:
            hindi = _english_fallback(meds)
        elif not hindi.endswith(CONFIRM_HI):
            hindi = f"{hindi} {CONFIRM_HI}"
        return {"fit": fit, "hindi_summary": hindi, "_trace": trace}
    except Exception as e:
        return {"fit": unclear("Assessment failed; not assessed."), "hindi_summary": _english_fallback(meds),
                "error": f"assess_context crashed: {_short(e)}", "_trace": []}
