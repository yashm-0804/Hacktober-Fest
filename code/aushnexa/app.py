"""AushNexa patient page. Gemma reads, code decides, a doctor confirms."""
from __future__ import annotations

import html
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st

from core import llm, pipeline, store
from core.safe_md import safe_md

st.set_page_config(page_title="AushNexa", layout="wide")

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "demo_assets"

BAND_STYLE = {  # colour always paired with a text label + symbol
    "HIGH": ("#166534", "#dcfce7", "HIGH ✓"),
    "MEDIUM": ("#92400e", "#fef3c7", "MEDIUM ⚠"),
    "LOW": ("#991b1b", "#fee2e2", "LOW ✕"),
}
SEV_STYLE = {
    "HIGH": ("#991b1b", "#fee2e2", "HIGH ✕"),
    "REVIEW": ("#92400e", "#fef3c7", "REVIEW ⚠"),
    "INFO": ("#1e3a8a", "#dbeafe", "INFO ℹ"),
}
STRIP_STYLE = {
    "MATCH": ("#166534", "#dcfce7", "MATCH ✓"),
    "MISMATCH": ("#991b1b", "#fee2e2", "MISMATCH ✕"),
    "NOT_PRESCRIBED": ("#991b1b", "#fee2e2", "NOT PRESCRIBED ✕"),
    "ERROR": ("#374151", "#f3f4f6", "COULD NOT CHECK"),
}
STATUS_CHIP = {
    "auto": "Auto-matched",
    "needs_confirmation": "Needs confirmation",
    "awaiting_doctor": "⏳ Awaiting doctor",
    "confirmed_by_doctor": "✅ Confirmed by doctor",
    "picked_by_patient": "☑ Picked by you",
}
SLOTS = ["Morning", "Afternoon", "Night", "Bedtime", "As needed"]

st.markdown(
    """<style>
    html, body, [class*="css"] { font-size: 17px; }
    .ax-badge { display:inline-block; padding:4px 12px; border-radius:6px; font-weight:700; font-size:1rem;
                border:2px solid currentColor; }
    .ax-card { padding:12px 16px; border-radius:8px; margin:6px 0; border-left:8px solid currentColor; }
    .ax-big { font-size:1.6rem; font-weight:800; }
    .ax-raw { font-family: ui-monospace, Menlo, monospace; background:#f3f4f6; color:#111827;
              padding:2px 8px; border-radius:4px; font-size:1.05rem; }
    </style>""",
    unsafe_allow_html=True,
)


def badge(style: tuple) -> str:
    fg, bg, label = style
    return f'<span class="ax-badge" style="color:{fg};background:{bg}">{html.escape(label)}</span>'


def salts_text(salts) -> str:
    out = []
    for s in salts or []:
        if isinstance(s, dict):
            out.append(f"{s.get('salt', '')} {s.get('strength', '') or ''}".strip())
        else:
            out.append(str(s))
    return " + ".join(out) or "salts unknown"


def ss_init():
    for k, v in {"case": None, "case_id": None, "esc": {}, "demo_rx": None, "demo_strip": None,
                 "ctx": "", "allergy_text": "", "typed_rx": ""}.items():
        st.session_state.setdefault(k, v)


ss_init()
if st.session_state.get("voice_context"):  # handed over from the Symptom Check page, applied once
    st.session_state.ctx = st.session_state.pop("voice_context")


# ------------------------------------------------------------------ sidebar

def load_demo():
    ctx_f, al_f = DEMO / "context.txt", DEMO / "allergies.txt"
    if ctx_f.exists():
        st.session_state.ctx = ctx_f.read_text().strip()
    st.session_state.allergy_text = al_f.read_text().strip() if al_f.exists() else "penicillin"
    rx, strip = DEMO / "prescription.jpg", DEMO / "strip.jpg"
    st.session_state.demo_rx = rx.read_bytes() if rx.exists() else None
    st.session_state.demo_strip = strip.read_bytes() if strip.exists() else None


def clear_demo():
    st.session_state.demo_rx = None
    st.session_state.demo_strip = None


with st.sidebar:
    st.header("Settings")
    default_idx = 1 if os.environ.get("LLM_BACKEND", "gemini").lower() == "ollama" else 0
    backend = st.radio("Gemma 4 backend", ["Gemini API", "Local Ollama"], index=default_idx, key="backend")
    os.environ["LLM_BACKEND"] = "ollama" if backend == "Local Ollama" else "gemini"
    try:
        info = llm.backend_info()
    except Exception as e:  # noqa: BLE001
        info = {"backend": "?", "model": f"unavailable ({e})"}
    st.caption(f"Backend: **{info.get('backend')}** · Model: `{info.get('model')}`")
    st.divider()
    st.button("Load demo case", on_click=load_demo, width="stretch", type="primary")
    if st.session_state.demo_rx or st.session_state.demo_strip:
        st.caption("Synthetic demo prescription loaded.")
        st.button("Clear demo images", on_click=clear_demo, width="stretch")
    st.divider()
    st.caption("Brand data: junioralive/Indian-Medicine-Dataset (MIT). Jan Aushadhi prices indicative.")


# ------------------------------------------------------------------ header + inputs

st.title("AushNexa — prescription safety for Indian brand medicines")
st.caption("Powered by Gemma 4 (gemma-4-26b-a4b-it) via the Gemini API. Gemma reads, code decides, a doctor confirms.")

st.subheader("Step 1 · Patient context")
c1, c2 = st.columns([3, 2])
with c1:
    st.text_area("Symptoms / condition", key="ctx", height=100,
                 placeholder="e.g. fever and body ache for 3 days; known vitamin D deficiency with joint pain")
with c2:
    st.text_input("Allergies (comma-separated)", key="allergy_text", placeholder="e.g. penicillin, sulfa")

st.subheader("Step 2 · Prescription")
tab_photo, tab_typed = st.tabs(["Photo", "Type it"])
with tab_photo:
    up = st.file_uploader("Prescription photo", type=["jpg", "jpeg", "png", "webp"], key="rx_upload")
    use_cam = st.toggle("Use camera instead", key="use_cam")
    cam = st.camera_input("Take a photo of the prescription", key="rx_cam") if use_cam else None
    if st.session_state.demo_rx and not up and not cam:
        st.image(st.session_state.demo_rx, caption="Synthetic demo prescription", width=420)
with tab_typed:
    st.text_area("One medicine per line", key="typed_rx", height=120,
                 placeholder="Dolo 650 TDS x 5 days\nCombiflam SOS\nCelemax 500 OD")
    st.caption("If text is entered here, it is used instead of the photo (no Gemma read needed).")

strip_up = st.file_uploader("Medicine strip/box photo (optional): what the pharmacy gave you",
                            type=["jpg", "jpeg", "png", "webp"], key="strip_upload")
if st.session_state.demo_strip and not strip_up:
    st.image(st.session_state.demo_strip, caption="Synthetic demo medicine strip", width=260)


def current_inputs():
    rx_bytes = None
    if cam is not None:
        rx_bytes = cam.getvalue()
    elif up is not None:
        rx_bytes = up.getvalue()
    elif st.session_state.demo_rx:
        rx_bytes = st.session_state.demo_rx
    strip_bytes = strip_up.getvalue() if strip_up is not None else st.session_state.demo_strip
    typed = (st.session_state.typed_rx or "").strip() or None
    return rx_bytes, typed, strip_bytes


def run_analysis():
    rx_bytes, typed, strip_bytes = current_inputs()
    if not typed and rx_bytes is None:
        st.warning("Add a prescription photo or type the medicines first.")
        return
    allergies = [a.strip() for a in (st.session_state.allergy_text or "").split(",") if a.strip()]
    steps: list[str] = []
    t0 = time.time()
    with st.status("Starting…", expanded=True) as status:
        shown = 0
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(pipeline.analyze, st.session_state.ctx, allergies,
                            rx_image=None if typed else rx_bytes, rx_text=typed,
                            strip_image=strip_bytes, on_step=steps.append)
            while True:
                done = fut.done()
                while shown < len(steps):
                    st.write(f"• {steps[shown]}  ({time.time() - t0:.0f}s)")
                    shown += 1
                label = steps[-1] if steps else "Starting…"
                status.update(label=f"{label}  · {time.time() - t0:.0f}s elapsed")
                if done:
                    break
                time.sleep(0.5)
            case = fut.result()
        errs = case.get("errors") or []
        status.update(label=f"Analysis finished in {time.time() - t0:.1f}s" + (" (with warnings)" if errs else ""),
                      state="error" if errs and not case.get("meds") else "complete", expanded=bool(errs))
        for e in errs:
            st.warning(e)
    image_path = store.save_upload(rx_bytes) if (rx_bytes is not None and not typed) else None
    case["image_path"] = image_path
    st.session_state.case = case
    st.session_state.case_id = store.save_case(st.session_state.ctx, allergies, image_path, case)
    st.session_state.esc = {}


if st.button("Analyze prescription", type="primary", width="stretch"):
    run_analysis()


# ------------------------------------------------------------------ escalation

def ask_doctor(i: int):
    case = st.session_state.case
    med = case["meds"][i]
    cands = med["candidates"]
    cand_txt = ", ".join(f"{c.get('name')} ({salts_text(c.get('salts'))})" for c in cands) or "none found"
    reasons = "; ".join((med.get("confidence") or {}).get("reasons") or []) or "n/a"
    msg = (f"AushNexa could not confidently read line {i + 1}: '{med['read'].get('raw_text', '')}'. "
           f"Top candidates: {cand_txt}. Patient context: {case.get('context') or 'not given'}. "
           f"Allergies: {', '.join(case.get('allergies') or []) or 'none'}. Reasons: {reasons}.")
    eid = store.open_escalation(st.session_state.case_id, i, med["read"].get("raw_text", ""),
                                cands, case.get("context", ""))
    store.add_message(eid, "system", msg)
    st.session_state.esc[str(i)] = eid


def patient_pick(i: int):
    choice = st.session_state.get(f"pick_{i}")
    if not choice:
        return
    case = pipeline.apply_resolution(st.session_state.case, i, {"name": choice}, by="patient")
    case = pipeline.recheck(case)
    st.session_state.case = case
    if st.session_state.case_id:
        store.update_case(st.session_state.case_id, case)


@st.fragment(run_every=3)
def doctor_chat_panel():
    esc = st.session_state.esc
    if not esc:
        return
    st.subheader("Ask a doctor · chat")
    st.caption("Demo: a teammate plays the consultant on the Doctor Console page. This panel refreshes every 3 s.")
    changed = False
    for key, eid in list(esc.items()):
        i = int(key)
        e = store.get_escalation(eid)
        if e is None:
            continue
        med = st.session_state.case["meds"][i]
        if e["status"] == "resolved" and med.get("status") != "confirmed_by_doctor":
            case = pipeline.apply_resolution(st.session_state.case, i, e.get("resolution") or {}, by="doctor")
            case = pipeline.recheck(case)
            st.session_state.case = case
            if st.session_state.case_id:
                store.update_case(st.session_state.case_id, case)
            changed = True
            continue
        with st.container(border=True):
            state = "✅ Resolved" if e["status"] == "resolved" else "⏳ Open, waiting for a doctor"
            st.markdown(f"**Line {i + 1}: `{html.escape(e['raw_text'] or '')}`** · {state}")
            for m in store.messages(eid):
                role = {"patient": "user", "doctor": "assistant", "system": "assistant"}.get(m["sender"], "assistant")
                avatar = {"patient": "🧑", "doctor": "🩺", "system": "⚙️"}.get(m["sender"])
                with st.chat_message(role, avatar=avatar):
                    st.markdown(f"**{m['sender'].title()}:** {safe_md(m['text'])}")
            if e["status"] == "open":
                txt = st.chat_input("Message the doctor…", key=f"pchat_{eid}")
                if txt:
                    store.add_message(eid, "patient", txt)
                    st.rerun(scope="fragment")
    if changed:
        st.rerun(scope="app")


# ------------------------------------------------------------------ results

def med_status(med: dict) -> str:
    s = med.get("status", "auto")
    if s == "needs_confirmation" and str(med["index"]) in st.session_state.esc:
        return "awaiting_doctor"
    return s


def render_med(med: dict):
    i = med["index"]
    read, cands = med["read"], med["candidates"]
    conf = med.get("confidence") or {}
    band = conf.get("band", "LOW")
    status = med_status(med)
    resolved = st.session_state.case["resolved"][i]
    with st.container(border=True):
        a, b, c = st.columns([3, 4, 2])
        with a:
            st.markdown(f"**{i + 1}.** <span class='ax-raw'>{html.escape(read.get('raw_text') or '')}</span>",
                        unsafe_allow_html=True)
            st.caption(f"Read as: {read.get('brand_or_drug') or '?'} · strength {read.get('strength') or '?'} · "
                       f"{read.get('dose_and_frequency') or 'no frequency'}"
                       + (" · Gemma marked UNSURE" if read.get("unsure") else ""))
        with b:
            st.markdown(f"→ **{html.escape(resolved.get('label') or 'No match')}**")
            st.caption(salts_text(resolved.get("salts")))
        with c:
            if status in ("confirmed_by_doctor", "picked_by_patient"):
                st.markdown(badge(("#166534", "#dcfce7", STATUS_CHIP[status])), unsafe_allow_html=True)
            else:
                st.markdown(badge(BAND_STYLE.get(band, BAND_STYLE["LOW"])), unsafe_allow_html=True)
                st.caption(f"{STATUS_CHIP.get(status, status)} · score {conf.get('value', 0):.2f}")

        with st.expander("Why?"):
            for r in conf.get("reasons") or []:
                st.markdown(f"- {r}")
            if conf.get("breakdown"):
                st.dataframe(pd.DataFrame([conf["breakdown"]]), hide_index=True)
            if conf.get("lasa_rival"):
                rv = conf["lasa_rival"]
                st.markdown(f"**Look-alike rival:** {rv.get('name')} ({salts_text(rv.get('salts'))})")
            rows = []
            for cnd in cands:
                f = (med.get("fits") or {}).get(cnd.get("name")) or {}
                rows.append({"Candidate": cnd.get("name"), "Salts": salts_text(cnd.get("salts")),
                             "Match score": round(float(cnd.get("score") or 0), 1),
                             "Fits patient? (Gemma)": f.get("fits", "n/a"), "Gemma note": f.get("reason", "")})
            if rows:
                st.markdown("**Top candidates**")
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        if status in ("confirmed_by_doctor", "picked_by_patient"):
            return
        names = [cnd.get("name") for cnd in cands]
        if band == "MEDIUM" and names:
            p1, p2 = st.columns([3, 1])
            with p1:
                st.radio("Pick the right medicine", names, key=f"pick_{i}", horizontal=True)
                st.button("Use this medicine", key=f"use_{i}", on_click=patient_pick, args=(i,))
            with p2:
                if status != "awaiting_doctor":
                    st.button("Ask a doctor", key=f"ask_{i}", on_click=ask_doctor, args=(i,))
        elif band == "LOW" and status != "awaiting_doctor":
            st.error("We could not read this medicine confidently. A doctor should confirm it before you take it.")
            st.button("🩺 Ask a doctor", key=f"ask_{i}", on_click=ask_doctor, args=(i,), type="primary",
                      width="stretch")


def render_results(case: dict):
    st.divider()
    st.header("Step 3 · Results")
    if not case.get("meds"):
        st.error("No medicines could be read. Try the **Type it** tab, or a clearer photo.")
        return

    st.subheader("Medicines")
    for med in case["meds"]:
        render_med(med)

    doctor_chat_panel()

    st.subheader("Safety alerts")
    alerts = case.get("alerts") or []
    if not alerts:
        st.info("No alerts from our checks. No alert ≠ safe. Please review with your doctor or pharmacist.")
    for al in alerts:
        fg, bg, label = SEV_STYLE.get(al.get("severity"), SEV_STYLE["INFO"])
        st.markdown(
            f"<div class='ax-card' style='color:{fg};background:{bg}'>{badge((fg, bg, label))} "
            f"<b style='color:#111827'>{html.escape(al.get('type', ''))}: {html.escape(al.get('title', ''))}</b>"
            f"<div style='color:#111827;margin-top:6px'>{html.escape(al.get('detail', ''))}</div></div>",
            unsafe_allow_html=True)

    st.subheader("Strip check")
    strip = case.get("strip")
    if strip:
        fg, bg, label = STRIP_STYLE.get(strip.get("status"), STRIP_STYLE["ERROR"])
        sr = case.get("strip_resolved") or {}
        st.markdown(
            f"<div class='ax-card' style='color:{fg};background:{bg}'><span class='ax-big'>{html.escape(label)}</span>"
            f"<div style='color:#111827;margin-top:6px'>Strip: <b>{html.escape(str(sr.get('label') or '?'))}</b> "
            f"{html.escape(str(sr.get('strength') or ''))}<br>{html.escape(strip.get('detail', ''))}</div></div>",
            unsafe_allow_html=True)
    else:
        st.caption("No strip photo added. Upload the strip or box the pharmacy gave you to check it.")

    st.subheader("Dose schedule")
    rows = []
    sched = case.get("schedule") or []
    extra = [x for s in sched for x in (s.get("slots") or []) if x not in SLOTS]
    cols = SLOTS + list(dict.fromkeys(extra))  # keep any slot names safety.schedule() adds
    for s in sched:
        slots = set(s.get("slots") or [])
        row = {"Medicine": s.get("label"), "Frequency": s.get("freq") or "?"}
        for slot in cols:
            row[slot] = "✓ yes" if slot in slots else ""
        rows.append(row)
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Jan Aushadhi generics (indicative)")
    ja_rows = []
    for j in case.get("jan_aushadhi") or []:
        g = j.get("generic") or {}
        ja_rows.append({"Brand": j.get("brand"),
                        "Brand ₹": j.get("brand_price"),
                        "Jan Aushadhi generic": g.get("generic_name", "not in our list"),
                        "Generic ₹ (indicative)": g.get("price"),
                        "Pack": g.get("pack", "")})
    if ja_rows:
        st.dataframe(pd.DataFrame(ja_rows), hide_index=True, width="stretch")
    st.metric("Estimated savings", f"Save about ₹{case.get('savings', 0):.0f}/month")
    st.caption("Indicative prices; verify at janaushadhi.gov.in.")

    with st.expander("Hindi summary (हिंदी सारांश)", expanded=True):
        st.markdown(safe_md(case.get("hindi_summary")) or "Not available.")

    with st.expander("How Gemma 4 + code decided (pipeline trace)"):
        tr = [{"Step": t.get("step"), "Model / backend": f"{t.get('model')} / {t.get('backend')}",
               "Seconds": t.get("seconds"), "Cache hit": "yes" if t.get("cache_hit") else "no",
               "Error": t.get("error") or ""} for t in case.get("_trace") or []]
        if tr:
            st.dataframe(pd.DataFrame(tr), hide_index=True, width="stretch")
        if case.get("rechecked"):
            st.caption("After the confirmation, only the code checks re-ran. No new Gemma call.")


if st.session_state.case:
    render_results(st.session_state.case)

st.divider()
st.caption("Supports medication review. No alert ≠ safe. Not a substitute for a doctor or pharmacist.")
