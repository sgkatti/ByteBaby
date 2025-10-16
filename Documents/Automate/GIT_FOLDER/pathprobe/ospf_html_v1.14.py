#!/usr/bin/env python3
import json
import argparse
from pyvis.network import Network
import os
import time

class OSPFHtmlGenerator:
    def __init__(self, json_file, html_out):
        self.json_file = json_file
        self.html_out = html_out
        self.net_vis = Network(height="750px", width="100%", directed=True)
        self.ghost_count = 1
        self.node_map = {}  # Map for real and ghost nodes

    def load_json(self):
        print(f"[INFO] Loaded JSON file: {self.json_file}")
        with open(self.json_file, "r") as f:
            self.data = json.load(f)

    def add_nodes(self):
        print("[INFO] Adding nodes...")
        for router in self.data.get("routers", []):
            rid = router.get("router_id") or self.create_ghost_node()
            self.node_map[rid] = rid
            self.net_vis.add_node(rid, label=f"Router\n{rid}", color="lightblue")

        for network in self.data.get("networks", []):
            nid = network.get("network_id") or self.create_ghost_node()
            self.node_map[nid] = nid
            self.net_vis.add_node(nid, label=f"Network\n{nid}", color="lightgreen")

        for summary in self.data.get("summary", []):
            sid = summary.get("link") or self.create_ghost_node()
            self.node_map[sid] = sid
            self.net_vis.add_node(sid, label=f"Summary\n{sid}", color="orange")

    def create_ghost_node(self):
        ghost_id = f"vNode{self.ghost_count}"
        self.ghost_count += 1
        self.node_map[ghost_id] = ghost_id
        self.net_vis.add_node(ghost_id, label=f"Ghost\n{ghost_id}", color="red")
        return ghost_id

    def get_node(self, node_id):
        if node_id in self.node_map:
            return self.node_map[node_id]
        else:
            return self.create_ghost_node()

    def add_edges(self):
        print("[INFO] Adding edges...")
        # Routers to networks
        for router in self.data.get("routers", []):
            rid = router.get("router_id") or self.create_ghost_node()
            links = router.get("links", [])
            for link in links:
                target = link or self.create_ghost_node()
                self.net_vis.add_edge(rid, self.get_node(target))

        # Networks to attached routers
        for network in self.data.get("networks", []):
            nid = network.get("network_id") or self.create_ghost_node()
            attached_list = network.get("attached_routers", [])
            for att in attached_list:
                self.net_vis.add_edge(self.get_node(att), self.get_node(nid))

        # Summary LSAs
        for summary in self.data.get("summary", []):
            link = summary.get("link") or self.create_ghost_node()
            adv = summary.get("adv_router") or self.create_ghost_node()
            self.net_vis.add_edge(self.get_node(adv), self.get_node(link))

    def generate_html_topology(self):
        start_time = time.time()
        self.load_json()
        self.add_nodes()
        self.add_edges()
        try:
            os.makedirs(os.path.dirname(self.html_out), exist_ok=True)
            self.net_vis.show(self.html_out)
            print(f"[INFO] HTML topology generated: {self.html_out}")
        except Exception as e:
            print(f"[ERROR] Failed to generate HTML: {e}")
        print(f"[INFO] Time taken: {round(time.time() - start_time, 3)} seconds")

def main():
    parser = argparse.ArgumentParser(description="Generate OSPF network topology HTML from parsed JSON")
    parser.add_argument("json_file", help="Parsed OSPF JSON file")
    parser.add_argument("--html", required=True, help="Output HTML file path")
    args = parser.parse_args()

    gen = OSPFHtmlGenerator(args.json_file, args.html)
    gen.generate_html_topology()

if __name__ == "__main__":
    main()
