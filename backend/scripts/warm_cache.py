"""Warm the Gemma disk cache (cache/llm/) for the demo case, so the live demo answers instantly.

Usage: .venv/bin/python scripts/warm_cache.py [--assets /path/to/demo_assets]

Runs the same pipeline.analyze() calls the app makes for "Load the demo case": once with the prescription
photo and once with the typed lines, both with the strip photo. Because the inputs are identical, the app's
Gemma calls then hit the cache. Uses whatever LLM_BACKEND is set (default from .env). Run it again: every
Gemma step should say "cached". Warm-up is not user-facing, so it waits longer than the app:
GEMMA_TIMEOUT_S=200, GEMMA_BUDGET_S=420 unless set.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("GEMMA_TIMEOUT_S", "200")
os.environ.setdefault("GEMMA_BUDGET_S", "420")

from core import llm, pipeline  # noqa: E402

ASSETS = Path(sys.argv[sys.argv.index("--assets") + 1]) if "--assets" in sys.argv else ROOT / "demo_assets"


def _read(name: str) -> str:
    path = ASSETS / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _run(label: str, **inputs) -> bool:
    t = time.time()
    case = pipeline.analyze(_read("context.txt"), _read("allergies.txt"), **inputs)
    print(f"\n{label}: {time.time() - t:.1f}s, {len(case['meds'])} medicines", flush=True)
    for step in case["_trace"]:
        if step["backend"] in ("python", "code"):
            continue
        state = f"ERROR {step['error']}" if step["error"] else ("cached" if step["cache_hit"] else "ok")
        print(f"   {step['step']:40} {step['seconds']:7.2f}s  {state}")
    for m in case["meds"]:
        print(f"   [{m['index']}] {m['read'].get('brand_or_drug')!s:24} -> {(case['resolved'][m['index']]['label'])!s:28} "
              f"{m['confidence']['band']}")
    for e in case["errors"]:
        print(f"   ! {e}")
    return not case["errors"]


def main() -> int:
    print(f"backend: {llm.backend_info()}  assets: {ASSETS}")
    rx, strip = ASSETS / "prescription.jpg", ASSETS / "strip.jpg"
    strip_bytes = strip.read_bytes() if strip.exists() else None
    ok = True
    if rx.exists():
        ok &= _run("Demo photo", rx_image=rx.read_bytes(), strip_image=strip_bytes)
    if _read("typed_rx.txt"):
        ok &= _run("Demo typed", rx_text=_read("typed_rx.txt"), strip_image=strip_bytes)
    print("\nALL OK" if ok else "\nSOME STEPS FAILED (run it again to retry; successes are cached)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
