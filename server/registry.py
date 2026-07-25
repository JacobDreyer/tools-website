"""Discovery of tool modules and assembly of the category tree."""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
import traceback
from pathlib import Path
from typing import Any

from toolkit import Tool

BASE_DIR = Path(__file__).resolve().parent
TOOLS_PKG = "tools"
CATEGORY_FILE = BASE_DIR / "categories.json"


def _titleise(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug).strip().title()


class Registry:
    """Holds the loaded tools plus the category tree they hang off."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        self.categories: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []

    # -- loading ------------------------------------------------------
    def load(self) -> "Registry":
        self.tools.clear()
        self.errors.clear()
        self._load_tools()
        self._build_categories()
        return self

    def _load_tools(self) -> None:
        package = importlib.import_module(TOOLS_PKG)
        importlib.reload(package)

        for info in pkgutil.walk_packages(package.__path__, prefix=f"{TOOLS_PKG}."):
            if info.ispkg or info.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            try:
                module = importlib.import_module(info.name)
                module = importlib.reload(module)
            except Exception:
                self.errors.append({"module": info.name, "error": traceback.format_exc()})
                continue

            tool = getattr(module, "TOOL", None)
            if not isinstance(tool, Tool):
                continue
            if tool.id in self.tools:
                self.errors.append({
                    "module": info.name,
                    "error": f"duplicate tool id {tool.id!r}, keeping the first one loaded",
                })
                continue

            tool.module = info.name
            tool.source_path = str(Path(module.__file__).resolve()) if module.__file__ else ""
            tool.category = tool.category.strip("/").lower()
            self.tools[tool.id] = tool

    # -- categories ---------------------------------------------------
    def _build_categories(self) -> None:
        declared: list[dict[str, Any]] = []
        if CATEGORY_FILE.exists():
            try:
                declared = json.loads(CATEGORY_FILE.read_text(encoding="utf-8")).get("categories", [])
            except (OSError, json.JSONDecodeError) as exc:
                self.errors.append({"module": "categories.json", "error": str(exc)})

        def clone(nodes: list[dict[str, Any]], parent: str) -> list[dict[str, Any]]:
            out = []
            for node in nodes:
                slug = str(node["id"]).strip("/").lower()
                path = f"{parent}/{slug}" if parent else slug
                out.append({
                    "id": slug,
                    "path": path,
                    "name": node.get("name") or _titleise(slug),
                    "description": node.get("description", ""),
                    "children": clone(node.get("children", []), path),
                    "count": 0,
                    "total": 0,
                })
            return out

        tree = clone(declared, "")

        # Graft in any path a tool references that the file did not declare.
        def ensure(path: str) -> dict[str, Any] | None:
            if not path:
                return None
            level = tree
            node = None
            walked = ""
            for slug in path.split("/"):
                walked = f"{walked}/{slug}" if walked else slug
                node = next((n for n in level if n["id"] == slug), None)
                if node is None:
                    node = {"id": slug, "path": walked, "name": _titleise(slug),
                            "description": "", "children": [], "count": 0, "total": 0}
                    level.append(node)
                level = node["children"]
            return node

        for tool in self.tools.values():
            node = ensure(tool.category)
            if node is not None:
                node["count"] += 1

        def roll_up(nodes: list[dict[str, Any]]) -> int:
            running = 0
            for node in nodes:
                node["total"] = node["count"] + roll_up(node["children"])
                running += node["total"]
            return running

        roll_up(tree)
        self.categories = tree

    # -- queries ------------------------------------------------------
    def get(self, tool_id: str) -> Tool | None:
        return self.tools.get(tool_id)

    def catalog(self) -> dict[str, Any]:
        tools = sorted(self.tools.values(), key=lambda t: (t.category, t.name.lower()))
        return {
            "categories": self.categories,
            "tools": [t.to_dict() for t in tools],
            "errors": [{"module": e["module"], "error": e["error"].strip().splitlines()[-1]}
                       for e in self.errors],
        }


registry = Registry()
