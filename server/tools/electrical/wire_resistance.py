"""AWG resistance lookup — feeds the resistivity input of the voltage drop tools."""

from toolkit import Result, Tool, ToolError, fields


# region: code
# DC resistance of solid conductor at 20 C, ohms per 1000 ft (NEC ch.9 tbl.8 basis).
AWG_OHMS_PER_KFT = {
    "4/0": 0.0490, "3/0": 0.0618, "2/0": 0.0779, "1/0": 0.0983,
    "1": 0.1239, "2": 0.1563, "4": 0.2485, "6": 0.3951, "8": 0.6282,
    "10": 0.9989, "12": 1.588, "14": 2.525, "16": 4.016, "18": 6.385,
    "20": 10.15, "22": 16.14, "24": 25.67, "26": 40.81, "28": 64.90,
}

# Resistance relative to copper, and the temperature coefficient per degree C.
MATERIALS = {
    "copper": (1.000, 0.00393),
    "aluminium": (1.640, 0.00403),
    "tinned-copper": (1.020, 0.00393),
}


def wire_resistance(gauge, material="copper", temp_c=20.0, stranded=False):
    """Ohms per foot of a single conductor, corrected for material and temperature."""
    base = AWG_OHMS_PER_KFT[gauge] / 1000.0
    factor, alpha = MATERIALS[material]
    r = base * factor
    if stranded:
        r *= 1.02                          # stranding adds length per unit of run
    return r * (1 + alpha * (temp_c - 20.0))
# endregion: code


def run(p):
    gauge = p["gauge"]
    material = p["material"]
    temp = p["temp_c"]
    stranded = p["stranded"]
    length = p["length_ft"]
    current = p["current_a"]
    supply = p["supply_v"]

    if gauge not in AWG_OHMS_PER_KFT:
        raise ToolError(f"No table entry for {gauge} AWG.")

    per_ft = wire_resistance(gauge, material, temp, stranded)
    loop = per_ft * length * 2
    drop = loop * current

    out = Result()
    out.metric("Resistivity", f"{per_ft:.6f}", "Ω/ft", emphasis=True,
               hint="paste this into the voltage drop tool")
    out.metric("Per 1000 ft", f"{per_ft * 1000:.4f}", "Ω")
    out.metric("Per metre", f"{per_ft / 0.3048:.6f}", "Ω/m")
    out.metric("Loop resistance", f"{loop:.4f}", "Ω",
               hint=f"{length:,.0f} ft out and back")
    out.metric("Drop at load", f"{drop:.3f}", "V",
               hint=f"{current:g} A steady")
    if supply > 0:
        out.metric("Drop", f"{drop / supply * 100:.2f}", "%",
                   emphasis=drop / supply > 0.1,
                   hint=f"of {supply:g} V")
        out.notice(
            f"{gauge} AWG {material} at {temp:g} °C over {length:,.0f} ft loses "
            f"{drop:.3f} V at {current:g} A — {drop / supply * 100:.2f}% of a "
            f"{supply:g} V supply.",
            "warn" if drop / supply > 0.1 else "ok")

    rows = []
    for g in AWG_OHMS_PER_KFT:
        r = wire_resistance(g, material, temp, stranded)
        d = r * length * 2 * current
        rows.append([
            g,
            f"{r:.6f}",
            f"{r * 1000:.4f}",
            f"{r * length * 2:.4f}",
            {"value": f"{d:.3f}", "flag": supply > 0 and d / supply > 0.1},
            {"value": f"{d / supply * 100:.2f}" if supply > 0 else "—",
             "flag": supply > 0 and d / supply > 0.1},
        ])
    out.table(
        [{"label": "AWG", "align": "left"}, {"label": "R", "unit": "Ω/ft"},
         {"label": "R", "unit": "Ω/kft"}, {"label": "R LOOP", "unit": "Ω"},
         {"label": "DROP", "unit": "V"}, {"label": "DROP", "unit": "%"}],
        rows,
        title=f"Full table — {material}, {temp:g} °C, {length:,.0f} ft, {current:g} A",
        note="Flagged rows exceed the 10% rule of thumb.",
    )
    return out


TOOL = Tool(
    id="wire-resistance",
    name="Wire Resistance",
    summary="AWG resistance per foot for copper or aluminium, corrected for temperature, "
            "with the loop drop for a given run and load.",
    description=(
        "Table 8 DC resistance for solid conductors at 20 °C, scaled by material and "
        "temperature coefficient. The per-foot figure is what the voltage drop tools want "
        "for their resistivity input — they apply the ×2 for the return leg themselves."
    ),
    category="electrical/conductors",
    inputs=[
        fields.select("gauge", "Gauge", list(AWG_OHMS_PER_KFT.keys()), "18",
                      unit="AWG", group="Conductor"),
        fields.select("material", "Material",
                      [("copper", "Copper"), ("aluminium", "Aluminium"),
                       ("tinned-copper", "Tinned copper")],
                      "copper", group="Conductor"),
        fields.boolean("stranded", "Stranded", False, group="Conductor",
                       help="Adds 2% for the lay of the strands."),
        fields.number("temp_c", "Conductor temperature", 20, unit="°C", min=-60, max=200,
                      group="Conductor"),
        fields.number("length_ft", "One-way run", 140, unit="ft", min=0, group="Run",
                      help="Doubled internally for the return conductor."),
        fields.number("current_a", "Current", 1.667, unit="A", min=0, step=0.001, group="Run"),
        fields.number("supply_v", "Supply", 24, unit="V", min=0, group="Run",
                      help="Set to 0 to skip the percentage column."),
    ],
    notes=["Solid-conductor DC values; skin effect and AC reactance are ignored."],
    run=run,
)
