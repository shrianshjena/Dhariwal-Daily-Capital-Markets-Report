#!/usr/bin/env python3
"""Rebuild an issue's "sources" list from every source object it cites (unique by URL, in order).

    python3 render/fill_sources.py issues/2026-10-29.json
"""
import json
import sys
from pathlib import Path


def walk(node, found):
    if isinstance(node, dict):
        if set(node) == {"name", "url"}:
            found.setdefault(node["url"], node["name"])
        for value in node.values():
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)


path = Path(sys.argv[1])
issue = json.loads(path.read_text(encoding="utf-8"))
found = {}
walk({k: v for k, v in issue.items() if k != "sources"}, found)
issue["sources"] = [{"name": name, "url": url} for url, name in found.items()]
path.write_text(json.dumps(issue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(found)} sources written to {path}")
