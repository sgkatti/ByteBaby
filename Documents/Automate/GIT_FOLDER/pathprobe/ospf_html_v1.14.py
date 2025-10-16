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
        # Ensure pyvis has a compiled template available to render. Some envs
        # may leave `template` as None; load it explicitly from the templateEnv.
        try:
            if getattr(self.net_vis, 'template', None) is None:
                self.net_vis.template = self.net_vis.templateEnv.get_template(self.net_vis.path)
        except Exception:
            # If this fails, we'll let show() raise a clear error later; keep init resilient.
            pass
        self.ghost_count = 1
        self.node_map = {}  # Map for real and ghost nodes

    def _normalize_schema(self):
        """
        Normalize various parser output schemas into a common shape used by this generator.
        Supported input variants (examples):
        - {"router_lsas": [...], "network_lsas": [...], "summary_lsas": [...]} (ospf_parser_v1.11 / v1.10)
        - {"routers": [...], "networks": [...], "summary": [...]} (older/other)
        The normalized result will populate keys: routers, networks, summary
        """
        # If newer parser keys exist, map them
        if "router_lsas" in self.data:
            # router_lsas items may be dataclass dicts or simple dicts; map to expected keys
            routers = []
            for r in self.data.get("router_lsas", []):
                # support both 'router_id' and 'router' keys
                rid = r.get("router_id") or r.get("router") or r.get("id")
                # links might be list of dicts with link_id or raw strings
                links = []
                for l in r.get("links", []):
                    if isinstance(l, dict):
                        links.append(l.get("link_id") or l.get("link") or str(l))
                    else:
                        links.append(str(l))
                routers.append({"router_id": rid, "links": links})
            self.data["routers"] = routers

        # Map network_lsas -> networks
        if "network_lsas" in self.data:
            networks = []
            for n in self.data.get("network_lsas", []):
                # older parser used 'attached' vs 'attached_routers'
                attached = n.get("attached_routers") or n.get("attached")
                # ensure attached_routers is a list
                if isinstance(attached, list):
                    attached_list = attached
                elif attached is None:
                    attached_list = []
                else:
                    attached_list = [attached]
                networks.append({"network_id": n.get("network_id") or n.get("network"), "attached_routers": attached_list})
            self.data["networks"] = networks

        # Map summary_lsas -> summary
        if "summary_lsas" in self.data:
            summary = []
            for s in self.data.get("summary_lsas", []):
                # support different key names
                link = s.get("link_id") or s.get("link") or s.get("prefix") or s.get("adv_router")
                adv = s.get("adv_router") or s.get("adv") or s.get("advertising_router")
                summary.append({"link": link, "adv_router": adv})
            self.data["summary"] = summary

    def load_json(self):
        print(f"[INFO] Loaded JSON file: {self.json_file}")
        with open(self.json_file, "r") as f:
            self.data = json.load(f)

    def add_nodes(self):
        print("[INFO] Adding nodes...")
        # Normalize schema if needed
        self._normalize_schema()

        for router in self.data.get("routers", []):
            rid = router.get("router_id") or self.create_ghost_node()
            if rid in self.node_map:
                node_id = self.node_map[rid]
            else:
                node_id = rid
                self.node_map[rid] = rid
            self.net_vis.add_node(node_id, label=f"Router\n{rid}", color="lightblue")

        for network in self.data.get("networks", []):
            nid = network.get("network_id") or self.create_ghost_node()
            if nid in self.node_map:
                node_id = self.node_map[nid]
            else:
                node_id = nid
                self.node_map[nid] = nid
            self.net_vis.add_node(node_id, label=f"Network\n{nid}", color="lightgreen")

        for summary in self.data.get("summary", []):
            sid = summary.get("link") or self.create_ghost_node()
            if sid in self.node_map:
                node_id = self.node_map[sid]
            else:
                node_id = sid
                self.node_map[sid] = sid
            self.net_vis.add_node(node_id, label=f"Summary\n{sid}", color="orange")

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
