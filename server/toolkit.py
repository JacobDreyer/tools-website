"""Authoring kit for Field Kit tools.

A tool is a single Python module under ``server/tools/`` that defines a
module-level ``TOOL = Tool(...)``. The registry imports every module in that
package on startup and picks those up, so adding a tool never means editing
the server.

    from toolkit import Tool, Result, fields

    def run(p):
        out = Result()
        out.metric("Answer", p["a"] + p["b"])
        return out

    TOOL = Tool(
        id="add",
        name="Add",
        summary="Adds two numbers.",
        category="math/arithmetic",
        inputs=[fields.number("a", "A"), fields.number("b", "B")],
        run=run,
    )

Anything between ``# region: code`` and ``# endregion: code`` markers in the
module is what gets shown in the SOURCE panel on the site. Without markers the
whole file is shown.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------

class InputError(Exception):
    """A supplied parameter is missing or unusable.

    ``index`` points at the offending entry when the field is a list, so the
    form can flag one cell instead of the whole column.
    """

    def __init__(self, message: str, field_id: str | None = None,
                 index: int | None = None):
        super().__init__(message)
        self.message = message
        self.field_id = field_id
        self.index = index


class ToolError(Exception):
    """The tool ran but could not produce a result. Message is user facing."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


# --------------------------------------------------------------------------
# input fields
# --------------------------------------------------------------------------

@dataclass
class Field:
    id: str
    label: str
    type: str
    default: Any = None
    unit: str | None = None
    help: str | None = None
    required: bool = True
    group: str | None = None          # form section heading
    table: str | None = None          # list fields sharing a key render as one table
    placeholder: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[dict[str, Any]] = dc_field(default_factory=list)
    length_from: str | None = None    # list length is driven by this field's value
    rows: int | None = None           # textarea height

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "required": self.required,
        }
        for key in ("unit", "help", "group", "table", "placeholder",
                    "min", "max", "step", "length_from", "rows"):
            value = getattr(self, key)
            if value is not None:
                d[key] = value
        if self.options:
            d["options"] = self.options
        return d


def _normalise_options(options: Iterable[Any]) -> list[dict[str, Any]]:
    out = []
    for opt in options:
        if isinstance(opt, dict):
            out.append({"value": opt["value"], "label": opt.get("label", str(opt["value"]))})
        elif isinstance(opt, (tuple, list)):
            out.append({"value": opt[0], "label": str(opt[1])})
        else:
            out.append({"value": opt, "label": str(opt)})
    return out


class fields:
    """Namespace of field constructors. Never instantiated."""

    @staticmethod
    def number(id: str, label: str, default: float = 0.0, **kw: Any) -> Field:
        return Field(id=id, label=label, type="number", default=default, **kw)

    @staticmethod
    def integer(id: str, label: str, default: int = 0, **kw: Any) -> Field:
        kw.setdefault("step", 1)
        return Field(id=id, label=label, type="integer", default=default, **kw)

    @staticmethod
    def text(id: str, label: str, default: str = "", **kw: Any) -> Field:
        return Field(id=id, label=label, type="text", default=default, **kw)

    @staticmethod
    def textarea(id: str, label: str, default: str = "", **kw: Any) -> Field:
        kw.setdefault("rows", 6)
        return Field(id=id, label=label, type="textarea", default=default, **kw)

    @staticmethod
    def boolean(id: str, label: str, default: bool = False, **kw: Any) -> Field:
        return Field(id=id, label=label, type="boolean", default=default, **kw)

    @staticmethod
    def select(id: str, label: str, options: Iterable[Any], default: Any = None, **kw: Any) -> Field:
        opts = _normalise_options(options)
        if default is None and opts:
            default = opts[0]["value"]
        return Field(id=id, label=label, type="select", default=default, options=opts, **kw)

    @staticmethod
    def number_list(id: str, label: str, default: Sequence[float] = (), **kw: Any) -> Field:
        """A vector of numbers. Pair with ``length_from`` to lock its length to
        another field, and ``table`` to merge several vectors into one grid."""
        return Field(id=id, label=label, type="number_list", default=list(default), **kw)

    @staticmethod
    def text_list(id: str, label: str, default: Sequence[str] = (), **kw: Any) -> Field:
        return Field(id=id, label=label, type="text_list", default=list(default), **kw)


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------

class Result:
    """Ordered stack of display blocks handed back to the front end."""

    def __init__(self) -> None:
        self.blocks: list[dict[str, Any]] = []
        self._metrics: dict[str, Any] | None = None

    # -- metrics ------------------------------------------------------
    def metric(self, label: str, value: Any, unit: str | None = None,
               hint: str | None = None, emphasis: bool = False) -> "Result":
        """Add a single readout to the current metric strip."""
        if self._metrics is None or self.blocks[-1] is not self._metrics:
            self._metrics = {"type": "metrics", "items": []}
            self.blocks.append(self._metrics)
        item = {"label": label, "value": value}
        if unit:
            item["unit"] = unit
        if hint:
            item["hint"] = hint
        if emphasis:
            item["emphasis"] = True
        self._metrics["items"].append(item)
        return self

    # -- table --------------------------------------------------------
    def table(self, columns: Sequence[Any], rows: Sequence[Sequence[Any]],
              title: str | None = None, note: str | None = None) -> "Result":
        """``columns`` accepts plain strings or dicts of
        ``{label, align, unit, flag}``. A row cell may be a dict of
        ``{value, flag}`` to mark it as out of tolerance."""
        cols = []
        for col in columns:
            cols.append({"label": col} if isinstance(col, str) else dict(col))
        self.blocks.append({
            "type": "table", "title": title, "note": note,
            "columns": cols, "rows": [list(r) for r in rows],
        })
        self._metrics = None
        return self

    # -- chart --------------------------------------------------------
    def chart(self, series: Sequence[dict[str, Any]], title: str | None = None,
              kind: str = "line", x_label: str = "", y_label: str = "",
              x_ticks: Sequence[Sequence[Any]] | None = None,
              y_min: float | None = None, y_max: float | None = None) -> "Result":
        """``series`` items are ``{name, points: [[x, y], ...], color?}``."""
        self.blocks.append({
            "type": "chart", "title": title, "kind": kind,
            "x_label": x_label, "y_label": y_label,
            "x_ticks": [list(t) for t in x_ticks] if x_ticks else None,
            "y_min": y_min, "y_max": y_max,
            "series": [dict(s) for s in series],
        })
        self._metrics = None
        return self

    # -- prose / raw --------------------------------------------------
    def text(self, body: str, title: str | None = None) -> "Result":
        self.blocks.append({"type": "text", "title": title, "body": body})
        self._metrics = None
        return self

    def log(self, body: str, title: str | None = None) -> "Result":
        self.blocks.append({"type": "log", "title": title, "body": body})
        self._metrics = None
        return self

    def json(self, data: Any, title: str | None = None) -> "Result":
        self.blocks.append({"type": "json", "title": title, "data": data})
        self._metrics = None
        return self

    def notice(self, body: str, level: str = "info") -> "Result":
        """``level`` is one of info, warn, error, ok."""
        self.blocks.append({"type": "notice", "level": level, "body": body})
        self._metrics = None
        return self

    def to_dict(self) -> dict[str, Any]:
        return {"blocks": self.blocks}


# --------------------------------------------------------------------------
# tool
# --------------------------------------------------------------------------

@dataclass
class Tool:
    id: str
    name: str
    summary: str
    category: str                       # slug path, e.g. "electrical/power-distribution"
    run: Callable[[dict[str, Any]], Result]
    inputs: list[Field] = dc_field(default_factory=list)
    description: str = ""               # longer prose shown on the tool sheet
    tag: str = "py"                     # language badge in the card footer
    rev: str = "A"
    timeout: float = 30.0
    autorun: bool = True                # run once with the defaults on open
    notes: list[str] = dc_field(default_factory=list)

    # filled in by the registry
    module: str = ""
    source_path: str = ""

    def source(self) -> str:
        return extract_source(Path(self.source_path)) if self.source_path else ""

    def to_dict(self, with_source: bool = False) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "category": self.category,
            "description": self.description,
            "tag": self.tag,
            "rev": self.rev,
            "autorun": self.autorun,
            "notes": self.notes,
            "inputs": [f.to_dict() for f in self.inputs],
        }
        if with_source:
            d["source"] = self.source()
            d["source_file"] = Path(self.source_path).name if self.source_path else ""
        return d


# --------------------------------------------------------------------------
# source extraction
# --------------------------------------------------------------------------

_REGION_START = re.compile(r"^\s*#\s*region:\s*code\s*$", re.I)
_REGION_END = re.compile(r"^\s*#\s*endregion:\s*code\s*$", re.I)


def extract_source(path: Path) -> str:
    """Return the copy-pasteable slice of a tool module.

    Everything between ``# region: code`` and ``# endregion: code`` is kept,
    with the common indent stripped. Files without markers are returned whole.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    kept: list[str] = []
    inside = False
    found = False
    for line in lines:
        if not inside and _REGION_START.match(line):
            inside, found = True, True
            if kept:
                kept.append("")
            continue
        if inside and _REGION_END.match(line):
            inside = False
            continue
        if inside:
            kept.append(line)

    if not found:
        return "\n".join(lines).strip("\n") + "\n"
    return textwrap.dedent("\n".join(kept)).strip("\n") + "\n"


# --------------------------------------------------------------------------
# parameter coercion
# --------------------------------------------------------------------------

def _to_float(value: Any, field: Field, where: str) -> float:
    if isinstance(value, bool):
        raise InputError(f"{where} must be a number.", field.id)
    if isinstance(value, (int, float)):
        out = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise InputError(f"{where} is required.", field.id)
        try:
            out = float(stripped)
        except ValueError:
            raise InputError(f"{where} is not a number: {value!r}", field.id) from None
    else:
        raise InputError(f"{where} must be a number.", field.id)

    if out != out or out in (float("inf"), float("-inf")):
        raise InputError(f"{where} must be finite.", field.id)
    if field.min is not None and out < field.min:
        raise InputError(f"{where} must be at least {field.min}.", field.id)
    if field.max is not None and out > field.max:
        raise InputError(f"{where} must be at most {field.max}.", field.id)
    return out


def _to_int(value: Any, field: Field, where: str) -> int:
    number = _to_float(value, field, where)
    if abs(number - round(number)) > 1e-9:
        raise InputError(f"{where} must be a whole number.", field.id)
    return int(round(number))


def coerce_params(tool: Tool, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise the submitted payload against the tool's fields."""
    raw = raw or {}
    out: dict[str, Any] = {}

    for field in tool.inputs:
        present = field.id in raw and raw[field.id] is not None
        value = raw.get(field.id)

        if not present:
            if field.required and field.default is None:
                raise InputError(f"{field.label} is required.", field.id)
            value = field.default

        if field.type == "number":
            out[field.id] = _to_float(value, field, field.label)
        elif field.type == "integer":
            out[field.id] = _to_int(value, field, field.label)
        elif field.type == "boolean":
            out[field.id] = bool(value)
        elif field.type == "select":
            allowed = [o["value"] for o in field.options]
            if allowed and value not in allowed:
                raise InputError(f"{field.label}: {value!r} is not one of {allowed}.", field.id)
            out[field.id] = value
        elif field.type in ("text", "textarea"):
            text = "" if value is None else str(value)
            if field.required and not text.strip():
                raise InputError(f"{field.label} is required.", field.id)
            out[field.id] = text
        elif field.type == "number_list":
            if not isinstance(value, (list, tuple)):
                raise InputError(f"{field.label} must be a list of numbers.", field.id)
            numbers = []
            for i, item in enumerate(value):
                try:
                    numbers.append(_to_float(item, field, f"{field.label}[{i + 1}]"))
                except InputError as exc:
                    raise InputError(exc.message, field.id, i) from None
            out[field.id] = numbers
        elif field.type == "text_list":
            if not isinstance(value, (list, tuple)):
                raise InputError(f"{field.label} must be a list.", field.id)
            out[field.id] = [str(v) for v in value]
        else:
            out[field.id] = value

    # length_from wiring is enforced after everything is coerced
    for field in tool.inputs:
        if field.length_from and field.type in ("number_list", "text_list"):
            expected = out.get(field.length_from)
            if isinstance(expected, int) and len(out[field.id]) != expected:
                raise InputError(
                    f"{field.label} has {len(out[field.id])} values but "
                    f"{expected} were expected.", field.id)

    return out
