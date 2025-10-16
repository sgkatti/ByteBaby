#!/usr/bin/env python3
import argparse
import json
import time
import os

class OspfParser:
    def __init__(self, filename, show_skipped=False):
        self.filename = filename
        self.show_skipped = show_skipped
        self.router_lsas = []
        self.network_lsas = []
        self.summary_lsas = []
        self.skipped_lsas = []
        self.start_time = time.time()

    def parse_file(self):
        print(f"[INFO] Parsing file: {self.filename}")
        with open(self.filename, "r") as f:
            lines = f.readlines()

        block_type = None
        block_lines = []
        start_line_no = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("OSPF Router") or stripped.startswith("Router Link States"):
                if block_lines:
                    self._process_block(block_type, start_line_no, block_lines)
                    block_lines = []
                block_type = "ROUTER"
                start_line_no = i + 1
            elif stripped.startswith("Summary Net Link States"):
                if block_lines:
                    self._process_block(block_type, start_line_no, block_lines)
                    block_lines = []
                block_type = "SUMMARY"
                start_line_no = i + 1
            elif stripped.startswith("Link ID") and block_type != "ROUTER":
                if block_lines:
                    self._process_block(block_type, start_line_no, block_lines)
                    block_lines = []
                block_type = "NETWORK"
                start_line_no = i + 1

            block_lines.append(line)

        if block_lines:
            self._process_block(block_type, start_line_no, block_lines)

        self._write_output()
        end_time = time.time()
        print(f"[INFO] Time taken: {end_time - self.start_time:.3f} seconds")

    def _process_block(self, block_type, start_line, block_lines):
        if block_type == "ROUTER":
            router_id = None
            area_id = "unknown"
            links = []

            for l in block_lines:
                if "Router with ID" in l:
                    parts = l.strip().split()
                    router_id = parts[3].strip("()")
                if "Link connected to" in l:
                    links.append(l.strip())

            if router_id:
                self.router_lsas.append({
                    "router_id": router_id,
                    "area_id": area_id,
                    "links": links
                })
                print(f"[OK] Parsed Router LSA: {router_id}, Links: {len(links)}")
            else:
                self.skipped_lsas.append({"type": "Router", "lines": list(range(start_line, start_line + len(block_lines))), "reason": "Missing router ID"})
                if self.show_skipped:
                    print(f"[WARN] Skipping malformed Router LSA:")
                    for idx, l in enumerate(block_lines, start=start_line):
                        print(f"  {idx}: {l.strip()}")

        elif block_type == "NETWORK":
            for l in block_lines[1:]:
                if l.strip() == "":
                    continue
                parts = l.strip().split()
                if len(parts) >= 2:
                    network_id = parts[0]
                    attached = parts[1]
                else:
                    network_id = "Network"
                    attached = "unknown"
                self.network_lsas.append({"network_id": network_id, "attached": attached})
                print(f"[OK] Parsed Network LSA: {network_id}, Attached: {attached}")

        elif block_type == "SUMMARY":
            for l in block_lines[1:]:
                if l.strip() == "":
                    continue
                parts = l.strip().split()
                if len(parts) >= 6:
                    link_id = parts[0]
                    adv_router = parts[1]
                    metric = parts[-1]
                else:
                    link_id = "Link"
                    adv_router = "ID"
                    metric = 20
                self.summary_lsas.append({"link_id": link_id, "adv_router": adv_router, "metric": int(metric)})
                print(f"[OK] Parsed Summary LSA: {link_id}, AdvRouter: {adv_router}, Metric: {metric}")

    def _write_output(self):
        os.makedirs("output", exist_ok=True)
        out_file = os.path.join("output", "parsed_output.json")
        data = {
            "router_lsas": self.router_lsas,
            "network_lsas": self.network_lsas,
            "summary_lsas": self.summary_lsas,
            "skipped_lsas": self.skipped_lsas
        }
        with open(out_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[INFO] Output written to: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OSPF LSA Parser v1.14")
    parser.add_argument("filename", help="OSPF database text file")
    parser.add_argument("--show-skipped", action="store_true", help="Show skipped/malformed LSAs")
    args = parser.parse_args()

    parser_obj = OspfParser(args.filename, show_skipped=args.show_skipped)
    parser_obj.parse_file()
