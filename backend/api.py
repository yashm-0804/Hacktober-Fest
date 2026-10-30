"""AushNexa REST API for the mobile app. Gemma reads, code decides, a doctor confirms.

Run:  uvicorn api:app --host 0.0.0.0 --port 8000

If the web app has been built (cd mobile && npx expo export --platform web), the same server also serves it,
so the whole app opens at http://localhost:8000 (see run-website.sh at the repository root).

Slow work (Gemma reads can take 40-200 s) runs as a background job: POST returns {"job_id"} at once and
the app polls GET /api/jobs/{id}, which reports each pipeline step as it happens. Everything else is
plain request/response over the same SQLite store (core/store.py).
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core import llm, pipeline, store, stt, triage
from core.testlab import run_cases

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "demo_assets"
DEMO_FILES = {"prescription.jpg", "strip.jpg"}
WEB_DIR = Path(os.environ.get("WEB_DIR") or ROOT.parent / "mobile" / "dist")
MAX_UPLOAD = 15 * 1024 * 1024
MAX_TEXT = 2000

app = FastAPI(title="AushNexa API", version="1.0.0",
              description="Prescription safety for Indian brand medicines, built with Gemma 4.")
app.add_middleware(CORSMiddleware, allow_origins=(os.environ.get("CORS_ORIGINS") or "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])

_case_lock = threading.Lock()  # serialises read-modify-write of a case payload


# ---------------------------------------------------------------- jobs

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=4)
JOB_TTL_S = 3600


def _start_job(kind: str, work) -> str:
    """Run work(on_step) on the pool. on_step(label) appends a progress step the app can show."""
    jid = uuid.uuid4().hex[:16]
    job = {"id": jid, "kind": kind, "status": "running", "steps": [], "started": time.time(),
           "finished": None, "result": None, "error": None}
    with _jobs_lock:
        now = time.time()
        for k in [k for k, j in _jobs.items() if j["finished"] and now - j["finished"] > JOB_TTL_S]:
            del _jobs[k]
        _jobs[jid] = job

    def on_step(label: str) -> None:
        job["steps"].append({"label": label, "at": round(time.time() - job["started"], 1)})

    def run() -> None:
        try:
            job["result"] = work(on_step)
            job["status"] = "done"
        except Exception as e:  # noqa: BLE001 - reported to the app, never raised into the pool
            job["error"] = f"{type(e).__name__}: {e}"[:300]
            job["status"] = "error"
        job["finished"] = time.time()

    _pool.submit(run)
    return jid


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found (it may have expired).")
    end = job["finished"] or time.time()
    return {**{k: v for k, v in job.items() if k not in ("started", "finished")},
            "elapsed": round(end - job["started"], 1)}


# ---------------------------------------------------------------- helpers

def _split_allergies(text: str) -> list[str]:
    return [a.strip() for a in (text or "").split(",") if a.strip()]


def _salts_text(salts) -> str:
    return " + ".join(f"{s.get('salt', '')} {s.get('strength', '') or ''}".strip() for s in salts or []
                      if isinstance(s, dict)) or "salts unknown"


def _get_case(case_id: int) -> dict:
    row = store.get_case(case_id)
    if row is None:
        raise HTTPException(404, "Case not found.")
    return row


def _get_med(payload: dict, med_index: int) -> dict:
    meds = payload.get("meds") or []
    if not 0 <= med_index < len(meds):
        raise HTTPException(404, "Medicine not found in this case.")
    return meds[med_index]


def _get_escalation(eid: int) -> dict:
    esc = store.get_escalation(eid)
    if esc is None:
        raise HTTPException(404, "Escalation not found.")
    return esc


def _kind(esc: dict) -> str:
    return "symptom" if (esc.get("med_index") is not None and esc["med_index"] < 0) else "medicine"


def _esc_summary(esc: dict) -> dict:
    msgs = store.messages(esc["id"])
    return {"id": esc["id"], "kind": _kind(esc), "case_id": esc["case_id"], "med_index": esc["med_index"],
            "raw_text": esc["raw_text"], "status": esc["status"], "resolution": esc["resolution"],
            "created_at": esc["created_at"], "message_count": len(msgs),
            "last_message": msgs[-1] if msgs else None}


def _case_view(row: dict) -> dict:
    payload = dict(row["payload"] or {})
    payload.pop("image_path", None)  # a server path; the app uses image_url
    has_image = bool(row.get("image_path")) and Path(row["image_path"]).exists()
    return {"id": row["id"], "created_at": row["created_at"],
            "kind": payload.get("kind") or "prescription",
            "image_url": f"/api/cases/{row['id']}/image" if has_image else None,
            "case": payload,
            "escalations": [_esc_summary(e) for e in store.list_for_case(row["id"])]}


async def _read_upload(f: UploadFile | None) -> bytes | None:
    if f is None:
        return None
    data = await f.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, f"{f.filename or 'Upload'} is larger than 15 MB.")
    return data or None


# ---------------------------------------------------------------- meta

@app.get("/api/health")
def health():
    return {"ok": True, "service": "aushnexa", **llm.backend_info()}


class SettingsIn(BaseModel):
    backend: Literal["gemini", "ollama"]


def _settings() -> dict:
    gemini_model = os.environ.get("GEMMA_MODEL") or "gemma-4-26b-a4b-it"
    ollama_model = os.environ.get("OLLAMA_MODEL") or "gemma4:e4b"
    return {**llm.backend_info(),
            "fallback_to_local": os.environ.get("GEMMA_FALLBACK", "").strip().lower() == "ollama",
            "gemini_key_set": (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "")
                              not in ("", "your-ai-studio-key"),  # the old .env.example placeholder
            "options": [{"id": "gemini", "label": "Gemini API", "model": gemini_model},
                        {"id": "ollama", "label": "Local Ollama", "model": ollama_model}]}


@app.get("/api/settings")
def get_settings():
    return _settings()


@app.put("/api/settings")
def put_settings(body: SettingsIn):
    os.environ["LLM_BACKEND"] = body.backend  # core/llm.py reads it at call time
    return _settings()


@app.get("/api/demo")
def demo():
    ctx, al, typed = DEMO / "context.txt", DEMO / "allergies.txt", DEMO / "typed_rx.txt"
    return {"context": ctx.read_text().strip() if ctx.exists() else "",
            "allergies": al.read_text().strip() if al.exists() else "penicillin",
            "typed_rx": typed.read_text().strip() if typed.exists() else "",
            "prescription_url": "/api/demo/prescription.jpg", "strip_url": "/api/demo/strip.jpg"}


@app.get("/api/demo/{name}")
def demo_file(name: str):
    path = DEMO / name
    if name not in DEMO_FILES or not path.exists():
        raise HTTPException(404, "No such demo file.")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/testlab")
def testlab():
    results = run_cases()
    return {"results": results, "passed": sum(r["passed"] for r in results), "total": len(results)}


# ---------------------------------------------------------------- prescription check

@app.post("/api/analyze", status_code=202)
async def analyze(context: str = Form(""), allergies: str = Form(""), rx_text: str = Form(""),
                  use_demo_images: bool = Form(False),
                  rx_image: UploadFile | None = File(None), strip_image: UploadFile | None = File(None)):
    """Start a prescription check. Typed text (one medicine per line) wins over a photo."""
    rx_bytes, strip_bytes = await _read_upload(rx_image), await _read_upload(strip_image)
    if use_demo_images:
        rx_bytes = rx_bytes or (DEMO / "prescription.jpg").read_bytes()
        strip_bytes = strip_bytes or (DEMO / "strip.jpg").read_bytes()
    typed = rx_text.strip()[:MAX_TEXT] or None
    if not typed and rx_bytes is None:
        raise HTTPException(400, "Add a prescription photo or type the medicines first.")
    context = context.strip()[:MAX_TEXT]
    allergy_list = _split_allergies(allergies)

    def work(on_step):
        case = pipeline.analyze(context, allergy_list, rx_image=None if typed else rx_bytes, rx_text=typed,
                                strip_image=strip_bytes, on_step=on_step)
        image_path = store.save_upload(rx_bytes) if (rx_bytes is not None and not typed) else None
        case_id = store.save_case(context, allergy_list, image_path, case)
        return {"case_id": case_id}

    return {"job_id": _start_job("analyze", work)}


@app.get("/api/cases/{case_id}")
def get_case(case_id: int):
    return _case_view(_get_case(case_id))


@app.get("/api/cases/{case_id}/image")
def case_image(case_id: int):
    path = _get_case(case_id).get("image_path")
    if not path or not Path(path).exists():
        raise HTTPException(404, "This case has no photo.")
    return FileResponse(path, media_type="image/jpeg")


class PickIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@app.post("/api/cases/{case_id}/meds/{med_index}/pick")
def pick(case_id: int, med_index: int, body: PickIn):
    """The patient picks one of the candidates for a MEDIUM medicine. Only the code checks re-run."""
    with _case_lock:
        row = _get_case(case_id)
        med = _get_med(row["payload"], med_index)
        if med.get("status") == "confirmed_by_doctor":
            raise HTTPException(409, "A doctor has already confirmed this medicine.")
        if body.name not in [c.get("name") for c in med.get("candidates") or []]:
            raise HTTPException(400, "Pick one of the listed candidates.")
        case = pipeline.recheck(pipeline.apply_resolution(row["payload"], med_index, {"name": body.name}, by="patient"))
        store.update_case(case_id, case)
    return _case_view(_get_case(case_id))


def _ask_doctor_message(case: dict, med: dict) -> str:
    cands = med.get("candidates") or []
    cand_txt = ", ".join(f"{c.get('name')} ({_salts_text(c.get('salts'))})" for c in cands) or "none found"
    reasons = "; ".join((med.get("confidence") or {}).get("reasons") or []) or "n/a"
    return (f"AushNexa could not confidently read line {med['index'] + 1}: '{med['read'].get('raw_text', '')}'. "
            f"Top candidates: {cand_txt}. Patient context: {case.get('context') or 'not given'}. "
            f"Allergies: {', '.join(case.get('allergies') or []) or 'none'}. Reasons: {reasons}.")


@app.post("/api/cases/{case_id}/meds/{med_index}/ask-doctor")
def ask_doctor(case_id: int, med_index: int):
    """Open (or return the already open) doctor chat for one medicine."""
    row = _get_case(case_id)
    case = row["payload"]
    med = _get_med(case, med_index)
    if med.get("status") == "confirmed_by_doctor":
        raise HTTPException(409, "A doctor has already confirmed this medicine.")
    existing = next((e for e in store.list_for_case(case_id) if e["med_index"] == med_index and e["status"] == "open"),
                    None)
    if existing:
        return {"escalation_id": existing["id"], "case": _case_view(row)}
    eid = store.open_escalation(case_id, med_index, med["read"].get("raw_text", ""), med.get("candidates") or [],
                                case.get("context", ""))
    store.add_message(eid, "system", _ask_doctor_message(case, med))
    return {"escalation_id": eid, "case": _case_view(_get_case(case_id))}


# ---------------------------------------------------------------- symptom check

class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)


@app.post("/api/triage", status_code=202)
def start_triage(body: TextIn):
    """Warning-sign rules answer instantly (code); the Gemma 4 triage runs as a job."""
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Record or type your symptoms first.")

    def work(on_step):
        on_step("Checking warning signs…")
        on_step("Gemma 4 is thinking about possible causes…")
        result = triage.triage(text)
        on_step("Done")
        case_id = store.save_case(text, "", None, {"kind": "symptom_check", "transcript": text, **result})
        return {"case_id": case_id, "text": text, "triage": result}

    return {"job_id": _start_job("triage", work), "red_flags": triage.match_red_flags(text)}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Speech to text with local Whisper (English / Hindi). Accepts WAV, m4a (phones) and webm (browsers)."""
    data = await _read_upload(audio)
    if not data:
        raise HTTPException(400, "No audio recorded.")
    return await run_in_threadpool(stt.transcribe, data)


def _symptom_message(text: str, t: dict) -> str:
    g = t.get("gemma") or {}
    flags = "; ".join(f["message"] for f in t.get("red_flags") or []) or "none"
    causes = ", ".join(c["name"] for c in g.get("possible_causes") or []) or "n/a"
    return (f"Symptom check: {t.get('urgency')}. Patient says: \"{text}\". Red flags: {flags}. "
            f"Possible causes (AI, not diagnosis): {causes}.")


@app.post("/api/cases/{case_id}/ask-doctor")
def ask_doctor_symptoms(case_id: int):
    """Open (or return the already open) doctor chat for a symptom check."""
    row = _get_case(case_id)
    payload = row["payload"] or {}
    if payload.get("kind") != "symptom_check":
        raise HTTPException(400, "Use /meds/{index}/ask-doctor for a prescription case.")
    existing = next((e for e in store.list_for_case(case_id) if e["status"] == "open"), None)
    if existing:
        return {"escalation_id": existing["id"]}
    text = payload.get("transcript") or row.get("context") or ""
    eid = store.open_escalation(case_id, -1, text, [], text)
    store.add_message(eid, "system", _symptom_message(text, payload))
    return {"escalation_id": eid}


# ---------------------------------------------------------------- doctor chat

@app.get("/api/escalations")
def list_escalations(status: Literal["open", "resolved", "all"] = "open"):
    return [_esc_summary(e) for e in store.list_escalations(None if status == "all" else status)]


@app.get("/api/escalations/{eid}")
def get_escalation(eid: int):
    """Everything the doctor (or the patient's chat screen) needs for one escalation."""
    esc = _get_escalation(eid)
    row = store.get_case(esc["case_id"]) if esc.get("case_id") else None
    payload = (row or {}).get("payload") or {}
    out = {**_esc_summary(esc), "messages": store.messages(eid), "context": esc.get("context") or "",
           "allergies": (row or {}).get("allergies") or "", "candidates": esc["candidates"],
           "image_url": None, "med": None, "triage": None}
    if row and row.get("image_path") and Path(row["image_path"]).exists():
        out["image_url"] = f"/api/cases/{row['id']}/image"
    if _kind(esc) == "symptom":
        out["triage"] = {k: payload.get(k) for k in ("urgency", "urgency_source", "red_flags", "gemma")}
    else:
        meds = payload.get("meds") or []
        if esc["med_index"] is not None and esc["med_index"] < len(meds):
            out["med"] = meds[esc["med_index"]]
    return out


class MessageIn(BaseModel):
    sender: Literal["patient", "doctor"]
    text: str = Field(min_length=1, max_length=MAX_TEXT)


@app.post("/api/escalations/{eid}/messages", status_code=201)
def post_message(eid: int, body: MessageIn):
    esc = _get_escalation(eid)
    if esc["status"] != "open":
        raise HTTPException(409, "This chat is closed.")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Type a message first.")
    store.add_message(eid, body.sender, text)
    return {"messages": store.messages(eid)}


class ResolveIn(BaseModel):
    name: str | None = Field(None, max_length=200)
    free_text: str | None = Field(None, max_length=200)


@app.post("/api/escalations/{eid}/resolve")
def resolve(eid: int, body: ResolveIn):
    """The doctor confirms a candidate (name) or types the right medicine (free_text). The patient's case is
    updated here and only the code checks re-run. A symptom chat is simply marked answered."""
    esc = _get_escalation(eid)
    if esc["status"] != "open":
        raise HTTPException(409, "This escalation is already resolved.")
    name, free = (body.name or "").strip(), (body.free_text or "").strip()
    if _kind(esc) == "symptom":
        store.resolve(eid, {"answered": True})
        store.add_message(eid, "doctor", "Marked as answered.")
        return _esc_summary(_get_escalation(eid))
    if not name and not free:
        raise HTTPException(400, "Confirm a candidate or type the correct medicine.")
    resolution = {"name": name} if name else {"free_text": free}
    with _case_lock:
        row = store.get_case(esc["case_id"]) if esc.get("case_id") else None
        if row and 0 <= esc["med_index"] < len((row["payload"] or {}).get("meds") or []):
            case = pipeline.recheck(pipeline.apply_resolution(row["payload"], esc["med_index"], resolution, by="doctor"))
            store.update_case(row["id"], case)
        store.resolve(eid, resolution)
    store.add_message(eid, "doctor", f"Confirmed: {name or free}")
    return _esc_summary(_get_escalation(eid))


# ---------------------------------------------------------------- website (must stay last)

@app.get("/{path:path}", include_in_schema=False)
def website(path: str):
    """The exported web app, when built. Other paths fall back to index.html so deep links such as /report or
    /doctor/3 open the right screen."""
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "Not found.")
    root = WEB_DIR.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise HTTPException(404, "The website is not built yet. Run: cd mobile && npx expo export --platform web")
    target = (root / path).resolve()
    if path and target.is_file() and target.is_relative_to(root):
        return FileResponse(target)
    return FileResponse(index)
