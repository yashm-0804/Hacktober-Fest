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
