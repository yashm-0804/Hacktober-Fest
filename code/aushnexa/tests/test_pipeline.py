import json

from core import pipeline


def test_parse_typed_basic():
    r = pipeline.parse_typed("Dolo 650 TDS x 5 days")[0]
    assert r == {"raw_text": "Dolo 650 TDS x 5 days", "brand_or_drug": "Dolo 650", "form": None,
                 "strength": "650", "dose_and_frequency": "TDS", "duration": "5 days", "unsure": False}


def test_parse_typed_multi_and_units():
    rs = pipeline.parse_typed("Dolo 650 TDS\nCombiflam SOS\n\nTab Augmentin 625mg BD for 5 days\nCalcimax HS")
    assert [r["brand_or_drug"] for r in rs] == ["Dolo 650", "Combiflam", "Augmentin 625mg", "Calcimax"]
    assert [r["dose_and_frequency"] for r in rs] == ["TDS", "SOS", "BD", "HS"]
    assert rs[1]["strength"] is None
    assert rs[2]["strength"] == "625 mg" and rs[2]["form"] == "tablet" and rs[2]["duration"] == "5 days"


def test_parse_typed_no_freq():
    r = pipeline.parse_typed("1. Pan 40")[0]
    assert r["brand_or_drug"] == "Pan 40" and r["strength"] == "40" and r["dose_and_frequency"] == ""


def test_analyze_typed_with_stubs_or_real():
    steps = []
    case = pipeline.analyze("fever and body ache", "penicillin", rx_text="Dolo 650 TDS\nCombiflam SOS",
                            on_step=steps.append)
    json.dumps(case)  # must be storable
    assert len(case["meds"]) == 2 and len(case["resolved"]) == 2
    for m in case["meds"]:
        assert m["confidence"]["band"] in ("HIGH", "MEDIUM", "LOW")
        assert m["status"] in ("auto", "needs_confirmation")
    assert case["allergies"] == ["penicillin"]
    assert isinstance(case["alerts"], list) and isinstance(case["savings"], float)
    assert case["strip"] is None
    assert any(t["step"].startswith("parse_typed") for t in case["_trace"])
    assert any("safety" in t["step"] for t in case["_trace"])
    assert steps[0].startswith("Parsing") and steps[-1] == "Done"
    assert case["hindi_summary"]


def test_analyze_photo_and_strip_with_stubs_or_real():
    case = pipeline.analyze("fever", [], rx_image=b"img", strip_image=b"strip")
    assert case["input_mode"] == "photo"
    assert case["meds"] or case["errors"]
    if case["strip_resolved"]:
        assert case["strip"]["status"] in ("MATCH", "MISMATCH", "NOT_PRESCRIBED", "ERROR")


def test_apply_resolution_and_recheck():
    case = pipeline.analyze("vitamin D deficiency", [], rx_text="Celemax 500 OD")
    c2 = pipeline.apply_resolution(case, 0, {"free_text": "Calcimax"})
    assert c2["meds"][0]["status"] == "confirmed_by_doctor"
    assert case["meds"][0]["status"] != "confirmed_by_doctor"  # original untouched
    c3 = pipeline.recheck(c2)
    assert c3["resolved"][0]["status"] == "confirmed_by_doctor"
    assert c3["rechecked"] is True
    assert "recheck" in c3["_trace"][-2]["step"]
    # picking an existing candidate by name keeps that candidate
    top = case["meds"][0]["candidates"][0]["name"]
    c4 = pipeline.recheck(pipeline.apply_resolution(case, 0, {"name": top}, by="patient"))
    assert c4["resolved"][0]["label"] == top and c4["meds"][0]["status"] == "picked_by_patient"


# ---------------------------------------------------------------- UI smoke tests (streamlit AppTest)

def _app(path, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("APP_DB", str(tmp_path / "ui.db"))
    from pathlib import Path
    return AppTest.from_file(str(Path(__file__).resolve().parent.parent / path), default_timeout=60)


def test_ui_patient_typed_flow(tmp_path, monkeypatch):
    at = _app("app.py", tmp_path, monkeypatch)
    at.run()
    assert not at.exception
    at.text_area(key="typed_rx").input("Dolo 650 TDS\nCombiflam SOS")
    next(b for b in at.button if b.label == "Analyze prescription").click()
    at.run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown) + " ".join(h.value for h in at.header)
    assert "Step 3" in text and "Dolo 650 TDS" in text
    assert at.session_state.case["meds"][0]["read"]["brand_or_drug"] == "Dolo 650"
    assert any("Hindi" in e.label for e in at.expander)
    assert any("pipeline trace" in e.label for e in at.expander)


def test_ui_ask_doctor_and_doctor_console(tmp_path, monkeypatch):
    from core import pipeline as pl, store
    # Force a LOW band so the Ask-a-doctor path renders, whatever confidence implementation is present.
    real_score = pl.confidence.score
    monkeypatch.setattr(pl.confidence, "score",
                        lambda r, c, f=None: dict(real_score(r, c, f), band="LOW", value=0.3, reasons=["test LOW"]))
    at = _app("app.py", tmp_path, monkeypatch)
    at.run()
    at.text_area(key="typed_rx").input("Celemax 500 OD")
    at.text_area(key="ctx").input("vitamin D deficiency, joint pain")
    next(b for b in at.button if b.label == "Analyze prescription").click()
    at.run()
    assert not at.exception, at.exception
    next(b for b in at.button if "Ask a doctor" in b.label).click()
    at.run()
    assert not at.exception, at.exception
    [esc] = store.list_open()
    msgs = store.messages(esc["id"])
    assert msgs[0]["sender"] == "system" and "could not confidently read line 1" in msgs[0]["text"]

    doc = _app("pages/2_Doctor_Console.py", tmp_path, monkeypatch)
    doc.run()
    assert not doc.exception, doc.exception
    assert doc.title[0].value == "Doctor Console"
    next(b for b in doc.button if b.label == "Open").click()
    doc.run()
    assert not doc.exception, doc.exception
    doc.text_input(key=f"other_{esc['id']}").input("Calcimax")
    next(b for b in doc.button if b.label == "Confirm other").click()
    doc.run()
    assert not doc.exception, doc.exception
    e = store.get_escalation(esc["id"])
    assert e["status"] == "resolved" and e["resolution"] == {"free_text": "Calcimax"}
    assert store.messages(esc["id"])[-1]["text"] == "Confirmed: Calcimax"

    at.run()  # patient page picks up the resolution (fragment -> app rerun)
    at.run()
    assert not at.exception, at.exception
    assert at.session_state.case["meds"][0]["status"] == "confirmed_by_doctor"
    assert at.session_state.case["rechecked"] is True
