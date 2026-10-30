import pytest

from core import store


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB", str(tmp_path / "t.db"))


def test_case_round_trip():
    cid = store.save_case("fever", ["penicillin"], "/x.jpg", {"meds": [{"index": 0}]})
    c = store.get_case(cid)
    assert c["context"] == "fever" and c["allergies"] == "penicillin" and c["image_path"] == "/x.jpg"
    assert c["payload"] == {"meds": [{"index": 0}]}
    store.update_case(cid, {"meds": []})
    assert store.get_case(cid)["payload"] == {"meds": []}
    assert store.get_case(9999) is None


def test_escalation_messages_resolve():
    cid = store.save_case("ctx", "", None, {})
    eid = store.open_escalation(cid, 2, "Celemax 500", [{"name": "Calcimax"}], "vit D deficiency")
    assert [e["id"] for e in store.list_open()] == [eid]
    e = store.get_escalation(eid)
    assert e["status"] == "open" and e["candidates"] == [{"name": "Calcimax"}] and e["med_index"] == 2
    store.add_message(eid, "system", "hello")
    store.add_message(eid, "patient", "please help")
    store.add_message(eid, "doctor", "Confirmed: Calcimax")
    msgs = store.messages(eid)
    assert [m["sender"] for m in msgs] == ["system", "patient", "doctor"]
    with pytest.raises(ValueError):
        store.add_message(eid, "hacker", "x")
    store.resolve(eid, {"name": "Calcimax"})
    e = store.get_escalation(eid)
    assert e["status"] == "resolved" and e["resolution"] == {"name": "Calcimax"}
    assert store.list_open() == []


def test_save_upload_is_content_addressed():
    p1 = store.save_upload(b"abc")
    p2 = store.save_upload(b"abc")
    assert p1 == p2 and p1.endswith(".jpg") and "cache/uploads" in p1
