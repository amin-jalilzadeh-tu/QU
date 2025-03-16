"""
create_mv_lv_lines.py

Creates MV and LV lines for a distribution network, given:
  1) A substation node with lat/lon
  2) A list of feeder nodes, each with lat/lon
  3) (Optionally) we can create a few "LV branches" off each feeder node,
     but not assigned to buildings. This is just a topology skeleton.

Outputs lines in CSV or JSON with fields:
   line_id, from_id, to_id, length_km, voltage_level
"""

import csv
import json
import math

def distance_lat_lon(lat1, lon1, lat2, lon2):
    """
    Approximate distance in km using the haversine formula.
    """
    R = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def create_mv_lv_lines(
    substation_id="Substation",
    substation_lat=40.1000,
    substation_lon=-3.5000,
    feeder_nodes=None,
    lv_branches_per_feeder=0,
    output_format="csv",
    output_path="lines.csv"
):
    """
    :param substation_id: name/id for the substation node
    :param substation_lat, substation_lon: substation location
    :param feeder_nodes: list of dicts:
        [
          {
            "feeder_id": "Feeder1",
            "lat": 40.105,
            "lon": -3.505,
          },
          {
            "feeder_id": "Feeder2",
            "lat": 40.110,
            "lon": -3.520,
          },
          ...
        ]
    :param lv_branches_per_feeder: how many LV lines to create from each feeder node
        (purely to illustrate an LV topology skeleton, not assigned to buildings).
    :param output_format: "csv" or "json"
    :param output_path: file path to write lines
    :return: a list of line dicts with fields
        {
          "line_id": ...,
          "from_id": ...,
          "to_id": ...,
          "length_km": ...,
          "voltage_level": "MV" or "LV"
        }
    """
    if feeder_nodes is None:
        feeder_nodes = []

    lines_list = []
    line_count = 1

    # 1) For each feeder node, create an MV line from the substation to that node
    for feeder in feeder_nodes:
        f_id = feeder["feeder_id"]
        f_lat = feeder["lat"]
        f_lon = feeder["lon"]

        dist_km = distance_lat_lon(substation_lat, substation_lon, f_lat, f_lon)
        line_id = f"L{line_count:04d}"
        lines_list.append({
            "line_id": line_id,
            "from_id": substation_id,
            "to_id": f_id,
            "length_km": round(dist_km, 4),
            "voltage_level": "MV"
        })
        line_count += 1

        # 2) Optionally create some LV lines to represent branches from the feeder node
        for branch_i in range(lv_branches_per_feeder):
            # We'll create a simple pseudo-lv node at a random small offset
            # In reality, you'd define actual coordinates or further branching logic
            offset_lat = f_lat + 0.001 * (branch_i + 1)  # purely demonstration
            offset_lon = f_lon - 0.001 * (branch_i + 1)
            dist_lv = distance_lat_lon(f_lat, f_lon, offset_lat, offset_lon)

            lv_line_id = f"L{line_count:04d}"
            lv_node_id = f"{f_id}_LVbranch_{branch_i+1}"
            lines_list.append({
                "line_id": lv_line_id,
                "from_id": f_id,
                "to_id": lv_node_id,
                "length_km": round(dist_lv, 4),
                "voltage_level": "LV"
            })
            line_count += 1

    # 3) Write output
    if output_format.lower() == "csv":
        fieldnames = ["line_id", "from_id", "to_id", "length_km", "voltage_level"]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(lines_list)
        print(f"[create_mv_lv_lines] Created lines CSV: {output_path}")
    elif output_format.lower() == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lines_list, f, indent=2)
        print(f"[create_mv_lv_lines] Created lines JSON: {output_path}")
    else:
        raise ValueError("output_format must be 'csv' or 'json'.")

    return lines_list

if __name__ == "__main__":
    """
    Example usage:
      Suppose we have 2 feeders, we define their lat/lon here.
      We'll create a substation at (40.10, -3.50).
      We'll generate an MV line from substation to each feeder.
      Then for each feeder, we create 2 LV branches as a demonstration.
    """
    feeder_list = [
        {"feeder_id": "Feeder1", "lat": 40.105, "lon": -3.505},
        {"feeder_id": "Feeder2", "lat": 40.110, "lon": -3.520}
    ]
    lines = create_mv_lv_lines(
        substation_id="MainSubstation",
        substation_lat=40.1000,
        substation_lon=-3.5000,
        feeder_nodes=feeder_list,
        lv_branches_per_feeder=2,  # purely for demonstration
        output_format="csv",
        output_path="lines_demo.csv"
    )
    print(f"Created {len(lines)} lines in lines_demo.csv.")
