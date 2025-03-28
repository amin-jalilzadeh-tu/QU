"""
time_series_runner_long.py

Runs time-series power flow for each time step in 'time_series_loads.csv',
then outputs a LONG format CSV with one row per (time_step, entity).

Columns:
  time_step,
  entity_id, record_type, line_id,
  voltage_pu, p_injection_kW, q_injection_kvar, pf,
  i_from_a, i_to_a, line_rating_a, loading_percent

We detect building vs station vs feeder from the node_name:
  - starts with 'B' => building
  - 'MainSubstation' => station
  - starts with 'Feeder' => feeder
  - else => other_node
We approximate Q and PF because the dummy solver doesn't provide them.
"""

import csv
import copy
import math
import os

from build_network_model import build_network_model, update_building_loads
from json_generator import generate_json_data
from power_flow_solver import solve_power_flow_in_memory

def load_time_series_data(ts_file):
    """
    Reads time_series_loads.csv (generated by generate_time_series_loads),
    only parse rows where Energy=='total_electricity' for net building load.
    Returns (load_data, time_headers) where:
      load_data[b_id] = [ val_t0, val_t1, ... ]
      time_headers = [ '00:00:00', '00:15:00', ... ]
    """
    load_data = {}
    time_headers = []

    with open(ts_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        time_headers = headers[2:]  # from third column onward

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
    Decide if node is building, station, feeder, or other_node.
    """
    if node_name.startswith("B"):
        return "building"
    elif node_name == "MainSubstation":
        return "station"
    elif node_name.startswith("Feeder"):
        return "feeder"
    else:
        return "other_node"

def run_time_series_pf_long(
    buildings_file="buildings_demo.csv",
    lines_file="lines_demo.csv",
    assignments_file="building_assignments.csv",
    ts_file="time_series_loads.csv",
    output_csv="time_series_long.csv"
):
    """
    1) Build a base model from (buildings_file, lines_file, assignments_file).
    2) Load time-series loads from (ts_file) => net building load at each time step.
    3) For each time step:
       a) update building loads in the model
       b) solve PF in memory
       c) parse results for each node + line
       d) write a row for each entity to results

    The final CSV is a LONG format with one row per (time_step, entity).
    Columns:
      time_step, entity_id, record_type, line_id,
      voltage_pu, p_injection_kW, q_injection_kvar, pf,
      i_from_a, i_to_a, line_rating_a, loading_percent
    """
    # 1) Build base model
    print("[time_series_runner_long] Building base model from CSVs.")
    base_model = build_network_model(buildings_file, lines_file, assignments_file)

    # 2) Load time-series net loads
    if not os.path.exists(ts_file):
        print(f"[time_series_runner_long] No {ts_file} => skip.")
        return
    load_data, time_headers = load_time_series_data(ts_file)
    num_steps = len(time_headers)
    print(f"[time_series_runner_long] Found {num_steps} time columns => {time_headers}")

    # We'll keep line ratings, node names for reference
    line_rating_map = {}
    line_id_map = {}
    for ln in base_model["lines"]:
        line_rating_map[ln["id"]] = ln["i_n"]  # nominal rating in A
        line_id_map[ln["id"]] = ln["name"]

    node_id_to_name = {}
    for nd in base_model["nodes"]:
        node_id_to_name[nd["id"]] = nd["name"]

    # We'll gather results in memory as a list of dict rows
    # Each row => {time_step, entity_id, record_type, line_id, voltage_pu, ...}
    results_rows = []

    # 3) Loop over each time step
    for t_idx in range(num_steps):
        time_label = time_headers[t_idx]  # e.g. "00:00:00"
        # copy model
        model_t = copy.deepcopy(base_model)
        # build load dict for this time
        step_load = {}
        for b_id, arr in load_data.items():
            step_load[b_id] = arr[t_idx]
        update_building_loads(model_t, step_load)

        # solve PF
        input_dict = generate_json_data(model_t)
        pf_res = solve_power_flow_in_memory(input_dict)
        sym_data = pf_res["sym"]["data"]  # node:[], line:[], shunt:[]

        # parse node results
        for nd_obj in sym_data["node"]:
            node_id = nd_obj["id"]
            node_name = node_id_to_name[node_id]
            r_type = get_node_record_type(node_name)  # building, station, feeder, other
            v_pu = nd_obj.get("u_pu", 1.0)
            p_w = nd_obj.get("p", 0.0)
            p_kW = p_w/1000.0
            # approximate q, pf
            q_w = 0.3*p_w
            q_kvar = q_w/1000.0
            s_kW = math.sqrt((p_kW**2)+(q_kvar**2)) if abs(p_kW)>1e-9 or abs(q_kvar)>1e-9 else 1e-9
            pf_val = abs(p_kW/s_kW) if s_kW>1e-9 else 1.0

            row = {
                "time_step": time_label,
                "entity_id": node_name,
                "record_type": r_type,
                "line_id": "",
                "voltage_pu": round(v_pu,3),
                "p_injection_kW": round(p_kW,3),
                "q_injection_kvar": round(q_kvar,3),
                "pf": round(pf_val,3),
                "i_from_a": "",
                "i_to_a": "",
                "line_rating_a": "",
                "loading_percent": ""
            }
            results_rows.append(row)

        # parse line results
        for ln_obj in sym_data["line"]:
            l_id = ln_obj["id"]
            i_from = ln_obj.get("i_from", 0.0)
            rating_a = line_rating_map.get(l_id, 9999)
            load_pct = 0.0
            if rating_a>0:
                load_pct = (i_from/rating_a)*100.0

            row = {
                "time_step": time_label,
                "entity_id": "",
                "record_type": "line",
                "line_id": line_id_map[l_id],
                "voltage_pu": "",
                "p_injection_kW": "",
                "q_injection_kvar": "",
                "pf": "",
                "i_from_a": round(i_from,3),
                "i_to_a": "",
                "line_rating_a": rating_a,
                "loading_percent": round(load_pct,2)
            }
            results_rows.append(row)

    # 4) Write final CSV
    out_cols = [
        "time_step","entity_id","record_type","line_id",
        "voltage_pu","p_injection_kW","q_injection_kvar","pf",
        "i_from_a","i_to_a","line_rating_a","loading_percent"
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols)
        writer.writeheader()
        for rw in results_rows:
            writer.writerow(rw)

    print(f"[time_series_runner_long] Wrote {len(results_rows)} rows => '{output_csv}'")


if __name__=="__main__":
    """
    Example usage if run standalone:
    python time_series_runner_long.py
    Make sure buildings_demo.csv, lines_demo.csv, building_assignments.csv, time_series_loads.csv exist.
    This will produce time_series_long.csv (one row per time_step per entity).
    """
    run_time_series_pf_long(
        buildings_file="buildings_demo.csv",
        lines_file="lines_demo.csv",
        assignments_file="building_assignments.csv",
        ts_file="time_series_loads.csv",
        output_csv="time_series_long.csv"
    )
