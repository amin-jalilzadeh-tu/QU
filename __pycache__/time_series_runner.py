"""
time_series_runner_wide.py

Generates a single wide-format CSV with columns:

entity_id, record_type, line_id,
voltage_pu, p_injection_kW, q_injection_kvar, pf,
i_from_a, i_to_a, line_rating_a, loading_percent,
<time step 1>, <time step 2>, ...

Where:
 - If record_type != 'line', then 'entity_id' is the node name (B0001, Feeder1, MainSubstation, etc.)
   and the time-step columns store node voltage in p.u.
   building vs station vs feeder is decided by node name:
     e.g. node_name=="MainSubstation" => 'station'
          node_name.startswith("Feeder") => 'feeder'
          node_name.startswith("B") => 'building'
          else => 'other_node'
   'line_id' is empty for these rows.

 - If record_type='line', we store line_id=the line name, entity_id=''
   The time-step columns store the line current in A.
   We also store final i_from_a, line_rating_a, loading_percent, etc.

We also approximate q_injection_kvar and pf for demonstration, since the dummy solver doesn't provide them.
"""

import csv
import copy
import math

from build_network_model import build_network_model, update_building_loads
from json_generator import generate_json_data
from power_flow_solver import solve_power_flow_in_memory

def load_time_series_data(ts_file):
    """
    Reads time_series_loads.csv with columns:
      building_id, Energy, 00:00:00, 00:15:00, 00:30:00, ...
    We only parse rows where Energy=='total_electricity'.
    Returns load_data[b_id] = [val_t0, val_t1, ...],
    plus a list of time_headers.
    """
    load_data = {}
    time_headers = []

    # Adjust delimiter if needed (',' instead of '\t')
    with open(ts_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=',')
        headers = reader.fieldnames
        time_headers = headers[2:]  # from the 3rd column onward

        for row in reader:
            if row["Energy"].strip().lower() == "total_electricity":
                b_id = row["building_id"]
                values = []
                for h in time_headers:
                    values.append(float(row[h]))
                load_data[b_id] = values

    return load_data, time_headers


def get_node_record_type(node_name):
    """
    Logic for deciding if a node is building, station, feeder, or other_node.
    """
    if node_name.startswith("B"):
        return "building"
    elif node_name == "MainSubstation":
        return "station"
    elif node_name.startswith("Feeder"):
        return "feeder"
    else:
        return "other_node"


def run_time_series_pf_wide(
    buildings_file="buildings_demo.csv",
    lines_file="lines_demo.csv",
    assignments_file="building_assignments.csv",
    ts_file="time_series_loads.csv",
    output_csv="time_series_wide.csv"
):
    print("[time_series_runner_wide] Building base model from CSVs...")
    base_model = build_network_model(buildings_file, lines_file, assignments_file)

    # Store line ratings, node names, etc.
    line_rating_map = {}
    line_id_map = {}
    for ln in base_model["lines"]:
        line_rating_map[ln["id"]] = ln["i_n"]  # nominal rating in A
        line_id_map[ln["id"]] = ln["name"]

    node_id_to_name = {}
    for nd in base_model["nodes"]:
        node_id_to_name[nd["id"]] = nd["name"]

    # parse time-series loads
    load_data, time_headers = load_time_series_data(ts_file)
    num_steps = len(time_headers)
    print(f"[time_series_runner_wide] Found {num_steps} time columns => {time_headers}")

    # We'll accumulate time-series arrays for nodes & lines
    node_acc = {}   # node_acc[node_id]["time_values"] = [voltage@t0, voltage@t1, ...]
    node_final = {} # store final-step p_inj, q_inj, etc.

    line_acc = {}
    line_final = {}

    # 1) Loop over time steps, solve PF
    for t_idx in range(num_steps):
        model_t = copy.deepcopy(base_model)

        # build load dict for this time
        step_load = {}
        for b_id, arr in load_data.items():
            step_load[b_id] = arr[t_idx]
        update_building_loads(model_t, step_load)

        # solve PF in memory
        input_dict = generate_json_data(model_t)
        pf_results = solve_power_flow_in_memory(input_dict)
        sym_data = pf_results["sym"]["data"]  # {node:[], line:[], shunt:[]}

        # 2) parse node results
        for nd_obj in sym_data["node"]:
            node_id = nd_obj["id"]
            node_name = node_id_to_name.get(node_id, "")
            v_pu = nd_obj.get("u_pu", 1.0)
            p_w = nd_obj.get("p", 0.0)
            p_kW = p_w/1000.0
            # approximate q, pf
            q_w = 0.3 * p_w
            q_kvar = q_w/1000.0
            s_kW = math.sqrt((p_kW**2)+(q_kvar**2)) if abs(p_kW)>1e-9 or abs(q_kvar)>1e-9 else 1e-9
            pf_val = abs(p_kW/s_kW) if s_kW>1e-9 else 1.0

            if node_id not in node_acc:
                node_acc[node_id] = {"time_values":[None]*num_steps}
                node_final[node_id] = {
                    "p_injection_kW":0.0, "q_injection_kvar":0.0, "pf":1.0, "voltage_pu":1.0
                }
            node_acc[node_id]["time_values"][t_idx] = round(v_pu,4)

            # final
            node_final[node_id]["p_injection_kW"] = round(p_kW,3)
            node_final[node_id]["q_injection_kvar"] = round(q_kvar,3)
            node_final[node_id]["pf"] = round(pf_val,3)
            node_final[node_id]["voltage_pu"] = round(v_pu,3)

        # 3) parse line results
        for ln_obj in sym_data["line"]:
            l_id = ln_obj["id"]
            i_from = ln_obj.get("i_from", 0.0)
            if l_id not in line_acc:
                line_acc[l_id] = {"time_values":[None]*num_steps}
                line_final[l_id] = {
                    "i_from_a":0.0, "line_rating_a":line_rating_map.get(l_id,9999), "loading_percent":0.0
                }
            line_acc[l_id]["time_values"][t_idx] = round(i_from,3)

            rating_a = line_rating_map.get(l_id,9999)
            load_pct = 0.0
            if rating_a>0:
                load_pct = (i_from/rating_a)*100.0
            line_final[l_id]["i_from_a"] = round(i_from,3)
            line_final[l_id]["line_rating_a"] = rating_a
            line_final[l_id]["loading_percent"] = round(load_pct,2)

    # 4) Build final CSV
    # columns
    out_cols = [
        "entity_id","record_type","line_id",
        "voltage_pu","p_injection_kW","q_injection_kvar","pf",
        "i_from_a","i_to_a","line_rating_a","loading_percent"
    ] + time_headers

    rows = []

    # Node rows (buildings, feeders, station, etc.)
    for nd_id, acc in node_acc.items():
        finald = node_final[nd_id]
        node_name = node_id_to_name[nd_id]
        r_type = get_node_record_type(node_name)  # 'building','station','feeder','other_node'

        row = {
            "entity_id": node_name,   # e.g. "B0001", "MainSubstation", "Feeder1"
            "record_type": r_type,
            "line_id": "",
            "voltage_pu": finald["voltage_pu"],
            "p_injection_kW": finald["p_injection_kW"],
            "q_injection_kvar": finald["q_injection_kvar"],
            "pf": finald["pf"],
            "i_from_a": "",
            "i_to_a": "",
            "line_rating_a": "",
            "loading_percent": ""
        }
        # fill time columns with node voltage
        for i, t_col in enumerate(time_headers):
            row[t_col] = acc["time_values"][i]
        rows.append(row)

    # Line rows
    for ln_id, acc in line_acc.items():
        finald = line_final[ln_id]
        row = {
            "entity_id": "",
            "record_type": "line",
            "line_id": line_id_map.get(ln_id, f"L_{ln_id}"),
            "voltage_pu": "",
            "p_injection_kW": "",
            "q_injection_kvar": "",
            "pf": "",
            "i_from_a": finald["i_from_a"],
            "i_to_a": "",   # not in dummy solver
            "line_rating_a": finald["line_rating_a"],
            "loading_percent": finald["loading_percent"]
        }
        # fill time columns with line current
        for i, t_col in enumerate(time_headers):
            row[t_col] = acc["time_values"][i]
        rows.append(row)

    with open(output_csv,"w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols)
        writer.writeheader()
        for rw in rows:
            writer.writerow(rw)

    print(f"[time_series_runner_wide] Completed. Wrote {len(rows)} rows => {output_csv}")


if __name__=="__main__":
    """
    Example usage:
    python time_series_runner_wide.py
    - We expect time_series_loads.csv, buildings_demo.csv, lines_demo.csv,
      building_assignments.csv in the same folder.
    - Output => time_series_wide.csv
    """
    run_time_series_pf_wide(
        "buildings_demo.csv",
        "lines_demo.csv",
        "building_assignments.csv",
        "time_series_loads.csv",
        "time_series_wide.csv"
    )
