import io
import shutil
import subprocess
import struct
import wave
from pathlib import Path

import pytest

from core import stt, store, triage

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB", str(tmp_path / "t.db"))


def ids(text):
    return [f["id"] for f in triage.match_red_flags(text)]


def fake_gemma(urgency="SEE_DOCTOR", **extra):
    def _fn(prompt, step="triage", image=None):
        assert "<patient>" in prompt
        return {"possible_causes": [{"name": "Viral fever", "why": "fever"}, "Dehydration"], "self_care": ["Rest"],
                "urgency": urgency, "questions_for_doctor": ["How long will it last?"],
                "summary_for_context": "Fever for two days.", "_trace": [{"step": "triage", "model": "fake"}], **extra}
    return _fn


# ---------------------------------------------------------------- red-flag rules

@pytest.mark.parametrize("text,flag", [
    ("I have chest pain and sweating", "chest_pain"),
    ("there is PAIN IN MY CHEST", "chest_pain"),
    ("Seene mein dard ho raha hai", "chest_pain"),
    ("सीने में दर्द और पसीना", "chest_pain"),
    ("saans lene mein takleef hai", "breathing"),
    ("I can't breathe properly", "breathing"),
    ("my father is behosh", "unconscious"),
    ("her face is drooping and speech is slurred", "stroke"),
    ("worst headache of my life", "worst_headache"),
    ("headache, stiff neck and high fever", "meningitis"),
    ("vomiting blood since morning", "vomiting_blood"),
    ("black stools for 2 days", "black_stools"),
    ("severe pain in the stomach", "severe_abdominal_pain"),
    ("my 2 month old baby has fever", "infant_fever"),
    ("he had a seizure", "seizure"),
    ("I want to kill myself", "suicidal"),
    ("my lips are swelling and throat is closing", "anaphylaxis"),
    ("heavy bleeding from the cut", "heavy_bleeding"),
])
def test_red_flags_match(text, flag):
    assert flag in ids(text)


@pytest.mark.parametrize("text", ["mild headache since morning", "headache", "I am fit and fine", "stiff neck",
                                  "no chest pain, just a cough", "stomach pain and mild fever since yesterday", ""])
def test_no_false_positives(text):
    assert ids(text) == []


def test_negation_does_not_hide_a_later_flag():
    assert ids("no fever but chest pain") == ["chest_pain"]


def test_suicide_flag_gives_tele_manas():
    f = triage.match_red_flags("I don't want to live anymore")[0]
    assert f["level"] == "EMERGENCY" and "14416" in f["message"]


def test_rules_file_is_well_formed():
    for r in triage.load_rules():
        assert r["level"] in ("EMERGENCY", "URGENT") and r["message"] and r["id"]
        assert r.get("any_of") or r.get("all_of")


# ---------------------------------------------------------------- urgency logic

def test_gemma_only(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", fake_gemma("SELF_CARE"))
    r = triage.triage("runny nose for a day")
    assert r["urgency"] == "SELF_CARE" and r["urgency_source"] == "gemma" and r["red_flags"] == []
    assert r["gemma"]["possible_causes"][1] == {"name": "Dehydration", "why": ""}
    assert "error" not in r and r["_trace"][0]["step"] == "triage_red_flags"


def test_rules_raise_gemma_urgency(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", fake_gemma("SELF_CARE"))
    r = triage.triage("chest pain and sweating")
    assert r["urgency"] == "EMERGENCY" and r["urgency_source"] == "rules"


def test_rules_never_lower_gemma(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", fake_gemma("EMERGENCY"))
    r = triage.triage("black stools")  # rule says URGENT, Gemma says EMERGENCY: keep EMERGENCY
    assert r["urgency"] == "EMERGENCY" and r["urgency_source"] == "gemma"


def test_both_agree(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", fake_gemma("EMERGENCY"))
    assert triage.triage("chest pain")["urgency_source"] == "both"


def test_invalid_gemma_urgency_is_ignored(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", fake_gemma("maybe fine"))
    r = triage.triage("tired")
    assert r["urgency"] == "SEE_DOCTOR" and r["urgency_source"] == "default" and "error" in r


def test_gemma_failure_keeps_red_flags(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", lambda p, step="triage", image=None: {"error": "timeout", "_trace": []})
    r = triage.triage("chest pain")
    assert r["urgency"] == "EMERGENCY" and r["urgency_source"] == "rules" and "timeout" in r["error"]
    r = triage.triage("cough for a week")
    assert r["urgency"] == "SEE_DOCTOR" and r["urgency_source"] == "default" and "SEE_DOCTOR" in r["error"]


def test_gemma_crash_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(triage, "generate_json", boom)
    r = triage.triage("seizure")
    assert r["urgency"] == "EMERGENCY" and "error" in r


def test_empty_text_makes_no_gemma_call(monkeypatch):
    monkeypatch.setattr(triage, "generate_json", lambda *a, **k: pytest.fail("should not call Gemma"))
    r = triage.triage("   ")
    assert r["urgency"] == "SEE_DOCTOR" and "No symptoms" in r["error"]


# ---------------------------------------------------------------- speech-to-text

def _wav(seconds=1.0, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return buf.getvalue()


def test_transcribe_silence_never_raises():
    r = stt.transcribe(_wav())
    assert set(r) == {"text", "language", "seconds", "error"}
    assert r["text"] == "" and r["error"]


def test_transcribe_bad_input_never_raises():
    assert stt.transcribe(b"")["error"]
    assert stt.transcribe(b"not audio at all")["error"]
    assert stt.transcribe(_wav(0.01))["error"]  # too short


def test_decode_wav_resamples_to_16k():
    a = stt._decode_wav(_wav(1.0, rate=8000))
    assert abs(len(a) - 16000) <= 1


# ---------------------------------------------------------------- pages (Streamlit AppTest)

def test_symptom_page_renders_and_checks(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(triage, "generate_json", fake_gemma("SEE_DOCTOR"))
    at = AppTest.from_file(str(ROOT / "pages" / "1_Symptom_Check.py"), default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Symptom Check"
    at.text_area(key="sym_text").set_value("chest pain and sweating")
    at.button(key="sym_check").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "EMERGENCY" in body and "Call 108" in body
    at.button(key="sym_ask").click().run()
    assert not at.exception
    open_ = store.list_open()
    assert len(open_) == 1 and open_[0]["med_index"] == -1
    msgs = store.messages(open_[0]["id"])
    assert msgs[0]["sender"] == "system" and msgs[0]["text"].startswith("Symptom check: EMERGENCY")


def test_doctor_console_renders_symptom_escalation():
    from streamlit.testing.v1 import AppTest

    t = {"red_flags": triage.match_red_flags("chest pain"), "urgency": "EMERGENCY", "urgency_source": "rules",
         "gemma": {"possible_causes": [{"name": "Heart-related issue", "why": "chest pain"}], "self_care": [],
                   "urgency": "EMERGENCY", "questions_for_doctor": ["Is it my heart?"], "summary_for_context": "x"}}
    cid = store.save_case("chest pain", "", None, {"kind": "symptom_check", "transcript": "chest pain", **t})
    eid = store.open_escalation(cid, -1, "chest pain", [], "chest pain")
    store.add_message(eid, "system", "Symptom check: EMERGENCY.")
    at = AppTest.from_file(str(ROOT / "pages" / "2_Doctor_Console.py"), default_timeout=30)
    at.session_state["doc_sel"] = eid
    at.run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "Symptom check" in body and "EMERGENCY" in body
    assert not [b for b in at.button if (b.label or "").startswith("Confirm")]


@pytest.mark.skipif(not (shutil.which("say") and shutil.which("afconvert")), reason="needs macOS say/afconvert")
def test_hindi_speech_hits_devanagari_red_flag(tmp_path):
    aiff, wav = tmp_path / "hi.aiff", tmp_path / "hi.wav"
    subprocess.run(["say", "-v", "Lekha", "-o", str(aiff), "सीने में दर्द हो रहा है और पसीना आ रहा है"], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", str(aiff), str(wav)], check=True)
    r = stt.transcribe(wav.read_bytes())
    assert r["language"] == "hi" and not r["error"]
    assert "chest_pain" in ids(r["text"]), r["text"]


def test_negation_stops_at_clause_breaks():
    from core.triage import match_red_flags as red_flags_in
    assert red_flags_in("no fever, chest pain")
    assert red_flags_in("no vomiting, can't breathe")
    assert red_flags_in("no fever and chest pain")
    assert not red_flags_in("no chest pain, mild headache")
