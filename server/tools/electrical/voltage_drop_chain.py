"""Iterative voltage drop across a daisy-chained run of constant-power devices."""

from toolkit import Result, Tool, ToolError, fields


# region: code
def solve_voltage_drops(num_devices, distances, supply_voltages, watts,
                        resistivity, convergence_factor, max_iterations=500):
    """Relax the current/voltage-drop pair until the drops stop moving.

    Devices hang off one run in series. Segment `i` carries the current of every
    device from `i` downstream, and its loop length is `distance * 2` (out and
    back). Each device draws constant power, so when the line sags its current
    climbs, which sags the line further -- hence the iteration.

    Returns (voltage_drops, currents, iterations, converged, history).
    """

    currents = [0] * num_devices
    for i, w in enumerate(watts):
        currents[i] = w / supply_voltages[i]

    voltage_drops = [0.0] * num_devices
    history = []
    iterations = 0

    while True:
        change_amount = 0                                    # largest move this pass
        iterations += 1

        for index, dist in enumerate(distances):
            resistance = dist * 2 * resistivity              # loop resistance of the segment

            total_current = 0
            for i in range(index, num_devices):              # everything downstream
                total_current += currents[i]

            local_voltage_drop = resistance * total_current  # drop across this segment alone

            if index > 0:                                    # stack it on the upstream drop
                new_voltage_drop = local_voltage_drop + voltage_drops[index - 1]
            else:
                new_voltage_drop = local_voltage_drop

            if abs(new_voltage_drop - voltage_drops[index]) > change_amount:
                change_amount = abs(new_voltage_drop - voltage_drops[index])

            remaining = supply_voltages[index] - new_voltage_drop
            if remaining <= 0:
                raise ValueError(
                    f"Device {index + 1} collapses the run: all {supply_voltages[index]:g} V is "
                    f"eaten by {new_voltage_drop:.2f} V of line loss.")

            currents[index] = watts[index] / remaining       # constant power -> new current
            voltage_drops[index] = new_voltage_drop

        history.append(change_amount)

        if change_amount < convergence_factor:               # settled
            return voltage_drops, currents, iterations, True, history
        if iterations >= max_iterations:                     # bail out, still moving
            return voltage_drops, currents, iterations, False, history
# endregion: code


def run(p):
    n = p["num_devices"]
    if n < 1:
        raise ToolError("Need at least one device.")

    distances = p["distances"]
    voltages = p["voltages"]
    watts = p["watts"]
    resistivity = p["resistivity"]
    limit_pct = p["drop_limit_pct"]

    for i, v in enumerate(voltages):
        if v <= 0:
            raise ToolError(f"Device {i + 1} has a supply voltage of {v:g} V.")

    try:
        drops, currents, iterations, converged, history = solve_voltage_drops(
            n, distances, voltages, watts,
            resistivity, p["convergence_factor"], p["max_iterations"])
    except ValueError as exc:
        raise ToolError(
            str(exc),
            "The run diverges: line loss grows faster than the devices can pull. "
            "Shorten the run, drop the resistivity (heavier wire) or raise the supply."
        ) from None
    except ZeroDivisionError:
        raise ToolError("A device saw exactly 0 V at its terminals.") from None

    out = Result()

    # --- rebuild the per-segment picture from the settled currents -----
    segment_current = [sum(currents[i:]) for i in range(n)]
    resistances = [d * 2 * resistivity for d in distances]
    segment_drop = [resistances[i] * segment_current[i] for i in range(n)]
    device_voltage = [voltages[i] - drops[i] for i in range(n)]
    drop_pct = [drops[i] / voltages[i] * 100 for i in range(n)]
    over = [i for i in range(n) if drop_pct[i] > limit_pct]

    source_current = segment_current[0]
    source_power = voltages[0] * source_current
    load_power = sum(watts)
    loss = source_power - load_power

    # --- headline numbers ---------------------------------------------
    out.metric("Devices", n)
    out.metric("Run length", f"{sum(distances):,.0f}", "ft")
    out.metric("Source current", f"{source_current:.3f}", "A", emphasis=True)
    out.metric("End-of-run voltage", f"{device_voltage[-1]:.3f}", "V", emphasis=True,
               hint=f"{drop_pct[-1]:.2f}% below the {voltages[-1]:g} V supply")
    out.metric("Worst drop", f"{max(drop_pct):.2f}", "%",
               hint=f"device {drop_pct.index(max(drop_pct)) + 1}")
    out.metric("Line loss", f"{loss:.2f}", "W",
               hint=f"{loss / source_power * 100:.1f}% of {source_power:.1f} W drawn")
    out.metric("Iterations", iterations,
               hint="converged" if converged else "HIT THE CAP")

    # --- verdict -------------------------------------------------------
    if not converged:
        out.notice(
            f"Did not converge in {iterations} iterations — the largest drop still moved "
            f"{history[-1]:.3e} V on the last pass, against a convergence factor of "
            f"{p['convergence_factor']:g}. Raise the iteration cap or loosen the factor.",
            "warn")
    if over:
        listed = ", ".join(str(i + 1) for i in over)
        out.notice(
            f"{len(over)} device(s) exceed the {limit_pct:g}% advisory drop limit: {listed}. "
            f"Worst is device {drop_pct.index(max(drop_pct)) + 1} at {max(drop_pct):.2f}% "
            f"({device_voltage[drop_pct.index(max(drop_pct))]:.2f} V at the terminals).",
            "warn")
    elif converged:
        out.notice(
            f"Every device holds within {limit_pct:g}% of supply. "
            f"Worst case is {max(drop_pct):.2f}% at device "
            f"{drop_pct.index(max(drop_pct)) + 1}.", "ok")

    # --- the sheet ------------------------------------------------------
    rows = []
    run_length = 0.0
    for i in range(n):
        run_length += distances[i]
        rows.append([
            f"{i + 1}",
            f"{distances[i]:,.0f}",
            f"{run_length:,.0f}",
            f"{resistances[i]:.4f}",
            f"{segment_current[i]:.4f}",
            f"{segment_drop[i]:.4f}",
            f"{drops[i]:.4f}",
            {"value": f"{device_voltage[i]:.4f}", "flag": i in over},
            {"value": f"{drop_pct[i]:.2f}", "flag": i in over},
            f"{currents[i]:.5f}",
        ])
    out.table(
        [
            {"label": "DEV", "align": "left"},
            {"label": "SEG", "unit": "ft"},
            {"label": "FROM SRC", "unit": "ft"},
            {"label": "R LOOP", "unit": "Ω"},
            {"label": "SEG I", "unit": "A"},
            {"label": "SEG DROP", "unit": "V"},
            {"label": "CUM DROP", "unit": "V"},
            {"label": "V AT DEV", "unit": "V"},
            {"label": "DROP", "unit": "%"},
            {"label": "DEV I", "unit": "A"},
        ],
        rows,
        title="Per-device results",
        note="SEG I is the current carried by that segment — every device from here "
             "to the end of the run. R LOOP is distance × 2 × resistivity.",
    )

    # --- charts ----------------------------------------------------------
    cumulative = []
    running = 0.0
    for d in distances:
        running += d
        cumulative.append(running)

    limit_v = voltages[0] * (1 - limit_pct / 100)
    out.chart(
        [
            {"name": "Voltage at device", "points": [[0.0, voltages[0]]] +
                [[cumulative[i], device_voltage[i]] for i in range(n)]},
            {"name": f"{limit_pct:g}% limit", "color": "alt", "dashed": True,
             "points": [[0.0, limit_v], [cumulative[-1], limit_v]]},
        ],
        title="Voltage profile along the run",
        x_label="DISTANCE FROM SOURCE (ft)",
        y_label="VOLTS",
    )

    out.chart(
        [{"name": "Drop", "points": [[i + 1, drop_pct[i]] for i in range(n)]}],
        title="Cumulative drop by device",
        kind="bar",
        x_label="DEVICE",
        y_label="DROP (%)",
        x_ticks=[[i + 1, str(i + 1)] for i in range(n)],
    )

    # --- solver trace -----------------------------------------------------
    trace = ["ITER    MAX ΔV"]
    shown = history if len(history) <= 24 else history[:12] + [None] + history[-11:]
    index = 0
    for entry in shown:
        if entry is None:
            trace.append(f"  ...   ({len(history) - 23} passes elided)")
            index = len(history) - 11
            continue
        index += 1
        trace.append(f"{index:>5}   {entry:.3e}")
    trace.append("")
    trace.append(f"stop: max ΔV {history[-1]:.3e} "
                 f"{'<' if converged else '>='} convergence factor "
                 f"{p['convergence_factor']:g}")
    out.log("\n".join(trace), title="Convergence trace")

    return out


TOOL = Tool(
    id="voltage-drop-chain",
    name="Voltage Drop — Daisy Chain",
    summary="Iteratively solves line loss down a series run of constant-power devices, "
            "where sag raises current and current deepens sag.",
    description=(
        "Devices are wired in one series run: the first segment carries every device's "
        "current, the last carries only its own. Each device is treated as a constant-power "
        "load, so its current is watts ÷ (supply − accumulated drop) — which means current "
        "and drop chase each other. The solver sweeps the run repeatedly until the largest "
        "change in any accumulated drop falls below the convergence factor.\n\n"
        "Resistivity is the loop-metre value for your conductor in ohms per foot of "
        "single-conductor length; the solver doubles the distance for the return path. "
    ),
    category="electrical/power-distribution",
    rev="1.1",
    inputs=[
        fields.integer(
            "num_devices", "Number of devices", 1, min=1, max=200, group="Array",
            help="Devices on the run, ordered from the supply outward. "
                 "Changing this resizes the table below."),
        fields.number_list(
            "distances", "Distance", [10],
            unit="ft", table="devices", length_from="num_devices",
            help="Length of the segment feeding each device, measured from the previous "
                 "device (or the supply, for the first)."),
        fields.number_list(
            "voltages", "Supply", [24] * 8,
            unit="V", table="devices", length_from="num_devices",
            help="Nominal source voltage seen by each device before line loss."),
        fields.number_list(
            "watts", "Load", [5] * 8,
            unit="W", table="devices", length_from="num_devices",
            help="Constant power drawn by each device."),
        fields.number(
            "resistivity", "Resistivity", 0.0065, unit="Ω/ft", step=0.0001, min=0,
            group="Conductor",
            help="Per-foot resistance of one conductor. Loop resistance is distance × 2 × this."),
        fields.number(
            "convergence_factor", "Convergence factor", 0.00001, unit="V", step=0.000001, min=0,
            group="Solver",
            help="Stop once the largest change in accumulated drop falls below this."),
        fields.integer(
            "max_iterations", "Iteration cap", 500, min=1, max=100000, group="Solver",
            help="Safety net so a diverging run cannot spin forever."),
        fields.number(
            "drop_limit_pct", "Advisory drop limit", 3, unit="%", step=0.5, min=0, group="Solver",
            help="Reporting only — devices past this are flagged. 10% is the usual "
                 "rule of thumb for low-voltage runs."),
    ],
    notes=[
        "Assumes a single series run with no branches or taps.",
        "Resistivity is taken as constant — no temperature rise on the conductors.",
        "Devices are modelled as ideal constant-power loads with no minimum operating voltage.",
    ],
    run=run,
)
