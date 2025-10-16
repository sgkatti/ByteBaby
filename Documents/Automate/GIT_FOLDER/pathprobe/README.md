# PathProbe OSPF tools (mini)

This small workspace contains OSPF parsers and an HTML topology generator using `pyvis`.

Quick start

1. Install dependencies (recommended in a virtualenv):

```bash
python3 -m pip install -r requirements.txt
```

2. Run the parser (example):

```bash
python3 ospf_parser.py sample_db.txt --show-skipped
```

3. Generate an interactive topology from the parsed JSON:

```bash
python3 ospf_html_v1.14.py output/parsed_output.json --html output/topology.html
```

Smoke-run script

```bash
python3 scripts/run_smoke.py
```

What I changed in `ospf_html_v1.14.py`

- Made the generator tolerant to multiple parser JSON shapes (maps `router_lsas`/`network_lsas`/`summary_lsas` to `routers`/`networks`/`summary`).
- Explicitly loads the pyvis template if the Network instance's template is None (prevents a runtime AttributeError seen in some environments).

Notes

- If you run into template rendering errors, make sure `jinja2` and `pyvis` are installed in the Python environment you are using.
- Consider adding a small test harness or making parser outputs canonical for easier integration.
