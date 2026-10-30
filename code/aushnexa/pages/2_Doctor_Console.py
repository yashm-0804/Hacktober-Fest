"""Doctor Console: answer AushNexa escalations by chat and confirm the right medicine."""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from core import store
from core.safe_md import safe_md

st.set_page_config(page_title="AushNexa · Doctor Console", layout="wide")
st.title("Doctor Console")
st.caption("Demo: a teammate plays the consultant. In production this is a licensed doctor/pharmacist.")
st.session_state.setdefault("doc_sel", None)


def salts_text(salts) -> str:
    out = []
    for s in salts or []:
        out.append(f"{s.get('salt', '')} {s.get('strength', '') or ''}".strip() if isinstance(s, dict) else str(s))
    return " + ".join(out) or "salts unknown"


def select(eid: int):
    st.session_state.doc_sel = eid


@st.fragment(run_every=3)
def open_list():
    items = store.list_open()
    st.subheader(f"Open escalations ({len(items)})")
    if not items:
        st.info("No open escalations. When a patient taps **Ask a doctor**, it appears here within 3 seconds.")
        return
    for e in items:
        cols = st.columns([5, 1])
        what = ("🗣 Symptom check" if (e["med_index"] is not None and e["med_index"] < 0)
                else f"line {e['med_index'] + 1}")
        cols[0].markdown(f"**#{e['id']}** · {what}: `{html.escape((e['raw_text'] or '')[:80])}` · "
                         f"{len(store.messages(e['id']))} messages")
        if cols[1].button("Open", key=f"open_{e['id']}", type="primary" if st.session_state.doc_sel == e["id"] else "secondary"):
            select(e["id"])
            st.rerun(scope="app")


def confirm(eid: int, resolution: dict, label: str):
    store.resolve(eid, resolution)
    store.add_message(eid, "doctor", f"Confirmed: {label}")


@st.fragment(run_every=3)
def chat(eid: int):
    e = store.get_escalation(eid)
    for m in store.messages(eid):
        role = "user" if m["sender"] == "patient" else "assistant"
        avatar = {"patient": "🧑", "doctor": "🩺", "system": "⚙️"}.get(m["sender"])
        with st.chat_message(role, avatar=avatar):
            st.markdown(f"**{m['sender'].title()}:** {safe_md(m['text'])}")
    if e and e["status"] == "open":
        txt = st.chat_input("Reply to the patient as the doctor…", key=f"dchat_{eid}")
        if txt:
            store.add_message(eid, "doctor", txt)
            st.rerun(scope="fragment")


def symptom_view(esc: dict):
    """Symptom-check escalation (med_index -1): no photo and no candidates, so show the transcript + triage, then chat."""
    case = store.get_case(esc["case_id"]) if esc.get("case_id") else None
    t = (case or {}).get("payload") or {}
    g = t.get("gemma") or {}
    status = "✅ Resolved" if esc["status"] == "resolved" else "⏳ Open"
    st.header(f"Escalation #{esc['id']} · Symptom check · {status}")
    st.markdown(f"**Patient says:** {html.escape(esc.get('raw_text') or '')}")
    st.markdown(f"**AushNexa urgency:** {t.get('urgency', '?')} (from {t.get('urgency_source', '?')})")
    for f in t.get("red_flags") or []:
        st.markdown(f"- 🚩 **{f.get('id')}** ({f.get('level')}): {safe_md(f.get('message'))}")
    if g.get("possible_causes"):
        st.markdown("**Possible causes (AI, not a diagnosis):** "
                    + "; ".join(f"{safe_md(c.get('name'))} ({safe_md(c.get('why'))})" for c in g["possible_causes"]))
    if g.get("questions_for_doctor"):
        st.markdown("**Patient may ask:** " + " · ".join(safe_md(q) for q in g["questions_for_doctor"]))
    st.subheader("Chat with the patient")
    chat(esc["id"])


open_list()

eid = st.session_state.doc_sel
esc = store.get_escalation(eid) if eid else None
if esc and esc.get("med_index") is not None and esc["med_index"] < 0:
    st.divider()
    symptom_view(esc)
elif esc:
    st.divider()
    case = store.get_case(esc["case_id"]) if esc.get("case_id") else None
    payload = (case or {}).get("payload") or {}
    meds = payload.get("meds") or []
    med = meds[esc["med_index"]] if esc["med_index"] is not None and esc["med_index"] < len(meds) else {}
    status = "✅ Resolved" if esc["status"] == "resolved" else "⏳ Open"
    st.header(f"Escalation #{esc['id']} · {status}")

    left, right = st.columns([2, 3])
    with left:
        img = (case or {}).get("image_path")
        if img and Path(img).exists():
            st.image(img, caption="Patient's prescription photo", width="stretch")
        else:
            st.caption("No photo (typed prescription).")
    with right:
        st.markdown(f"**Line {esc['med_index'] + 1} as read:** `{html.escape(esc['raw_text'] or '')}`")
        st.markdown(f"**Patient context:** {safe_md(esc.get('context')) or 'not given'}")
        if case:
            st.markdown(f"**Allergies:** {case.get('allergies') or 'none'}")
        conf = med.get("confidence") or {}
        if conf:
            st.markdown(f"**AushNexa confidence:** {conf.get('band', '?')} ({conf.get('value', 0):.2f})")
            for r in conf.get("reasons") or []:
                st.markdown(f"- {r}")
        fits = med.get("fits") or {}
        rows = [{"Candidate": c.get("name"), "Salts": salts_text(c.get("salts")),
                 "Match score": round(float(c.get("score") or 0), 1),
                 "Fits patient? (Gemma)": (fits.get(c.get("name")) or {}).get("fits", "n/a"),
                 "Gemma fit note": (fits.get(c.get("name")) or {}).get("reason", "")}
                for c in esc["candidates"]]
        st.markdown("**Top candidates**")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Chat with the patient")
    chat(esc["id"])

    if esc["status"] == "open":
        st.subheader("Confirm the medicine")
        bcols = st.columns(max(1, len(esc["candidates"])))
        for k, c in enumerate(esc["candidates"]):
            if bcols[k].button(f"Confirm: {c.get('name')}", key=f"conf_{esc['id']}_{k}", width="stretch"):
                confirm(esc["id"], {"name": c.get("name")}, c.get("name"))
                st.rerun()
        o1, o2 = st.columns([3, 1])
        other = o1.text_input("Other medicine (type the correct name)", key=f"other_{esc['id']}",
                              placeholder="e.g. Calcimax")
        if o2.button("Confirm other", key=f"confother_{esc['id']}", type="primary", width="stretch"):
            if other.strip():
                confirm(esc["id"], {"free_text": other.strip()}, other.strip())
                st.rerun()
            else:
                st.warning("Type a medicine name first.")
    else:
        st.success(f"Resolved: {esc.get('resolution')}. The patient's page updates within 3 seconds.")
