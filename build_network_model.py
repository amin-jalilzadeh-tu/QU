"""
build_network_model.py

Creates a final 'model' dictionary for your distribution network, using:
  - buildings.csv/json
  - lines.csv/json
  - building_assignments.csv/json
  - node locations (dict or file)

and merges them into one data structure:

model = {
  "nodes": [...],
  "lines": [...],
  "links": [...],
  "loads": [...],
  "sources": [...],
  "shunts": []
}

You can then pass this model to ascii_generator.py, json_generator.py, or a time-series runner, etc.
"""

import csv
import json
import os
from data_lookup import DEFAULT_CONFIG, DEFAULT_LINE_PARAMS, DEFAULT_TRANSFORMER_PARAMS

def load_csv_or_json(filepath):
    """
    A utility to read either CSV or JSON into a list of dicts.
    """
    if filepath.lower().endswith(".csv"):
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        # assume JSON
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

def build_network_model(
    buildings_path="buildings.csv",
    lines_path="lines.csv",
    assignments_path="building_assignments.csv",
    node_locations=None,
    config=None
):
    """
    Builds a unified model dict for subsequent usage.

    :param buildings_path: CSV/JSON file with building data (id, lat, lon, peak_load, etc.)
    :param lines_path: CSV/JSON file with lines data (line_id, from_id, to_id, voltage_level, etc.)
    :param assignments_path: CSV/JSON file with building->line assignments
    :param node_locations: dict { node_id: (lat, lon) }, optional if lines_path doesn't store lat/lon
    :param config: dictionary of default config, from data_lookup.py or custom
    :return: a dictionary with structure:
       {
         "nodes": [],
         "lines": [],
         "links": [],
         "loads": [],
         "sources": [],
         "shunts": []
       }
    """
    if config is None:
        config = DEFAULT_CONFIG

    if node_locations is None:
        node_locations = {}

    # Initialize model
    model = {
        "nodes": [],
        "lines": [],
        "links": [],
        "loads": [],
        "sources": [],
        "shunts": []
    }
    current_id = 1

    def get_new_id():
        nonlocal current_id
        nid = current_id
        current_id += 1
        return nid

    # 1) Load the input files
    buildings_data = load_csv_or_json(buildings_path) if os.path.exists(buildings_path) else []
    lines_data = load_csv_or_json(lines_path) if os.path.exists(lines_path) else []
    assignments_data = load_csv_or_json(assignments_path) if os.path.exists(assignments_path) else []

    # 2) Create nodes from lines_data (unique from_id, to_id)
    node_ids = set()  # track which node "names" we've added

    for ln in lines_data:
        f_id = ln["from_id"]
        t_id = ln["to_id"]

        # from_id node
        if f_id not in node_ids:
            latlon = node_locations.get(f_id, (0, 0))
            node_model_id = get_new_id()
            model["nodes"].append({
                "id": node_model_id,
                "name": f_id,
                "u_rated": config.get("mv_voltage", 20000),
                "lat": latlon[0],
                "lon": latlon[1]
            })
            node_ids.add(f_id)

        # to_id node
        if t_id not in node_ids:
            latlon = node_locations.get(t_id, (0, 0))
            node_model_id = get_new_id()
            model["nodes"].append({
                "id": node_model_id,
                "name": t_id,
                "u_rated": config.get("mv_voltage", 20000),
                "lat": latlon[0],
                "lon": latlon[1]
            })
            node_ids.add(t_id)

    # 2a) Create a helper dict to map node "name" -> "model ID"
    name_to_model_id = {}
    for nd in model["nodes"]:
        name_to_model_id[nd["name"]] = nd["id"]

    # 3) Add lines to model["lines"]
    for ln in lines_data:
        line_id = get_new_id()
        from_node = name_to_model_id[ln["from_id"]]
        to_node = name_to_model_id[ln["to_id"]]
        voltage_level = ln.get("voltage_level", "MV")

        # default R/X based on voltage_level
        if voltage_level == "MV":
            r1 = DEFAULT_LINE_PARAMS["mv_r1"]
            x1 = DEFAULT_LINE_PARAMS["mv_x1"]
        else:
            # "LV"
            r1 = DEFAULT_LINE_PARAMS["lv_r1"]
            x1 = DEFAULT_LINE_PARAMS["lv_x1"]

        model["lines"].append({
            "id": line_id,
            "name": ln["line_id"],
            "from_node": from_node,
            "to_node": to_node,
            "r1": r1,
            "x1": x1,
            "i_n": DEFAULT_LINE_PARAMS["i_n"],
            "voltage_level": voltage_level
        })

    # 4) Create building nodes + loads
    #    p_kW is the default from CSV ("peak_load_kW") but in a time-series scenario,
    #    you can override these values later using 'update_building_loads' if you want.
    building_name_to_id = {}
    for b in buildings_data:
        bname = b["building_id"]
        latB = float(b.get("lat", 0))
        lonB = float(b.get("lon", 0))
        peak_load_kW = float(b.get("peak_load_kW", 0))

        # create node for building
        node_id = get_new_id()
        model["nodes"].append({
            "id": node_id,
            "name": bname,
            "u_rated": config.get("lv_voltage", 400),
            "lat": latB,
            "lon": lonB
        })
        building_name_to_id[bname] = node_id

        # add a load entry
        load_id = get_new_id()
        model["loads"].append({
            "id": load_id,
            "node": node_id,
            "status": 1,
            "type": 1,  # or a type code from config
            "p_kW": peak_load_kW
        })

    # 5) Use building_assignments to create "links"
    #    We'll link building -> line's "to_node" for simplicity.
    line_name_to_nodes = {}
    for ln in model["lines"]:
        line_name = ln["name"]  # e.g. "L0001"
        line_name_to_nodes[line_name] = (ln["from_node"], ln["to_node"])

    for asg in assignments_data:
        bname = asg["building_id"]  # e.g. "B0001"
        line_name = asg["line_id"]  # e.g. "L0001"
        dist_km = asg.get("distance_km", 0)

        if bname not in building_name_to_id:
            continue
        if line_name not in line_name_to_nodes:
            continue

        building_node_id = building_name_to_id[bname]
        from_node_id, to_node_id = line_name_to_nodes[line_name]

        link_id = get_new_id()
        model["links"].append({
            "id": link_id,
            "name": f"Link_{bname}_to_{line_name}",
            "from_node": building_node_id,
            "to_node": to_node_id,
            "dist_km": dist_km
        })

    # 6) Optionally add a "source" for the substation if known
    if "MainSubstation" in name_to_model_id:
        source_id = get_new_id()
        model["sources"].append({
            "id": source_id,
            "node": name_to_model_id["MainSubstation"],
            "status": 1,
            "u_ref": config.get("hv_slack_voltage_pu", 1.0)
        })

    return model


def update_building_loads(model, load_dict):
    """
    Allows overriding building loads in the model in memory.
    :param model: the final model dict (with "loads")
    :param load_dict: { building_name: p_kW_value, ... } or
                      { node_id: p_kW_value, ... }
    For example: { "B0001": 50.0, "B0002": 10.0 }

    If your model uses building_name == node name, you can match them.
    Otherwise, store a mapping from building_name->node ID and adapt.
    """
    # We'll assume building_name == model "node" name for loads
    # You might track them differently if needed.
    name_to_load_id = {}
    # build a quick map from node name -> load entry
    for ld in model["loads"]:
        node_id = ld["node"]
        # find the node in model["nodes"] to get name
        node_obj = next((n for n in model["nodes"] if n["id"] == node_id), None)
        if node_obj:
            b_name = node_obj["name"]
            name_to_load_id[b_name] = ld["id"]

    for bname, load_val in load_dict.items():
        # find load entry
        if bname in name_to_load_id:
            ld_id = name_to_load_id[bname]
            # update that load
            for ld in model["loads"]:
                if ld["id"] == ld_id:
                    ld["p_kW"] = load_val
                    break


if __name__ == "__main__":
    # Example usage
    model = build_network_model("buildings_demo.csv", "lines_demo.csv", "building_assignments.csv")
    print(f"Model has {len(model['nodes'])} nodes, {len(model['loads'])} loads.")

    # Suppose we want to override B0001's load to 45.0 kW
    new_loads = {"B0001": 45.0}
    update_building_loads(model, new_loads)

    # Now B0001's load is changed in memory
    for ld in model["loads"]:
        pass  # could print or verify
