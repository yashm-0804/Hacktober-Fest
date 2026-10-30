"""Warm the Gemma disk cache (cache/llm/) for the demo assets, so the live demo is instant.

Usage: .venv/bin/python scripts/warm_cache.py
Runs read_prescription, read_strip and assess_context on demo_assets/*; skips any missing file.
       .venv/bin/python scripts/warm_cache.py --assets /path/to/demo_assets
Uses whatever LLM_BACKEND is set (default from .env). Run it again: every step should report cache_hit=True.
Warm-up is not user-facing, so it waits longer than the UI: GEMMA_TIMEOUT_S=200, GEMMA_BUDGET_S=420 unless set.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("GEMMA_TIMEOUT_S", "200")
os.environ.setdefault("GEMMA_BUDGET_S", "420")

from core import llm, match  # noqa: E402

ASSETS = Path(sys.argv[sys.argv.index("--assets") + 1]) if "--assets" in sys.argv else ROOT / "demo_assets"


def _show(label: str, res: dict, secs: float) -> None:
    hits = [t.get("cache_hit") for t in res.get("_trace", [])]
    status = "ERROR " + res["error"] if "error" in res else "ok"
    print(f"{label:20} {secs:7.2f}s  cache_hit={hits[-1] if hits else None}  attempts={len(hits)}  {status}", flush=True)


def main() -> int:
    print(f"backend: {llm.backend_info()}  assets: {ASSETS}")
    rx_path, strip_path, ctx_path = ASSETS / "prescription.jpg", ASSETS / "strip.jpg", ASSETS / "context.txt"
    ok = True
    meds = []

    if rx_path.exists():
        t = time.time()
        rx = llm.read_prescription(rx_path.read_bytes())
        _show("read_prescription", rx, time.time() - t)
        ok &= "error" not in rx
        for i, m in enumerate(rx.get("medicines", [])):
            print(f"   [{i}] {m['brand_or_drug']!s:24} strength={m['strength']} dose={m['dose_and_frequency']} unsure={m['unsure']}")
            cands = match.candidates(m["brand_or_drug"], m.get("strength"), k=3)
            meds.append({"index": i, "raw_text": m["raw_text"],
                         "candidates": [{"name": c["name"], "salts": c.get("salts"), "desc": c.get("desc", "")} for c in cands]})
    else:
        print(f"skip read_prescription: {rx_path} missing")

    if strip_path.exists():
        t = time.time()
        st = llm.read_strip(strip_path.read_bytes())
        _show("read_strip", st, time.time() - t)
        ok &= "error" not in st
        print(f"   {st.get('brand_or_drug')} {st.get('strength')}")
    else:
        print(f"skip read_strip: {strip_path} missing")

    if ctx_path.exists() and meds:
        t = time.time()
        ac = llm.assess_context(ctx_path.read_text(encoding="utf-8").strip(), meds)
        _show("assess_context", ac, time.time() - t)
        ok &= "error" not in ac
        for f in ac.get("fit", []):
            print(f"   [{f['index']}] {f['candidate']!s:28} {f['fits']:8} {f['reason']}")
        print("   hindi:", ac.get("hindi_summary"))
    else:
        print("skip assess_context: " + ("no medicines read" if ctx_path.exists() else f"{ctx_path} missing"))

    print("ALL OK" if ok else "SOME STEPS FAILED (re-run to retry; successes are cached)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
