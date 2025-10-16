#!/usr/bin/env python3
"""
Run parser then generate HTML topology in one step.
Usage:
  python3 scripts/run_all.py <input_file.txt> [--html output.html]
If no input file is provided, the script will use output/parsed_output.json if present.
"""
import sys
from pathlib import Path
import argparse
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
parser_candidates = [ROOT / 'ospf_parser_v1.11.py', ROOT / 'ospf_parser.py']

ap = argparse.ArgumentParser()
ap.add_argument('input', nargs='?', help='OSPF DB text file (optional)')
ap.add_argument('--html', help='Output HTML path', default=str(ROOT / 'output' / 'topology_all.html'))
args = ap.parse_args()

input_path = None
if args.input:
    input_path = Path(args.input)
else:
    # prefer sample input if present
    sample = ROOT / 'sample_db.txt'
    if sample.exists():
        input_path = sample

# If we don't have an input file, but parsed_output.json exists, skip parsing
parsed_out = ROOT / 'output' / 'parsed_output.json'

def find_and_run_parser(input_file: Path):
    for cand in parser_candidates:
        if cand.exists():
            print(f"[INFO] Using parser: {cand.name}")
            spec = importlib.util.spec_from_file_location('ospf_parser_local', cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # heuristics: call parse() or parse_file()
            if hasattr(mod, 'OspfParser'):
                # instantiate and run (match v1.11 signature)
                Parser = getattr(mod, 'OspfParser')
                try:
                    parser_obj = Parser(str(input_file), show_skipped=False)
                    # try both parse_file and parse
                    if hasattr(parser_obj, 'parse_file'):
                        parser_obj.parse_file()
                    elif hasattr(parser_obj, 'parse'):
                        parser_obj.parse()
                    else:
                        raise RuntimeError('Parser has no parse method')
                    return True
                except TypeError:
                    # try alternative constructor
                    parser_obj = Parser(str(input_file))
                    if hasattr(parser_obj, 'parse_file'):
                        parser_obj.parse_file()
                    else:
                        parser_obj.parse()
                    return True
            elif hasattr(mod, 'OspfParser'):
                # fallback
                return False
    return False

# Run parser if we have an input; otherwise ensure parsed_output.json exists
if input_path and input_path.exists():
    ok = find_and_run_parser(input_path)
    if not ok:
        print('[WARN] No parser ran successfully. Ensure parser files exist and support current API.')
elif not parsed_out.exists():
    print('[ERROR] No input file given and parsed_output.json not found. Exiting.')
    sys.exit(1)

# Run generator using the parsed_output.json
from importlib import util
spec = util.spec_from_file_location('ospf_html_local', ROOT / 'ospf_html_v1.14.py')
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)
OSPFHtmlGenerator = mod.OSPFHtmlGenerator

json_input = parsed_out if parsed_out.exists() else (ROOT / 'output' / 'parsed_output.json')
print(f"[INFO] Generating HTML from: {json_input}")
generator = OSPFHtmlGenerator(str(json_input), args.html)
generator.generate_html_topology()
print('[INFO] Completed run_all')
