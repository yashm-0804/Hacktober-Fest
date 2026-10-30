"""Offline tests for core/llm.py, plus one live smoke test (RUN_LIVE=1)."""
import io
import os
from pathlib import Path

import pytest
from PIL import Image

from core import llm


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")
    monkeypatch.setattr(llm, "BACKOFF_S", (0, 0))
    return tmp_path / "llm"


def _png(w=2400, h=1200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 220, 240)).save(buf, format="PNG")
    return buf.getvalue()


# ---- JSON extraction

def test_extract_json_plain_and_fenced():
    assert llm.extract_json('{"a": 1}') == {"a": 1}
    assert llm.extract_json('```json\n{"medicines": []}\n```') == {"medicines": []}
    assert llm.extract_json('Sure! Here it is:\n{"x": {"y": [1, 2]}} hope that helps') == {"x": {"y": [1, 2]}}
    assert llm.extract_json('[{"brand_or_drug": "Dolo"}]') == {"items": [{"brand_or_drug": "Dolo"}]}


def test_extract_json_garbage():
    assert llm.extract_json("") is None
    assert llm.extract_json("no json here") is None
    assert llm.extract_json("{broken: json,}") is None


# ---- image prep and cache key

def test_prep_image_downscales_to_1600_jpeg():
    out = llm._prep_image(_png())
    im = Image.open(io.BytesIO(out))
    assert im.format == "JPEG" and max(im.size) == 1600


def test_cache_key_stable_and_sensitive():
    k = llm._cache_key("gemini", "m", "prompt", b"img")
    assert k == llm._cache_key("gemini", "m", "prompt", b"img")
    assert len({k, llm._cache_key("ollama", "m", "prompt", b"img"), llm._cache_key("gemini", "m2", "prompt", b"img"),
                llm._cache_key("gemini", "m", "prompt2", b"img"), llm._cache_key("gemini", "m", "prompt", b"img2")}) == 5


# ---- env + backend switch

def test_load_env_does_not_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# c\nAUSH_T1=from_file\nAUSH_T2="quoted"\nexport AUSH_T3=x\n')
    monkeypatch.setenv("AUSH_T1", "from_env")
    monkeypatch.delenv("AUSH_T2", raising=False)
    monkeypatch.delenv("AUSH_T3", raising=False)
    llm._load_env(env)
    assert os.environ["AUSH_T1"] == "from_env" and os.environ["AUSH_T2"] == "quoted" and os.environ["AUSH_T3"] == "x"


def test_backend_switch_at_call_time(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMMA_MODEL", "gemma-x")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:e4b")
    assert llm.backend_info() == {"backend": "gemini", "model": "gemma-x"}
    seen = []
    monkeypatch.setitem(llm._BACKENDS, "gemini", lambda *a: seen.append("gemini") or '{"medicines": []}')
    monkeypatch.setitem(llm._BACKENDS, "ollama", lambda *a: seen.append("ollama") or '{"medicines": []}')
    llm.read_prescription(_png(100, 100))
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    assert llm.backend_info() == {"backend": "ollama", "model": "gemma4:e4b"}
    r = llm.read_prescription(_png(100, 100))
    assert seen == ["gemini", "ollama"] and r["_trace"][0]["backend"] == "ollama"


# ---- retries, cache hits, error paths

def test_retry_then_success_then_cache_hit(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    calls = []

    def flaky(model, prompt, image, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise llm._Retryable("ServerError: 500")
        if len(calls) == 2:
            return "I could not do it"  # unparseable -> retry
        return '```json\n{"medicines": [{"raw_text": "Dolo 650", "brand_or_drug": "Dolo 650", "confidence": 0.9,' \
               ' "unsure": "false", "strength": "null"}]}\n```'

    monkeypatch.setitem(llm._BACKENDS, "gemini", flaky)
    img = _png(300, 300)
    r = llm.read_prescription(img)
    assert "error" not in r and len(calls) == 3
    med = r["medicines"][0]
    assert med["brand_or_drug"] == "Dolo 650" and med["unsure"] is False and med["strength"] is None
    assert "confidence" not in med
    assert [t["error"] is None for t in r["_trace"]] == [False, False, True]
    assert set(r["_trace"][0]) == {"step", "model", "backend", "seconds", "cache_hit", "error"}
    assert all(t <= llm._limits("gemini")[0] for t in calls)  # honours GEMMA_TIMEOUT_S overrides

    r2 = llm.read_prescription(img)
    assert len(calls) == 3 and r2["_trace"][0]["cache_hit"] is True and r2["_trace"][0]["seconds"] < 0.1
    assert r2["medicines"] == r["medicines"]


def test_gives_up_after_three_attempts_never_raises(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    n = []

    def boom(*a):
        n.append(1)
        raise llm._Retryable("ServerError: 503")

    monkeypatch.setitem(llm._BACKENDS, "gemini", boom)
    r = llm.read_strip(_png(200, 200))
    assert len(n) == 3 and "error" in r and len(r["_trace"]) == 3
    assert not list(tmp_cache.glob("*.json"))  # errors are not cached


def test_non_retryable_fails_fast(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    n = []

    def bad_key(*a):
        n.append(1)
        raise RuntimeError("ClientError: 400 API key not valid")

    monkeypatch.setitem(llm._BACKENDS, "gemini", bad_key)
    r = llm.read_report(_png(200, 200))
    assert len(n) == 1 and "error" in r and r["_trace"][0]["error"]


def test_real_gemini_errors_classified(monkeypatch, tmp_cache):
    """Fake genai client: a 500 ServerError is retried, then success."""
    from google.genai import errors

    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    n = []

    class FakeModels:
        def generate_content(self, model, contents, config):
            n.append(config.temperature)
            if len(n) == 1:
                raise errors.ServerError(500, {"error": {"code": 500, "message": "Internal", "status": "INTERNAL"}})
            return type("R", (), {"text": '{"brand_or_drug": "Dolo 650", "strength": "650 mg", "raw_text": "DOLO-650"}'})()

    monkeypatch.setattr(llm, "_gemini_client", lambda key: type("C", (), {"models": FakeModels()})())
    r = llm.read_strip(_png(200, 200))
    assert r["brand_or_drug"] == "Dolo 650" and len(n) == 2 and n[0] == 0


def test_unreadable_image_returns_error(tmp_cache):
    r = llm.read_prescription(b"not an image")
    assert "error" in r and r["_trace"][0]["error"].startswith("unreadable image")


def test_ollama_down_returns_error(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")  # nothing listens here
    r = llm.read_prescription(_png(100, 100))
    assert "error" in r and "Ollama not reachable" in r["error"] and len(r["_trace"]) == 1


# ---- assess_context

MEDS = [{"index": 0, "raw_text": "Dolo 650 TDS", "candidates": [{"name": "Dolo 650 Tablet", "salts": "paracetamol", "desc": ""}]},
        {"index": 1, "raw_text": "Calcimax", "candidates": [
            {"name": "Celemax 500", "salts": [{"salt": "cefuroxime", "strength": "500mg"}], "desc": ""},
            {"name": "Calcimax ISO", "salts": [{"salt": "calcium carbonate", "strength": "500mg"}], "desc": ""}]}]


def test_assess_context_fills_every_pair(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    out = ('{"fit": [{"index": 1, "candidate": "celemax 500", "fits": "NO", "reason": "antibiotic"},'
           ' {"index": 0, "candidate": "Dolo 650 Tablet", "fits": "yes", "reason": "fever"}],'
           ' "hindi_summary": "डोलो बुखार के लिए है। यह निदान नहीं है।"}')
    prompts_seen = []
    monkeypatch.setitem(llm._BACKENDS, "gemini", lambda m, p, img, t: prompts_seen.append((p, img)) or out)
    r = llm.assess_context("fever", MEDS)
    assert prompts_seen[0][1] is None and "cefuroxime 500mg" in prompts_seen[0][0]
    fits = {(f["index"], f["candidate"]): f["fits"] for f in r["fit"]}
    assert fits == {(0, "Dolo 650 Tablet"): "yes", (1, "Celemax 500"): "no", (1, "Calcimax ISO"): "unclear"}
    assert r["hindi_summary"].endswith(llm.CONFIRM_HI)


def test_assess_context_fallback(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")

    def boom(*a):
        raise RuntimeError("ClientError: 400")

    monkeypatch.setitem(llm._BACKENDS, "gemini", boom)
    r = llm.assess_context("fever", MEDS)
    assert "error" in r and len(r["fit"]) == 3 and all(f["fits"] == "unclear" for f in r["fit"])
    assert "Dolo 650 Tablet" in r["hindi_summary"] and "not a diagnosis" in r["hindi_summary"]


# ---- live smoke test

_HERE = Path(__file__).resolve()
_SAMPLES = [_HERE.parents[1] / "demo_assets" / "prescription.jpg"]


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call Gemma for real")
def test_live_read_prescription():
    sample = next((p for p in _SAMPLES if p.exists()), None)
    if sample is None:
        pytest.skip("no sample prescription image found")
    r = llm.read_prescription(sample.read_bytes())
    assert "error" not in r, r
    assert r["medicines"], r


# ---- generate_json (used by core/triage.py)

def test_generate_json_text_only_and_cache(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    seen = []
    monkeypatch.setitem(llm._BACKENDS, "gemini",
                        lambda m, p, img, t: seen.append(img) or '```json\n{"urgency": "routine", "advice": "rest"}\n```')
    r = llm.generate_json("triage: mild fever. JSON only.", step="triage")
    assert r["urgency"] == "routine" and r["_trace"][0]["step"] == "triage" and seen == [None]
    r2 = llm.generate_json("triage: mild fever. JSON only.", step="triage")
    assert r2["_trace"][0]["cache_hit"] is True and len(seen) == 1 and "_trace" not in {k for k in r2 if k != "_trace"}


def test_generate_json_error(monkeypatch, tmp_cache):
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setitem(llm._BACKENDS, "gemini", lambda *a: "not json")
    r = llm.generate_json("x", step="triage")
    assert set(r) == {"error", "_trace"} and len(r["_trace"]) == 3


def test_gemini_failure_falls_back_to_local_ollama(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path, raising=False)
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMMA_FALLBACK", "ollama")
    monkeypatch.setenv("GEMMA_BUDGET_S", "30")

    def gemini_down(*_a, **_k):
        raise RuntimeError("400 bad request")  # non-retryable, so the test is fast

    def local_ok(*_a, **_k):
        return '{"medicines": [{"brand_or_drug": "Dolo 650", "raw_text": "Dolo 650"}]}'

    monkeypatch.setattr(llm, "_BACKENDS", {"gemini": gemini_down, "ollama": local_ok})
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, "JPEG")
    r = llm.read_prescription(buf.getvalue())
    assert "error" not in r
    assert r["medicines"][0]["brand_or_drug"] == "Dolo 650"
    assert any("(local fallback)" in t["step"] and t["backend"] == "ollama" for t in r["_trace"])


def test_cached_local_fallback_is_reused_without_calling_gemini(monkeypatch, tmp_path):
    import io
    from PIL import Image
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path, raising=False)
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMMA_FALLBACK", "ollama")
    calls = []

    def gemini_down(*_a, **_k):
        calls.append("gemini")
        raise RuntimeError("400 bad request")

    def local_ok(*_a, **_k):
        calls.append("ollama")
        return '{"medicines": [{"brand_or_drug": "Dolo 650", "raw_text": "Dolo 650"}]}'

    monkeypatch.setattr(llm, "_BACKENDS", {"gemini": gemini_down, "ollama": local_ok})
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, "JPEG")
    first = llm.read_prescription(buf.getvalue())
    second = llm.read_prescription(buf.getvalue())
    assert "error" not in first and "error" not in second
    assert calls == ["gemini", "ollama"]  # the second call never waited on the API
    assert second["_trace"][-1]["cache_hit"] is True and second["_trace"][-1]["backend"] == "ollama"
