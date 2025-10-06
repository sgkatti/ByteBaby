#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PathProbe OSPF Database Parser v1.10
- Fully parses Router, Network, and Summary LSAs
- Shows skipped malformed LSA details optionally
- Interactive skip/abort for malformed LSAs
- JSON output in output/parsed_output.json
- CLI: python ospf_parser.py <file> [--show-skipped] [--interactive]
"""

import sys
import time
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from colorama import init, Fore, Style

init(autoreset=True)

@dataclass
class RouterLSA:
    router_id: str
    area_id: str
    links: list

@dataclass
class NetworkLSA:
    network_id: str
    attached_routers: list
    area_id: str

@dataclass
class SummaryLSA:
    adv_router: str
    prefix: str
    metric: int
    area_id: str

class OspfParser:
    def __init__(self, input_file: str, verbose=True, show_skipped=False, interactive=False):
        self.input_file = Path(input_file)
        self.router_lsas = []
        self.network_lsas = []
        self.summary_lsas = []
        self.skipped = 0
        self.verbose = verbose
        self.show_skipped = show_skipped
        self.interactive = interactive

    def parse(self):
        if not self.input_file.exists():
            print(Fore.RED + f"[ERROR] File not found: {self.input_file}")
            sys.exit(1)

        start_time = time.time()
        print(Fore.CYAN + f"[INFO] Parsing file: {self.input_file}")

        with open(self.input_file) as f:
            lines = f.readlines()

        current_type = None
        block_lines = []

        header_patterns = {
            "router": ["OSPF Router with ID", "Router Link States"],
            "network": ["Network Link States", "Net Link States", "Network LSAs"],
            "summary": ["Summary Net Link States", "Summary Net LSAs"]
        }

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            detected_type = None
            for t, patterns in header_patterns.items():
                for p in patterns:
                    if p.lower() in stripped.lower():
                        detected_type = t
                        break
                if detected_type:
                    break

            if detected_type:
                if block_lines and current_type:
                    self._process_block(current_type, block_lines)
                current_type = detected_type
                block_lines = [(lineno, stripped)]
            else:
                if current_type:
                    block_lines.append((lineno, stripped))

        if block_lines and current_type:
            self._process_block(current_type, block_lines)

        self._report()
        self._export_json()
        elapsed = time.time() - start_time
        print(Fore.CYAN + f"[INFO] Time taken: {elapsed:.3f} seconds")

    # ------------------------ PROCESS BLOCK ------------------------
    def _process_block(self, lsa_type, block_lines):
        if self.verbose:
            print(Fore.MAGENTA + f"\n[DEBUG] Processing {lsa_type.upper()} block lines {block_lines[0][0]}-{block_lines[-1][0]}")
        if lsa_type == "router":
            self._parse_router_block(block_lines)
        elif lsa_type == "network":
            self._parse_network_block(block_lines)
        elif lsa_type == "summary":
            self._parse_summary_block(block_lines)

    # ------------------------ ROUTER BLOCK ------------------------
    def _parse_router_block(self, block_lines):
        try:
            import re
            router_id = None
            area_id = "0"
            for lineno, line in block_lines:
                m = re.search(r"OSPF Router with ID\s*\(?([\d.]+)\)?", line, re.I)
                if m:
                    router_id = m.group(1)
                    break
            for lineno, line in block_lines:
                m = re.search(r"Router Link States\s*\(Area (\d+)\)", line, re.I)
                if m:
                    area_id = m.group(1)
                    break
            if not router_id:
                self._handle_skipped("Router", block_lines, "Missing router ID")
                return

            links = []
            for lineno, line in block_lines:
                if "Link ID" in line or "Link connected" in line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metric = int(parts[-1]) if parts[-1].isdigit() else 0
                        links.append({"link_id": parts[0], "metric": metric})
                    except:
                        self.skipped += 1

            self.router_lsas.append(RouterLSA(router_id=router_id, area_id=area_id, links=links))
            print(Fore.GREEN + f"[OK] Parsed Router LSA: {router_id}, Links: {len(links)}")

        except Exception as e:
            self._handle_skipped("Router", block_lines, str(e))

    # ------------------------ NETWORK BLOCK ------------------------
    def _parse_network_block(self, block_lines):
        try:
            area_id = "0"
            data_lines = [line for lineno, line in block_lines[1:]]
            for line in data_lines:
                if not line.strip() or "Link ID" in line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    self._handle_skipped("Network", [(0,line)], "Insufficient columns")
                    continue
                net_id = parts[0]
                attached = [parts[1]]
                self.network_lsas.append(NetworkLSA(network_id=net_id, attached_routers=attached, area_id=area_id))
                if self.verbose:
                    print(Fore.GREEN + f"[OK] Parsed Network LSA: {net_id}, Attached: {attached[0]}")
        except Exception as e:
            self._handle_skipped("Network", block_lines, str(e))

    # ------------------------ SUMMARY BLOCK ------------------------
    def _parse_summary_block(self, block_lines):
        try:
            area_id = "0"
            data_lines = [line for lineno, line in block_lines[1:]]
            for line in data_lines:
                if not line.strip() or "Link ID" in line:
                    continue
                parts = line.split()
                if len(parts) < 3:
                    self._handle_skipped("Summary", [(0,line)], "Insufficient columns")
                    continue
                prefix = parts[0]
                adv_router = parts[1]
                metric = next((int(x) for x in parts[2:] if x.isdigit()), 0)
                self.summary_lsas.append(SummaryLSA(adv_router=adv_router, prefix=prefix, metric=metric, area_id=area_id))
                if self.verbose:
                    print(Fore.GREEN + f"[OK] Parsed Summary LSA: {prefix}, AdvRouter: {adv_router}, Metric: {metric}")
        except Exception as e:
            self._handle_skipped("Summary", block_lines, str(e))

    # ------------------------ SKIPPED LSA HANDLER ------------------------
    def _handle_skipped(self, lsa_type, block_lines, reason):
        self.skipped += 1
        print(Fore.YELLOW + f"[WARN] Skipping malformed {lsa_type} LSA: {reason}")
        if self.show_skipped:
            for lineno, line in block_lines:
                print(Fore.YELLOW + f"  {lineno}: {line}")
        if self.interactive:
            choice = input("Skip (S) / Abort (A)? [S]: ").strip().lower() or "s"
            if choice == "a":
                sys.exit(1)

    # ------------------------ REPORT / EXPORT ------------------------
    def _report(self):
        print(Fore.GREEN + Style.BRIGHT + "\n[SUMMARY]")
        print(Fore.GREEN + f"  Router LSAs: {len(self.router_lsas)} | Network LSAs: {len(self.network_lsas)} | Summary LSAs: {len(self.summary_lsas)}")
        if self.skipped > 0:
            print(Fore.YELLOW + f"  Skipped malformed LSAs: {self.skipped}")

    def _export_json(self):
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / "parsed_output.json"

        data = {
            "router_lsas": [asdict(r) for r in self.router_lsas],
            "network_lsas": [asdict(n) for n in self.network_lsas],
            "summary_lsas": [asdict(s) for s in self.summary_lsas],
        }
        with open(out_file, "w") as f:
            json.dump(data, f, indent=4)
        print(Fore.CYAN + f"[INFO] Output written to: {out_file}")

# ------------------------ MAIN ------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(Fore.RED + "Usage: python ospf_parser.py <ospf_db_file.txt> [--show-skipped] [--interactive]")
        sys.exit(1)

    show_skipped = "--show-skipped" in sys.argv
    interactive = "--interactive" in sys.argv

    parser = OspfParser(sys.argv[1], verbose=True, show_skipped=show_skipped, interactive=interactive)
    parser.parse()
