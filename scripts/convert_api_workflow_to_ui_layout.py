"""Convert an API-format workflow (what our scripts run) into a tidy ComfyUI UI workflow:
nodes laid out in colored groups (left -> right) with a Vietnamese note per group.

Widget order comes from the running server's /object_info, so values land in the right widgets.
Usage (ComfyUI must be running):
  python scripts/convert_api_workflow_to_ui_layout.py workflows/ui/layout-character-scene-ipadapter-v1.json
Layout spec JSON: {"api": "...api.json", "output": "...ui.json",
                   "groups": [{"title": "...", "color": "#hex", "note": "...", "nodes": ["1", "10"]}]}
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = "http://127.0.0.1:8188"
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3"}
NODE_W, GROUP_GAP, PAD, NOTE_H = 340, 60, 40, 150


def fetch_object_info(class_types):
    info = {}
    for ct in sorted(set(class_types)):
        with urllib.request.urlopen(f"{SERVER}/object_info/{ct}", timeout=20) as r:
            info.update(json.loads(r.read()))
    return info


def input_kind(spec):
    """'COMBO' for list/COMBO specs, else the declared type name."""
    return "COMBO" if isinstance(spec[0], list) else spec[0]


def ordered_inputs(defn):
    order = defn.get("input_order") or {k: list(v) for k, v in defn["input"].items() if k in ("required", "optional")}
    for section in ("required", "optional"):
        for name in order.get(section, []):
            yield name, defn["input"][section][name]


def build_node(node_id, api_node, defn, links_in):
    inputs, widgets = [], []
    for name, spec in ordered_inputs(defn):
        kind, opts = input_kind(spec), (spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {})
        value = api_node["inputs"].get(name)
        if kind == "COMFY_DYNAMICCOMBO_V3" and name not in api_node["inputs"]:
            continue  # hidden/optional dynamic combo (e.g. SaveVideo legacy 'codec'): frontend adds it itself
        if kind in WIDGET_TYPES and not isinstance(value, list):
            widgets.append(value if value is not None else opts.get("default", spec[0][0] if kind == "COMBO" and isinstance(spec[0], list) else None))
            if opts.get("control_after_generate"):
                widgets.append("fixed")
            if opts.get("image_upload"):
                widgets.append("image")
            continue
        if kind in WIDGET_TYPES:  # widget value driven by a link: expose as converted input
            kind = kind if kind != "COMBO" else "*"
        inputs.append({"name": name, "type": kind, "link": links_in.get(name)})
    # nested dynamic-combo values such as "format.codec" follow their parent widget
    widgets += [v for k, v in api_node["inputs"].items() if "." in k and not isinstance(v, list)]
    outputs = [{"name": out, "type": out, "links": [], "slot_index": i} for i, out in enumerate(defn["output"])]
    rows = len(widgets) + max(len(inputs), len(outputs))
    height = 50 + 26 * rows + (120 if "STRING" in str(defn["input"].get("required", {}).get("text", "")) else 0)
    return {"id": int(node_id), "type": api_node["class_type"], "pos": [0, 0], "size": [NODE_W, height],
            "flags": {}, "order": 0, "mode": 0, "inputs": inputs, "outputs": outputs,
            "title": api_node.get("_meta", {}).get("title", api_node["class_type"]),
            "properties": {"Node name for S&R": api_node["class_type"]}, "widgets_values": widgets}


def main():
    spec = json.loads((ROOT / sys.argv[1]).read_text(encoding="utf-8-sig"))
    api = json.loads((ROOT / spec["api"]).read_text(encoding="utf-8-sig"))
    for nid, values in spec.get("overrides", {}).items():  # example values so the UI runs as-is
        api[nid]["inputs"].update(values)
    info =fetch_object_info(n["class_type"] for n in api.values())

    # links: one per API connection [source_id, slot] -> target input
    links, incoming, link_id = [], {}, 0
    for target_id, node in api.items():
        for name, value in node["inputs"].items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
                link_id += 1
                incoming.setdefault(target_id, {})[name] = link_id
                links.append([link_id, int(value[0]), value[1], int(target_id), name])

    nodes = {nid: build_node(nid, n, info[n["class_type"]], incoming.get(nid, {})) for nid, n in api.items()}
    for link in links:  # resolve target slot index + type, register on source output
        target = nodes[str(link[3])]
        slot = next(i for i, inp in enumerate(target["inputs"]) if inp["name"] == link[4])
        out = nodes[str(link[1])]["outputs"][link[2]]
        out["links"].append(link[0])
        link[4:] = [slot, out["type"]]

    groups, x, next_id = [], 0, max(int(k) for k in api) + 100
    for gi, group in enumerate(spec["groups"]):
        y = PAD + 40
        note_id, next_id = next_id, next_id + 1
        nodes[str(note_id)] = {"id": note_id, "type": "Note", "pos": [x + PAD, y], "size": [NODE_W, NOTE_H],
                               "flags": {}, "order": 0, "mode": 0, "inputs": [], "outputs": [],
                               "title": "Ghi chú", "properties": {}, "widgets_values": [group["note"]],
                               "color": "#432", "bgcolor": "#653"}
        y += NOTE_H + 30
        for nid in group["nodes"]:
            nodes[nid]["pos"] = [x + PAD, y]
            y += nodes[nid]["size"][1] + 40
        groups.append({"id": gi + 1, "title": group["title"], "bounding": [x, 0, NODE_W + 2 * PAD, y],
                       "color": group.get("color", "#3f789e"), "font_size": 24, "flags": {}})
        x += NODE_W + 2 * PAD + GROUP_GAP

    for order, node in enumerate(sorted(nodes.values(), key=lambda n: n["pos"][0] * 10000 + n["pos"][1])):
        node["order"] = order
    workflow = {"last_node_id": max(n["id"] for n in nodes.values()), "last_link_id": link_id,
                "nodes": list(nodes.values()), "links": links, "groups": groups, "config": {},
                "extra": {"ds": {"scale": 0.75, "offset": [20, 20]}}, "version": 0.4}
    out = ROOT / spec["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(workflow, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = set(api) - {nid for g in spec["groups"] for nid in g["nodes"]}
    print(f"OK {out} ({len(api)} nodes, {len(links)} links, {len(groups)} groups)"
          + (f" WARNING not placed in any group: {sorted(missing)}" if missing else ""))


if __name__ == "__main__":
    main()
