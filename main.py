"""
main.py

A single master script that:
 1) Generates buildings (if missing) => buildings_demo.csv
 2) Determines feeders => feeders.csv
 3) Creates lines => lines_demo.csv
 4) Assigns buildings => building_assignments.csv
 5) Builds final model => single-shot PF => sym_output.json / asym_output.json
 6) Generates time-series loads => time_series_loads.csv
 7) Runs time-series PF => time_series_wide.csv
"""

import os
import csv
import json
import random

# Pre-step modules (for generating or computing data)
from generate_buildings import generate_buildings_table
from determine_num_feeders import determine_feeders
from create_mv_lv_lines import create_mv_lv_lines
from assign_buildings import (
    load_buildings, load_lines,
    assign_buildings_to_lines, write_assignments_csv
)
from generate_time_series_loads import generate_time_series_loads

# Final-step modules
from build_network_model import build_network_model
from ascii_generator import generate_ascii_diagram
from json_generator import generate_json_data
from graph_visualizer import visualize_network
from power_flow_solver import solve_power_flow
from time_series_runner_long import run_time_series_pf_long


def get_building_ids_from_csv(buildings_csv):
    """
    Reads a 'buildings_demo.csv' that has columns like [building_id, lat, lon, ...].
    Returns a list of unique building_ids.
    Adjust if your CSV format differs.
    """
    if not os.path.exists(buildings_csv):
        return []
    ids = []
    with open(buildings_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # we assume each row has a 'building_id'
        for row in reader:
            if "building_id" in row:
                ids.append(row["building_id"])
    return list(set(ids))


def main():
    # ------------------- 1) Generate or Load Buildings -------------------
    buildings_csv = "buildings_demo.csv"
    if not os.path.exists("buildings_demo.csv"):
        print("[main] Generating building data (rich).")
        generate_buildings_table(num_buildings=12, output_path="buildings_demo.csv")
    else:
        print("[main] Using existing 'buildings_demo.csv'.")

    # ------------------- 2) Determine feeders -> feeders.csv ------------
    feeders_csv = "feeders.csv"
    if not os.path.exists(feeders_csv):
        print("[main] Determining feeders => feeders.csv")
        from determine_num_feeders import determine_feeders
        determine_feeders(
            buildings_csv=buildings_csv,
            feeders_csv=feeders_csv,
            buildings_per_feeder=5,
            placement_mode="random_in_bounding_box",
            lat_buffer=0.01,
            lon_buffer=0.01
        )
    else:
        print(f"[main] Found existing '{feeders_csv}' => using it.")

    # ------------------- 3) Create MV/LV lines -> lines_demo.csv --------
    lines_csv = "lines_demo.csv"
    if not os.path.exists(lines_csv):
        print("[main] Creating MV/LV lines => lines_demo.csv")
        substation_id = "MainSubstation"
        substation_lat = 40.150
        substation_lon = -3.550

        # read feeders from feeders.csv
        import csv
        feeder_list = []
        with open(feeders_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                feeder_list.append({
                    "feeder_id": row["feeder_id"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"])
                })

        create_mv_lv_lines(
            substation_id=substation_id,
            substation_lat=substation_lat,
            substation_lon=substation_lon,
            feeder_nodes=feeder_list,
            lv_branches_per_feeder=2,  # arbitrary
            output_format="csv",
            output_path=lines_csv
        )
    else:
        print(f"[main] Found existing '{lines_csv}' => using it.")

    # ------------------- 4) Assign buildings -> building_assignments.csv
    assignments_csv = "building_assignments.csv"
    if not os.path.exists(assignments_csv):
        print("[main] Assigning buildings => building_assignments.csv")
        # define node_locations for substation + feeders from the CSV
        substation_id = "MainSubstation"
        substation_lat = 40.150
        substation_lon = -3.550
        node_locations = { substation_id : (substation_lat, substation_lon) }

        # re-load feeder_list
        feeder_list = []
        with open(feeders_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                feeder_list.append(row)
        for fdr in feeder_list:
            fid = fdr["feeder_id"]
            node_locations[fid] = (float(fdr["lat"]), float(fdr["lon"]))

        # read lines
        lines_data = load_lines(lines_csv)
        # replicate logic from create_mv_lv_lines to set LV branches coords
        for ln in lines_data:
            if ln["voltage_level"] == "LV":
                feeder_id = ln["from_id"]
                lvbranch_id = ln["to_id"]
                if lvbranch_id not in node_locations:
                    parts = lvbranch_id.split("_LVbranch_")
                    if len(parts)==2:
                        try:
                            branch_i = int(parts[1])
                            f_lat, f_lon = node_locations[feeder_id]
                            offset_lat = f_lat + 0.001*branch_i
                            offset_lon = f_lon - 0.001*branch_i
                            node_locations[lvbranch_id] = (offset_lat, offset_lon)
                        except:
                            pass

        # load building data
        buildings_data = load_buildings(buildings_csv)
        assignments_list = assign_buildings_to_lines(
            buildings_data,
            lines_data,
            node_locations=node_locations,
            only_lv=True
        )
        write_assignments_csv(assignments_list, assignments_csv)
    else:
        print(f"[main] Found existing '{assignments_csv}' => using it.")

    # ------------------- 5) Build final model => single PF --------------
    print("[main] Building final model => single snapshot PF.")
    from build_network_model import build_network_model
    final_model = build_network_model(
        buildings_path=buildings_csv,
        lines_path=lines_csv,
        assignments_path=assignments_csv
    )
    # ASCII diagram
    from ascii_generator import generate_ascii_diagram
    ascii_str = generate_ascii_diagram(final_model)
    print("\n[main] ASCII Diagram:\n", ascii_str)

    # Convert to JSON => network_model.json
    from json_generator import generate_json_data
    network_json = generate_json_data(final_model)
    with open("network_model.json", "w", encoding="utf-8") as f:
        json.dump(network_json, f, indent=2)
    print("[main] Single-shot PF => 'network_model.json' created.")

    # visualize
    from graph_visualizer import visualize_network
    visualize_network(final_model, show_labels=True, title="Distribution Network Graph")

    # run dummy PF solver => sym_output.json, asym_output.json
    from power_flow_solver import solve_power_flow
    print("[main] Running dummy PF => sym_output.json, asym_output.json.")
    solve_power_flow(
        "network_model.json",
        params_json_path=None,
        sym_out_path="sym_output.json",
        asym_out_path="asym_output.json"
    )

    # ------------------- 6) Generate time-series loads => time_series_loads.csv
    ts_loads_csv = "time_series_loads.csv"
    if not os.path.exists(ts_loads_csv):
        print("[main] Generating time-series loads => time_series_loads.csv.")
        from generate_time_series_loads import generate_time_series_loads
        # get building IDs from buildings_demo.csv
        building_ids = get_building_ids_from_csv(buildings_csv)
        if not building_ids:
            print("[main] No building IDs found in building CSV. Skipping time-series loads.")
        else:
            generate_time_series_loads(
                building_ids=building_ids,
                categories=["heating","facility","generation","storage","total_electricity"],
                start_time="2025-01-01 00:00:00",
                end_time="2025-01-01 06:00:00",
                step_minutes=15,
                output_csv=ts_loads_csv
            )
    else:
        print(f"[main] Found existing '{ts_loads_csv}', using it.")

    # ------------------- 7) Time-series PF => time_series_wide.csv
    if os.path.exists("time_series_loads.csv"):
        run_time_series_pf_long(
            buildings_file="buildings_demo.csv",
            lines_file="lines_demo.csv",
            assignments_file="building_assignments.csv",
            ts_file="time_series_loads.csv",
            output_csv="time_series_long.csv"
        )
        print("[main] Time-series results => time_series_long.csv (LONG format).")
    else:
        print("[main] No time_series_loads.csv => skipping time-series PF.")

    print("[main] Full pipeline complete. Check outputs:\n",
          " - buildings_demo.csv\n",
          " - feeders.csv\n",
          " - lines_demo.csv\n",
          " - building_assignments.csv\n",
          " - network_model.json, sym_output.json, asym_output.json\n",
          " - time_series_loads.csv\n",
          " - time_series_wide.csv\n")


if __name__ == "__main__":
    main()
