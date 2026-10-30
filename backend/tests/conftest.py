"""Keep the offline suite off the network: Gemma backends fail fast unless a test is marked `live`."""
import pytest

from core import llm


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real Gemma API (run with RUN_LIVE=1)")


@pytest.fixture(autouse=True)
def _offline_gemma(request, monkeypatch):
    # .env may enable the local fallback; tests opt in explicitly so nothing reaches a real Ollama.
    monkeypatch.delenv("GEMMA_FALLBACK", raising=False)
    # test_llm.py fakes the backends itself; live tests need the real API.
    if request.node.get_closest_marker("live") or request.node.module.__name__.endswith("test_llm"):
        return

    def offline(*_args, **_kwargs):
        raise RuntimeError("offline test: Gemma backend disabled")

    monkeypatch.setattr(llm, "_BACKENDS", {name: offline for name in llm._BACKENDS})
