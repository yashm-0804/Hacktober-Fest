"""REST API flows the mobile app depends on. Gemma is offline here (conftest), so every Gemma step degrades
gracefully and the code checks still run."""
import time

import pytest
from fastapi.testclient import TestClient

import api
from core import pipeline, store, triage


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB", str(tmp_path / "api.db"))
    monkeypatch.setattr(store, "UPLOAD_DIR", tmp_path / "uploads")


@pytest.fixture
def client():
    return TestClient(api.app)


def wait_job(client, job_id, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def analyze_typed(client, rx_text, context="fever and body ache", allergies="penicillin"):
    r = client.post("/api/analyze", data={"context": context, "allergies": allergies, "rx_text": rx_text})
    assert r.status_code == 202, r.text
    job = wait_job(client, r.json()["job_id"])
    assert job["status"] == "done", job
    return client.get(f"/api/cases/{job['result']['case_id']}").json(), job


def force_low(monkeypatch):
    real_score = pipeline.confidence.score
    monkeypatch.setattr(pipeline.confidence, "score",
                        lambda r, c, f=None: dict(real_score(r, c, f), band="LOW", value=0.3, reasons=["test LOW"]))


def test_health_and_settings(client, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    assert client.get("/api/health").json()["ok"] is True
    s = client.get("/api/settings").json()
    assert s["backend"] == "gemini" and {o["id"] for o in s["options"]} == {"gemini", "ollama"}
    assert client.put("/api/settings", json={"backend": "ollama"}).json()["backend"] == "ollama"
    assert client.put("/api/settings", json={"backend": "gpt"}).status_code == 422


def test_analyze_typed_flow(client):
    view, job = analyze_typed(client, "Dolo 650 TDS\nCombiflam SOS")
    case = view["case"]
    assert view["kind"] == "prescription" and view["image_url"] is None and view["escalations"] == []
    assert [m["read"]["brand_or_drug"] for m in case["meds"]] == ["Dolo 650", "Combiflam"]
    assert any(a["type"] == "DUPLICATE" and "paracetamol" in a["title"].lower() for a in case["alerts"])
    assert "image_path" not in case
    labels = [s["label"] for s in job["steps"]]
    assert labels[0].startswith("Parsing") and labels[-1] == "Done"


def test_analyze_needs_input(client):
    assert client.post("/api/analyze", data={"context": "fever"}).status_code == 400


def test_analyze_photo_saves_image(client):
    r = client.post("/api/analyze", data={"use_demo_images": "true"})
    job = wait_job(client, r.json()["job_id"])
    view = client.get(f"/api/cases/{job['result']['case_id']}").json()
    assert view["case"]["input_mode"] == "photo"
    assert view["case"]["errors"]  # Gemma is offline in tests: the read fails, and the app is told why
    img = client.get(view["image_url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"


def test_patient_pick(client):
    view, _ = analyze_typed(client, "Dolo 650 TDS")
    name = view["case"]["meds"][0]["candidates"][0]["name"]
    assert client.post(f"/api/cases/{view['id']}/meds/0/pick", json={"name": "Not a candidate"}).status_code == 400
    assert client.post(f"/api/cases/{view['id']}/meds/5/pick", json={"name": name}).status_code == 404
    after = client.post(f"/api/cases/{view['id']}/meds/0/pick", json={"name": name}).json()
    assert after["case"]["meds"][0]["status"] == "picked_by_patient" and after["case"]["rechecked"] is True


def test_ask_doctor_and_doctor_confirms(client, monkeypatch):
    force_low(monkeypatch)
    view, _ = analyze_typed(client, "Celemax 500 OD", context="vitamin D deficiency, joint pain", allergies="")
    cid = view["id"]
    r = client.post(f"/api/cases/{cid}/meds/0/ask-doctor").json()
    eid = r["escalation_id"]
    assert client.post(f"/api/cases/{cid}/meds/0/ask-doctor").json()["escalation_id"] == eid  # idempotent
    assert r["case"]["escalations"][0]["status"] == "open"

    [open_] = client.get("/api/escalations").json()
    assert open_["id"] == eid and open_["kind"] == "medicine" and open_["message_count"] == 1
    detail = client.get(f"/api/escalations/{eid}").json()
    assert "could not confidently read line 1" in detail["messages"][0]["text"]
    assert detail["med"]["read"]["brand_or_drug"].startswith("Celemax") and detail["candidates"]

    client.post(f"/api/escalations/{eid}/messages", json={"sender": "patient", "text": "Is it the calcium one?"})
    msgs = client.post(f"/api/escalations/{eid}/messages", json={"sender": "doctor", "text": "Yes."}).json()["messages"]
    assert [m["sender"] for m in msgs] == ["system", "patient", "doctor"]
    assert client.post(f"/api/escalations/{eid}/messages", json={"sender": "system", "text": "x"}).status_code == 422

    assert client.post(f"/api/escalations/{eid}/resolve", json={}).status_code == 400
    done = client.post(f"/api/escalations/{eid}/resolve", json={"free_text": "Calcimax"}).json()
    assert done["status"] == "resolved" and done["last_message"]["text"] == "Confirmed: Calcimax"
    assert client.post(f"/api/escalations/{eid}/resolve", json={"free_text": "Calcimax"}).status_code == 409
    assert client.post(f"/api/escalations/{eid}/messages", json={"sender": "patient", "text": "hi"}).status_code == 409

    case = client.get(f"/api/cases/{cid}").json()["case"]
    assert case["meds"][0]["status"] == "confirmed_by_doctor" and case["rechecked"] is True
    assert client.get("/api/escalations").json() == []
    assert len(client.get("/api/escalations?status=all").json()) == 1
    assert client.post(f"/api/cases/{cid}/meds/0/pick", json={"name": "x"}).status_code == 409


def test_symptom_check_and_doctor_chat(client, monkeypatch):
    def fake(prompt, step="triage", image=None):
        return {"possible_causes": [{"name": "Heart-related issue", "why": "chest pain"}], "self_care": [],
                "urgency": "URGENT", "questions_for_doctor": [], "summary_for_context": "Chest pain today.",
                "_trace": []}

    monkeypatch.setattr(triage, "generate_json", fake)
    r = client.post("/api/triage", json={"text": "chest pain and sweating"}).json()
    assert r["red_flags"] and r["red_flags"][0]["level"] == "EMERGENCY"  # instant, from code rules
    job = wait_job(client, r["job_id"])
    t = job["result"]["triage"]
    assert t["urgency"] == "EMERGENCY" and t["urgency_source"] == "rules"  # code raised Gemma's URGENT

    cid = job["result"]["case_id"]
    assert client.get(f"/api/cases/{cid}").json()["kind"] == "symptom_check"
    eid = client.post(f"/api/cases/{cid}/ask-doctor").json()["escalation_id"]
    detail = client.get(f"/api/escalations/{eid}").json()
    assert detail["kind"] == "symptom" and detail["triage"]["urgency"] == "EMERGENCY"
    assert detail["messages"][0]["text"].startswith("Symptom check: EMERGENCY")
    assert client.post(f"/api/escalations/{eid}/resolve", json={}).json()["status"] == "resolved"


def test_symptom_ask_doctor_rejects_prescription_case(client):
    view, _ = analyze_typed(client, "Dolo 650 TDS")
    assert client.post(f"/api/cases/{view['id']}/ask-doctor").status_code == 400


def test_triage_rejects_empty(client):
    assert client.post("/api/triage", json={"text": ""}).status_code == 422
    assert client.post("/api/triage", json={"text": "   "}).status_code == 400


def test_demo_and_testlab(client):
    d = client.get("/api/demo").json()
    assert "penicillin" in d["allergies"] and "Dolo 650" in d["typed_rx"]
    assert client.get(d["prescription_url"]).status_code == 200
    assert client.get("/api/demo/context.txt").status_code == 404
    assert client.get("/api/demo/..%2Fapi.py").status_code == 404
    lab = client.get("/api/testlab").json()
    assert lab["total"] == 4 and lab["passed"] == 4


def test_transcribe_bad_audio_is_an_error_not_a_crash(client):
    r = client.post("/api/transcribe", files={"audio": ("a.m4a", b"not audio", "audio/m4a")})
    assert r.status_code == 200 and r.json()["error"]


def test_unknown_ids(client):
    assert client.get("/api/cases/999").status_code == 404
    assert client.get("/api/escalations/999").status_code == 404
    assert client.get("/api/jobs/nope").status_code == 404
