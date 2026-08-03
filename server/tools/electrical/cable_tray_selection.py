"""Cable tray selection — size a tray and its expansion hardware from the load
and temperature swing it has to survive.

Built from the original cable_tray_selection() function; the selection tables are
kept verbatim. The original had a few bugs that crashed it (a list/int subtraction,
two off-by-one range walks, and an abs() over the table's text header row) plus a
missing run() and most of its inputs — all fixed/filled in here. See the notes on
the tool for the two engineering assumptions worth confirming.
"""

from toolkit import Result, Tool, ToolError, fields


# region: code
# Tray class rated for a given uniform load (rows, lb/ft) at a given support span
# (columns, ft). A blank cell means that class is not offered at that combination.
LOAD_CAPACITY_TABLE = [
    ["",         "8 ft", "10 ft", "12 ft", "16 ft", "20 ft"],
    ["25 lb/ft",  "",     "A",     "",      "",      ""],
    ["45 lb/ft",  "",     "",      "",      "",      "D"],
    ["50 lb/ft",  "8A",   "",      "12A",   "16A",   "20A"],
    ["65 lb/ft",  "",     "C",     "",      "",      ""],
    ["75 lb/ft",  "8B",   "",      "12B",   "16B",   "E;20B"],
    ["100 lb/ft", "8C",   "",      "12C",   "16C",   "20C"],
    ["120 lb/ft", "",     "D",     "",      "",      ""],
    ["200 lb/ft", "",     "E",     "",      "",      ""],
]

# Maximum spacing between expansion joints (ft) for a temperature differential
# (first column, °F) and tray material (remaining columns).
EXPANSION_JOINT_TABLE = [
    ["Temp", "Steel", "Aluminum", "Stainless Steel 304", "Stainless Steel 316"],
    [25, 512, 260, 347, 379],
    [50, 256, 130, 174, 189],
    [75, 171,  87, 116, 126],
    [100, 128, 65,  87,  95],
    [125, 102, 52,  69,  76],
    [150,  85, 43,  58,  63],
    [175,  73, 37,  50,  54],
]


def cable_tray_selection(maximum_span, tray_width, tray_height, tray_material,
                         cable_load, snow_load, ice_thickness, ice_density,
                         wind_impact_pressure, concentrated_load,
                         max_temp, min_temp, install_temp):
    """Return the acceptable tray classes, expansion-joint spacing and gap setting.

    Loads are summed to a uniform lb/ft, matched to the smallest tray class that
    is rated at or above both that load and the required span. Expansion-joint
    spacing is read from the row whose temperature differential is nearest to
    (max_temp - min_temp), in the tray-material column.
    """
    # --- loads (all reduced to lb/ft) ----------------------------------
    uniform_concentrated_load = (concentrated_load * 2) / maximum_span
    ice_load = (tray_width * ice_thickness / 144) * ice_density
    wind_load = (wind_impact_pressure * tray_height) / 12
    total_load = cable_load + snow_load + ice_load + wind_load

    header = LOAD_CAPACITY_TABLE[0]
    spans = [int(cell.split(" ")[0]) for cell in header[1:]]                 # [8,10,12,16,20]
    ratings = [int(row[0].split(" ")[0]) for row in LOAD_CAPACITY_TABLE[1:]]  # [25,45,...,200]

    # smallest column whose span covers the required span
    length_index = next((i + 1 for i, s in enumerate(spans) if maximum_span <= s), None)
    if length_index is None:
        raise ValueError(
            f"Maximum span {maximum_span} ft exceeds the largest tabulated span "
            f"({spans[-1]} ft).")

    # smallest row whose rating covers the total load
    load_index = next((i + 1 for i, r in enumerate(ratings) if total_load <= r), None)
    if load_index is None:
        raise ValueError(
            f"Total load {total_load:.1f} lb/ft exceeds the largest tabulated rating "
            f"({ratings[-1]} lb/ft).")

    # every class in the sub-table at or beyond both the load and the span
    acceptable_ratings = []
    for r in range(load_index, len(LOAD_CAPACITY_TABLE)):
        for c in range(length_index, len(header)):
            cell = LOAD_CAPACITY_TABLE[r][c]
            if cell:
                acceptable_ratings.extend(part.strip() for part in cell.split(";"))

    # --- expansion joints ----------------------------------------------
    temperature_differential = max_temp - min_temp
    data_rows = EXPANSION_JOINT_TABLE[1:]
    closest_row = min(data_rows, key=lambda row: abs(row[0] - temperature_differential))
    material_col = EXPANSION_JOINT_TABLE[0].index(tray_material)
    expansion_joint_spacing = closest_row[material_col]

    # fraction of the joint's max gap to set at the install temperature
    gap_setting = (install_temp - max_temp) / (min_temp - max_temp)

    return {
        "total_load": total_load,
        "ice_load": ice_load,
        "wind_load": wind_load,
        "uniform_concentrated_load": uniform_concentrated_load,
        "load_index": load_index,
        "length_index": length_index,
        "acceptable_ratings": acceptable_ratings,
        "temperature_differential": temperature_differential,
        "closest_temp": closest_row[0],
        "material_col": material_col,
        "expansion_joint_spacing": expansion_joint_spacing,
        "gap_setting": gap_setting,
    }
# endregion: code


def _dedupe(seq):
    seen = []
    for item in seq:
        if item not in seen:
            seen.append(item)
    return seen


def run(p):
    if p["min_temp"] >= p["max_temp"]:
        raise ToolError("Minimum temperature must be below maximum temperature.",
                        "The gap setting divides by (min − max), so they can't be equal.")

    try:
        res = cable_tray_selection(
            p["maximum_span"], p["tray_width"], p["tray_height"], p["tray_material"],
            p["cable_load"], p["snow_load"], p["ice_thickness"], p["ice_density"],
            p["wind_impact_pressure"], p["concentrated_load"],
            p["max_temp"], p["min_temp"], p["install_temp"],
        )
    except ValueError as exc:
        raise ToolError(str(exc),
                        "Reduce the load or span, or extend the tables for a larger tray.") from None

    out = Result()
    classes = _dedupe(res["acceptable_ratings"])

    # --- headline -------------------------------------------------------
    if classes:
        out.notice("Acceptable tray classes: " + ", ".join(classes), "ok")
    else:
        out.notice("No tabulated tray class meets this load at this span.", "warn")

    out.metric("Total load", f"{res['total_load']:.1f}", "lb/ft", emphasis=True,
               hint="cable + snow + ice + wind")
    out.metric("Cable", f"{p['cable_load']:.1f}", "lb/ft")
    out.metric("Snow", f"{p['snow_load']:.1f}", "lb/ft")
    out.metric("Ice", f"{res['ice_load']:.2f}", "lb/ft",
               hint=f"{p['tray_width']}\" wide × {p['ice_thickness']}\" ice")
    out.metric("Wind", f"{res['wind_load']:.2f}", "lb/ft",
               hint=f"{p['wind_impact_pressure']} psf × {p['tray_height']}\" tall")
    out.metric("Concentrated (uniform)", f"{res['uniform_concentrated_load']:.2f}", "lb/ft",
               hint="reported only — not added to total load")
    out.metric("Expansion-joint spacing", f"{res['expansion_joint_spacing']}", "ft",
               emphasis=True,
               hint=f"{p['tray_material']}, ΔT {res['temperature_differential']:.0f} °F")
    out.metric("Gap setting", f"{res['gap_setting']:.2f}",
               hint="fraction of the joint's max gap at install temp")

    # --- load capacity table, acceptable region flagged ----------------
    header = LOAD_CAPACITY_TABLE[0]
    load_cols = [{"label": "LOAD \\ SPAN", "align": "left"}] + [{"label": h} for h in header[1:]]
    load_rows = []
    for r in range(1, len(LOAD_CAPACITY_TABLE)):
        row = LOAD_CAPACITY_TABLE[r]
        cells = [{"value": row[0], "flag": r == res["load_index"]}]
        for c in range(1, len(header)):
            picked = (r >= res["load_index"] and c >= res["length_index"] and bool(row[c]))
            cells.append({"value": row[c] or "·", "flag": picked})
        load_rows.append(cells)
    out.table(load_cols, load_rows,
              title="Load capacity — acceptable classes flagged",
              note="Flagged cells are classes rated at or above both the total load "
                   "and the required span. Row label flagged = governing load row.")

    # --- expansion joint table, chosen cell flagged --------------------
    exp_header = EXPANSION_JOINT_TABLE[0]
    exp_cols = [{"label": "ΔT °F"}] + [{"label": m} for m in exp_header[1:]]
    exp_rows = []
    for row in EXPANSION_JOINT_TABLE[1:]:
        on_row = row[0] == res["closest_temp"]
        cells = [{"value": row[0], "flag": on_row}]
        for c in range(1, len(row)):
            cells.append({"value": row[c], "flag": on_row and c == res["material_col"]})
        exp_rows.append(cells)
    out.table(exp_cols, exp_rows,
              title="Expansion-joint spacing (ft) — selected cell flagged",
              note=f"Nearest tabulated ΔT to {res['temperature_differential']:.0f} °F is "
                   f"{res['closest_temp']} °F; column = {p['tray_material']}.")

    return out


TOOL = Tool(
    id="cable-tray-selection",
    name="Cable Tray — Selection",
    summary="Sizes a cable tray and its expansion hardware from the combined cable, "
            "snow, ice and wind load plus the installation temperature swing.",
    description=(
        "Sums the cable, snow, ice and wind loads into a uniform lb/ft, then picks the "
        "tray classes rated at or above that load for the required support span. "
        "Expansion-joint spacing comes from the temperature differential (max − min) and "
        "the tray material; the gap setting is where the install temperature falls in "
        "that swing. Tray material is a dropdown because it must match one of the "
        "tabulated materials exactly."
    ),
    category="electrical/supports",
    rev="1.0",
    inputs=[
        fields.select(
            "tray_material", "Tray material",
            [("Steel", "Steel"), ("Aluminum", "Aluminum"),
             ("Stainless Steel 304", "Stainless Steel 304"),
             ("Stainless Steel 316", "Stainless Steel 316")],
            "Aluminum", group="Tray",
            help="Sets the expansion-joint spacing column."),
        fields.integer("maximum_span", "Maximum span", 10, min=1, max=20, unit="ft",
                       group="Tray", help="Distance between tray supports."),
        fields.integer("tray_width", "Tray width", 24, min=1, max=100, unit="in", group="Tray"),
        fields.integer("tray_height", "Tray height", 6, min=1, max=20, unit="in", group="Tray",
                       help="Loading (side-rail) height — the wind-catching face."),

        fields.number("cable_load", "Cable load", 10, min=0, unit="lb/ft", group="Loads",
                      help="Weight of the cable fill."),
        fields.number("snow_load", "Snow load", 5, min=0, unit="lb/ft", group="Loads"),
        fields.number("ice_thickness", "Ice thickness", 0.5, min=0, step=0.25, unit="in",
                      group="Loads"),
        fields.number("ice_density", "Ice density", 57, min=0, unit="lb/ft³", group="Loads",
                      help="~57 for solid glaze ice."),
        fields.number("wind_impact_pressure", "Wind pressure", 20, min=0, unit="psf",
                      group="Loads", help="Design wind impact pressure on the side rail."),
        fields.number("concentrated_load", "Concentrated load", 200, min=0, unit="lb",
                      group="Loads", help="Point load (e.g. a worker) at midspan."),

        fields.number("max_temp", "Max temperature", 100, unit="°F", group="Temperature"),
        fields.number("min_temp", "Min temperature", 0, unit="°F", group="Temperature"),
        fields.number("install_temp", "Install temperature", 70, unit="°F", group="Temperature",
                      help="Temperature at the time the joints are set."),
    ],
    notes=[
        "Load capacity and expansion-joint spacing come from the built-in tables; a "
        "load or span past their range raises an error rather than extrapolating.",
        "Total load = cable + snow + ice + wind. The concentrated load is reported as an "
        "equivalent uniform load but NOT added to the total — confirm if it should be.",
        "Acceptable classes = every non-empty cell rated at or above the load and span. "
        "Confirm this is the selection rule you want (vs. only the single minimum class).",
        "Expansion-joint spacing is in feet; gap setting is the fraction (0–1) of the "
        "joint's maximum gap to set at the install temperature.",
    ],
    run=run,
)
