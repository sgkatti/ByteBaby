#!/usr/bin/env python3
"""
Quick smoke-run script: runs generator on existing sample JSON and writes a smoke HTML file.
Usage: python3 scripts/run_smoke.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "output" / "parsed_output.json"
OUT = ROOT / "output" / "topology_smoke.html"

if not INPUT.exists():
    print(f"[ERROR] Sample input not found: {INPUT}")
    sys.exit(1)

sys.path.insert(0, str(ROOT))
import importlib.util
spec = importlib.util.spec_from_file_location("ospf_html_v1_14", ROOT / "ospf_html_v1.14.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
OSPFHtmlGenerator = mod.OSPFHtmlGenerator

print(f"[INFO] Using input: {INPUT}")
print(f"[INFO] Writing output: {OUT}")

gen = OSPFHtmlGenerator(str(INPUT), str(OUT))
gen.generate_html_topology()
print('[INFO] Smoke-run completed')
