"""Helpers to load an API-format workflow template and set inputs on nodes by title.

Nodes that change per shot are titled IN_* (e.g. IN_PositivePrompt, IN_Sampler),
so scripts never depend on numeric node ids.
"""
import copy
import json
from pathlib import Path


def load_workflow_template(path):
    # utf-8-sig tolerates a BOM added by Notepad
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def find_node_id_by_title(workflow, title):
    for node_id, node in workflow.items():
        if node.get("_meta", {}).get("title") == title:
            return node_id
    raise KeyError(f"No node titled '{title}' in workflow")


def with_inputs(template, overrides):
    """Return a copy of template with {node_title: {input_name: value}} applied."""
    workflow = copy.deepcopy(template)
    for title, inputs in overrides.items():
        node = workflow[find_node_id_by_title(workflow, title)]
        for key, value in inputs.items():
            if key not in node["inputs"]:
                raise KeyError(f"Node '{title}' has no input '{key}'")
            node["inputs"][key] = value
    return workflow
