"""Spike: can Gemma 4 (via the Gemini API) read medicines off messy handwritten prescriptions?

Usage: .venv/bin/python run_test.py [model] [runs]
Reads GEMINI_API_KEY from the environment or from ./.env.
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types

HERE = Path(__file__).parent
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma-4-31b-it"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 1

PROMPT = """You are reading a photo of an Indian doctor's prescription or clinical note.
List ONLY the medicines that are prescribed (ignore investigations, diagnoses, advice, and anything struck out).
For each medicine return:
- raw_text: exactly what is written, character by character as best you can; use ? for illegible letters
- brand_or_drug: your best reading of the medicine name
- form: tablet / capsule / syrup / suspension / drops / injection / sachet / other
- strength: e.g. "650 mg", or null if not written
- dose_and_frequency: e.g. "1 tab BD", "5 ml at bedtime"
- duration: e.g. "5 days", or null
- confidence: 0.0-1.0 that brand_or_drug is correct
- unsure: true if you cannot read it reliably
Never invent a medicine that is not written. If no medicines are prescribed, return an empty list.
Respond with JSON only: {"medicines": [ ... ]}"""


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    env = HERE / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(("GEMINI_API_KEY=", "GOOGLE_API_KEY=")):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("No GEMINI_API_KEY in env or .env")
    return key


def parse_json(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def main():
    client = genai.Client(api_key=load_key())
    truth = json.loads((HERE / "ground_truth.json").read_text())
    results = {"model": MODEL, "runs": RUNS, "images": {}}

    def run_one(name, r):
        img = (HERE / "samples" / name).read_bytes()
        t0 = time.time()
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=[types.Part.from_bytes(data=img, mime_type="image/jpeg"), PROMPT],
            )
            text, err = resp.text or "", None
        except Exception as e:  # keep going so one failure doesn't kill the spike
            text, err = "", f"{type(e).__name__}: {e}"
        secs = round(time.time() - t0, 1)
        parsed = parse_json(text)
        print(f"{name} run {r + 1}: {secs}s {'ERROR ' + err[:200] if err else ''}", flush=True)
        if parsed:
            for m in parsed.get("medicines", []):
                print(f"   - {m.get('brand_or_drug')!s:28} raw={m.get('raw_text')!s:30} conf={m.get('confidence')} unsure={m.get('unsure')}", flush=True)
        return name, {"seconds": secs, "error": err, "parsed": parsed, "raw": None if parsed else text[:2000]}

    jobs = [(n, r) for n in truth if not n.startswith("_") for r in range(RUNS)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for name, run in pool.map(lambda j: run_one(*j), jobs):
            entry = results["images"].setdefault(name, {"label": truth[name]["label"], "truth": truth[name]["medicines"], "runs": []})
            entry["runs"].append(run)
    out = HERE / f"results_{MODEL}.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
