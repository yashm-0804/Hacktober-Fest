"""Symptom Check: speak or type symptoms. Whisper transcribes, code red-flag rules + Gemma 4 triage."""
from __future__ import annotations

import hashlib
import html
import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from core import store, stt, triage
from core.safe_md import safe_md

st.set_page_config(page_title="AushNexa · Symptom Check", layout="wide")

MAPS_URL = "https://www.google.com/maps/search/?api=1&query=hospitals+near+me"
URG_STYLE = {  # (fg, bg, text label, action). Colour is always paired with a text label.
    "EMERGENCY": ("#991b1b", "#fee2e2", "EMERGENCY ✕", "Call 108 (ambulance) / 112 now"),
    "URGENT": ("#9a3412", "#ffedd5", "URGENT ⚠", "See a doctor today"),
    "SEE_DOCTOR": ("#92400e", "#fef3c7", "SEE A DOCTOR ⚠", "Book a doctor visit in the next day or two"),
    "SELF_CARE": ("#166534", "#dcfce7", "SELF-CARE ✓",
                  "Home care is likely enough for now. See a doctor if it gets worse or lasts more than 3 days"),
}

st.markdown(
    """<style>
    html, body, [class*="css"] { font-size: 17px; }
    .ax-badge { display:inline-block; padding:4px 12px; border-radius:6px; font-weight:700; font-size:1rem;
                border:2px solid currentColor; }
    .ax-card { padding:12px 16px; border-radius:8px; margin:6px 0; border-left:8px solid currentColor; }
    .ax-big { font-size:1.6rem; font-weight:800; }
    </style>""",
    unsafe_allow_html=True,
)

for k, v in {"sym_text": "", "sym_audio_hash": None, "sym_stt": None, "sym_result": None, "sym_esc": None}.items():
    st.session_state.setdefault(k, v)

st.title("Symptom Check")
st.caption("Speak or type what you're feeling. AushNexa suggests possible causes and how urgent it is — "
           "it does not diagnose.")

# ------------------------------------------------------------------ input

audio = st.audio_input("Tell us what's wrong", key="sym_audio")
if audio is not None:
    wav = audio.getvalue()
    h = hashlib.sha256(wav).hexdigest()
    if h != st.session_state.sym_audio_hash:  # transcribe each new recording once
        with st.spinner("Listening to your recording (Whisper speech-to-text, on this computer)…"):
            res = stt.transcribe(wav)
        st.session_state.sym_audio_hash = h
        st.session_state.sym_stt = res
        if res.get("text"):
            st.session_state.sym_text = res["text"]
res = st.session_state.sym_stt
if res:
    if res.get("error"):
        st.warning(res["error"])
    elif res.get("text"):
        lang = {"hi": "Hindi", "en": "English"}.get(res.get("language"), res.get("language") or "?")
        st.caption(f"Heard in {lang} in {res.get('seconds', 0):.1f}s. Check the text below and fix anything we got wrong.")

st.text_area("What are you feeling? (you can also type here)", key="sym_text", height=110,
             placeholder="e.g. stomach pain and mild fever since yesterday / seene mein dard ho raha hai")


def run_check():
    text = (st.session_state.sym_text or "").strip()
    if not text:
        st.warning("Record or type your symptoms first.")
        return
    flags = triage.match_red_flags(text)  # instant, code-only: show warning signs before Gemma answers
    t0 = time.time()
    with st.status("Checking your symptoms with Gemma 4…", expanded=bool(flags)) as status:
        if flags:
            st.error("Warning signs found: " + " ".join(f["message"] for f in flags))
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(triage.triage, text)
            while not fut.done():
                status.update(label=f"Checking your symptoms with Gemma 4… {time.time() - t0:.0f}s elapsed")
                time.sleep(0.5)
            result = fut.result()
        status.update(label=f"Checked in {time.time() - t0:.1f}s", state="complete", expanded=False)
    st.session_state.sym_result = {"text": text, "triage": result}
    st.session_state.sym_esc = None


if st.button("Check", type="primary", width="stretch", key="sym_check"):
    run_check()


# ------------------------------------------------------------------ ask a doctor

def system_message(text: str, t: dict) -> str:
    g = t.get("gemma") or {}
    flags = "; ".join(f["message"] for f in t.get("red_flags") or []) or "none"
    causes = ", ".join(c["name"] for c in g.get("possible_causes") or []) or "n/a"
    return (f"Symptom check: {t.get('urgency')}. Patient says: \"{text}\". Red flags: {flags}. "
            f"Possible causes (AI, not diagnosis): {causes}.")


def ask_doctor():
    r = st.session_state.sym_result
    text, t = r["text"], r["triage"]
    payload = {"kind": "symptom_check", "transcript": text, **t}
    cid = store.save_case(context=text, allergies="", image_path=None, payload=payload)
    eid = store.open_escalation(cid, -1, text, [], text)
    store.add_message(eid, "system", system_message(text, t))
    st.session_state.sym_esc = eid


@st.fragment(run_every=3)
def doctor_chat_panel():
    eid = st.session_state.sym_esc
    if not eid:
        return
    e = store.get_escalation(eid)
    if e is None:
        return
    st.subheader("Ask a doctor · chat")
    st.caption("Demo: a teammate plays the doctor on the Doctor Console page. This panel refreshes every 3 s.")
    with st.container(border=True):
        state = "✅ Answered" if e["status"] == "resolved" else "⏳ Open, waiting for a doctor"
        st.markdown(f"**Your symptom check** · {state}")
        for m in store.messages(eid):
            role = {"patient": "user", "doctor": "assistant", "system": "assistant"}.get(m["sender"], "assistant")
            avatar = {"patient": "🧑", "doctor": "🩺", "system": "⚙️"}.get(m["sender"])
            with st.chat_message(role, avatar=avatar):
                st.markdown(f"**{m['sender'].title()}:** {safe_md(m['text'])}")
        if e["status"] == "open":
            txt = st.chat_input("Message the doctor…", key=f"symchat_{eid}")
            if txt:
                store.add_message(eid, "patient", txt)
                st.rerun(scope="fragment")


# ------------------------------------------------------------------ results

def hospitals_button(prominent: bool):
    st.link_button("🏥 Hospitals near me", MAPS_URL, type="primary" if prominent else "secondary",
                   width="stretch" if prominent else "content")


def render_result(r: dict):
    t = r["triage"]
    g = t.get("gemma") or {}
    urgency = t.get("urgency") or "SEE_DOCTOR"
    fg, bg, label, action = URG_STYLE.get(urgency, URG_STYLE["SEE_DOCTOR"])
    src = {"rules": "warning-sign rules", "gemma": "Gemma 4", "both": "warning-sign rules and Gemma 4",
           "default": "safe default (AI unavailable)"}.get(t.get("urgency_source"), "")
    flag_html = "".join(f"<li>{html.escape(f['message'])}</li>" for f in t.get("red_flags") or [])
    st.divider()
    st.markdown(
        f"<div class='ax-card' style='color:{fg};background:{bg}'>"
        f"<span class='ax-badge' style='color:{fg};background:{bg}'>{html.escape(label)}</span> "
        f"<span class='ax-big'>{html.escape(action)}</span>"
        + (f"<ul style='color:#111827;margin:8px 0 0 0'>{flag_html}</ul>" if flag_html else "")
        + f"<div style='color:#374151;margin-top:6px;font-size:0.9rem'>Urgency from: {html.escape(src)}</div></div>",
        unsafe_allow_html=True)
    prominent = urgency in ("URGENT", "EMERGENCY")
    if prominent:
        hospitals_button(True)
    if t.get("error"):
        st.caption(f"Note: {t['error']}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Possible causes")
        causes = g.get("possible_causes") or []
        if not causes:
            st.caption("Not available. Please talk to a doctor.")
        for c in causes:
            st.markdown(f"- **{safe_md(c['name'])}** · *possible, not a diagnosis*" + (f"  \n  {safe_md(c['why'])}" if c.get("why") else ""))
    with c2:
        st.subheader("What you can do now")
        for s in g.get("self_care") or []:
            st.markdown(f"- {safe_md(s)}")
        if not g.get("self_care"):
            st.caption("No self-care tips available.")
    if g.get("questions_for_doctor"):
        st.subheader("Questions to ask your doctor")
        for q in g["questions_for_doctor"]:
            st.markdown(f"- {safe_md(q)}")

    st.subheader("Next steps")
    a, b, c = st.columns(3)
    with a:
        if st.session_state.sym_esc:
            st.button("🩺 Doctor asked", disabled=True, width="stretch", key="sym_ask_done")
        else:
            st.button("🩺 Ask a doctor", on_click=ask_doctor, width="stretch", key="sym_ask",
                      type="secondary" if prominent else "primary")
    with b:
        if st.button("Use as my prescription context →", width="stretch", key="sym_use"):
            st.session_state["voice_context"] = f"{r['text']} {g.get('summary_for_context') or ''}".strip()
            st.switch_page("app.py")
    with c:
        if not prominent:
            hospitals_button(False)

    doctor_chat_panel()

    with st.expander("How this was decided (trace)"):
        for tr in t.get("_trace") or []:
            st.markdown(f"- `{tr.get('step')}` · {tr.get('model')} / {tr.get('backend')} · {tr.get('seconds')}s"
                        + (f" · error: {tr.get('error')}" if tr.get("error") else ""))
        st.caption("Warning-sign rules run in code first. Gemma 4 can raise the urgency, but code never lowers it.")


if st.session_state.sym_result:
    render_result(st.session_state.sym_result)
else:
    hospitals_button(False)

st.divider()
st.caption("AushNexa suggests possible causes only. It is not a diagnosis and not a substitute for a doctor. "
           "In an emergency call 108 (ambulance) or 112. Mental health support: Tele-MANAS 14416 (free, 24x7).")
