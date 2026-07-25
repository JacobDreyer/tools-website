# Field Kit

A personal index for small tools and scripts. Vue 3 front end on the blueprint
theme from `Website Claude Theme/`, Python back end that actually runs the
scripts and hands back structured results.

Every tool gets a sheet with three panels: the **inputs** you fill in, the
**output** the script produced, and the **source** in a copyable code block.

```
D:\Projects\Tools-Website
├─ server\                 python side
│  ├─ app.py               FastAPI app + static hosting of the built UI
│  ├─ toolkit.py           the authoring API: Tool, fields, Result
│  ├─ registry.py          imports tools\**.py, assembles the category tree
│  ├─ categories.json      category / sub-category tree
│  └─ tools\               one module per tool — this is where you work
├─ frontend\               vue 3 + vite
│  └─ src\
│     ├─ views\            HomeView (index grid), ToolView (tool sheet)
│     ├─ components\       InputForm, ResultView, CodeBlock, chips, cards
│     └─ styles\theme.css  every design token, light + dark
└─ start.ps1
```

## Running it

```powershell
.\start.ps1
```

First run makes the venv, installs dependencies, builds the front end, then
serves the whole thing at <http://127.0.0.1:8765>.

While working on the interface, `.\start.ps1 -Dev` puts the API on `:8765` with
auto-reload and Vite on <http://localhost:5173> with hot module replacement.
After changing a tool, either restart or `POST /api/reload` to re-scan.

Rebuild the UI after front-end edits with `.\start.ps1 -Rebuild`.

## Adding a tool

Drop a `.py` file anywhere under `server\tools\`. Define a `run` function and a
module-level `TOOL`; the registry finds it on the next start. Nothing else to
register.

```python
from toolkit import Result, Tool, fields


# region: code
def slugify(text, separator="-"):
    """What gets shown in the SOURCE panel."""
    return separator.join(text.lower().split())
# endregion: code


def run(p):
    out = Result()
    out.metric("Slug", slugify(p["text"], p["separator"]), emphasis=True)
    return out


TOOL = Tool(
    id="slugify",
    name="Slugify",
    summary="Turns a title into a URL slug.",
    category="text/formatting",       # creates the sub-category if it is new
    inputs=[
        fields.text("text", "Text", "Hello World"),
        fields.text("separator", "Separator", "-"),
    ],
    run=run,
)
```

`run` receives a dict keyed by field id, already validated and coerced to the
right Python type, and returns a `Result`. Anything it `print`s shows up in a
console panel under the output.

### Fields

| Constructor | Renders as |
| --- | --- |
| `fields.number(id, label, default)` | numeric input |
| `fields.integer(id, label, default)` | whole-number input |
| `fields.text` / `fields.textarea` | single line / multi-line |
| `fields.select(id, label, options, default)` | dropdown; options are strings, `(value, label)` pairs or dicts |
| `fields.boolean(id, label, default)` | checkbox |
| `fields.number_list(id, label, default)` | a vector of numbers |
| `fields.text_list(id, label, default)` | a vector of strings |

Every field also takes `unit`, `help`, `min`, `max`, `step`, `placeholder`,
`required`, and:

- `group="Solver"` — starts a titled section in the form.
- `table="devices"` — list fields sharing a key merge into **one** grid, a
  column each, a row per index. Each column gets a *fill down* button.
- `length_from="num_devices"` — the vector resizes to whatever that field says,
  padding with the last value. Validated server-side too.

### Result blocks

Call these on the `Result` in the order you want them stacked:

- `out.metric(label, value, unit=, hint=, emphasis=)` — consecutive calls form
  one readout strip.
- `out.table(columns, rows, title=, note=)` — columns are strings or
  `{label, unit, align}`; a cell may be `{"value": x, "flag": True}` to redline it.
- `out.chart(series, kind="line"|"bar", title=, x_label=, y_label=, x_ticks=)` —
  series are `{name, points: [[x, y], ...], color: "ink"|"alt", dashed: bool}`.
  Drawn as inline SVG, no chart library.
- `out.notice(body, level="info"|"ok"|"warn"|"error")`
- `out.text(body)`, `out.log(body)`, `out.json(data)`

Raise `ToolError("message", "optional detail")` for a failure the user can fix;
it renders as a fault panel instead of a stack trace.

### Tool options

`id`, `name`, `summary`, `category`, `inputs`, `run` are the required bits.
Also available: `description` (long prose under the title), `notes` (assumption
list), `tag` (language badge, drives syntax highlighting), `rev`, `timeout`
(seconds, default 30), and `autorun=False` if a tool should not fire on open.

### The source panel

Whatever sits between `# region: code` and `# endregion: code` is what gets
shown and copied — keep the real algorithm in there and the plumbing outside.
Without the markers the whole file is shown.

## Categories and sub-categories

`server\categories.json` holds the tree. Nest `children` as deep as you like:

```json
{
  "categories": [
    {
      "id": "electrical",
      "name": "Electrical",
      "children": [
        { "id": "power-distribution", "name": "Power Distribution" },
        { "id": "conductors", "name": "Conductors",
          "children": [{ "id": "awg", "name": "AWG Tables" }] }
      ]
    }
  ]
}
```

A tool joins one with `category="electrical/conductors/awg"`. Any path a tool
references that is not in the file gets created automatically, so the file is
only needed for ordering, descriptions and empty placeholders.

On the index the chips cascade: pick a category and a second row appears with
its children, a third for grandchildren, as deep as the tree goes. Selecting a
parent lists everything in its subtree. Search and category both live in the
URL, so a filtered view is linkable.

## API

| Method | Path | Does |
| --- | --- | --- |
| GET | `/api/catalog` | category tree + every tool |
| GET | `/api/tools/{id}` | one tool, including its source |
| POST | `/api/tools/{id}/run` | `{"params": {...}}` → result blocks |
| POST | `/api/reload` | re-scan `tools\` without restarting |
| GET | `/api/docs` | generated OpenAPI docs |

## Notes

- Tools run in-process on a worker thread with the output captured and a
  per-tool timeout. There is no sandbox — this is meant to sit on localhost.
- Inputs persist per tool in `localStorage`, so a sheet reopens where you left
  it. **Reset** restores the declared defaults.
- The theme toggle switches between the paper print and a cyanotype negative;
  both are defined entirely by the custom properties at the top of `theme.css`.
