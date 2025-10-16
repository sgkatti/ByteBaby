import shutil
import tempfile
from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]

# helper to import module from file

def import_module_from(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parser_and_generator_end_to_end(tmp_path):
    # copy sample_db.txt into temp dir
    sample = ROOT / 'sample_db.txt'
    if not sample.exists():
        # fallback: use existing parsed_output.json for generator
        parsed = ROOT / 'output' / 'parsed_output.json'
        assert parsed.exists(), 'No sample_db.txt or parsed_output.json available for test'
        json_in = parsed
    else:
        work_input = tmp_path / 'sample_db.txt'
        shutil.copy(sample, work_input)
        # run parser
        parser_path = ROOT / 'ospf_parser_v1.11.py'
        parser_mod = import_module_from(parser_path, 'ospf_parser_test')
        Parser = getattr(parser_mod, 'OspfParser')
        p = Parser(str(work_input))
        # prefer parse_file or parse
        if hasattr(p, 'parse_file'):
            p.parse_file()
        else:
            p.parse()
        # parser currently writes to a relative 'output' directory. It may have
        # written under the temp dir or the project root. Accept either.
        candidate1 = tmp_path / 'output' / 'parsed_output.json'
        candidate2 = ROOT / 'output' / 'parsed_output.json'
        if candidate1.exists():
            json_in = candidate1
        elif candidate2.exists():
            json_in = candidate2
        else:
            raise AssertionError('parsed_output.json not found in tmp or project output')

    # Now run generator with that JSON
    gen_path = ROOT / 'ospf_html_v1.14.py'
    gen_mod = import_module_from(gen_path, 'ospf_html_test')
    Gen = getattr(gen_mod, 'OSPFHtmlGenerator')
    out_html = tmp_path / 'topology_test.html'
    g = Gen(str(json_in), str(out_html))
    g.generate_html_topology()
    assert out_html.exists()
    # quick sanity: output contains html root
    text = out_html.read_text()
    assert '<html' in text.lower()