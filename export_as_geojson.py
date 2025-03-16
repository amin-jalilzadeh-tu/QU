"""
export_as_geojson.py

Creates GeoJSON files from:
  1) buildings_demo.csv  -> buildings_demo.geojson
  2) lines_demo.csv      -> lines_demo.geojson
  3) building_assignments.csv -> assignments_demo.geojson

We assume:
  - buildings_demo.csv has columns [building_id, lat, lon, building_type, peak_load_kW, ...]
  - lines_demo.csv has columns [line_id, from_id, to_id, length_km, voltage_level, ...]
  - building_assignments.csv has columns [building_id, line_id, distance_km, ...]
  - node_locations: a dict { node_id: (lat, lon) } for from_id/to_id references in lines_demo.csv

Dependencies: None beyond Python stdlib. We'll produce standard GeoJSON FeatureCollections.
"""

import csv
import json
import math
import os

def load_csv_as_list_of_dict(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def export_buildings_geojson(buildings_csv, output_geojson="buildings_demo.geojson"):
    """
    Reads buildings CSV and creates a GeoJSON FeatureCollection of Points.
    Each Feature has geometry = Point(longitude, latitude)
    and properties for building_id, building_type, peak_load_kW, etc.
    """
    if not os.path.exists(buildings_csv):
        print(f"[export_buildings_geojson] File not found: {buildings_csv}")
        return

    buildings = load_csv_as_list_of_dict(buildings_csv)

    features = []
    for b in buildings:
        b_id = b.get("building_id", "Unknown")
        lat = float(b.get("lat", 0))
        lon = float(b.get("lon", 0))

        # Build the GeoJSON feature
        feat = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]  # GeoJSON => [longitude, latitude]
            },
            "properties": {
                "building_id": b_id,
                # Include other columns as well
                "building_type": b.get("building_type", ""),
                "peak_load_kW": b.get("peak_load_kW", "")
                # Add more if you have them
            }
        }
        features.append(feat)

    fc = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)
    print(f"[export_buildings_geojson] Created '{output_geojson}' with {len(features)} features.")


def export_lines_geojson(lines_csv, node_locations, output_geojson="lines_demo.geojson"):
    """
    Converts lines_demo.csv to a GeoJSON FeatureCollection of LineStrings,
    using 'node_locations' to find lat/lon for from_id and to_id.

    lines_csv columns: [line_id, from_id, to_id, length_km, voltage_level, ...]
    node_locations: dict { "Feeder1": (lat, lon), ... }
    """
    if not os.path.exists(lines_csv):
        print(f"[export_lines_geojson] File not found: {lines_csv}")
        return

    lines = load_csv_as_list_of_dict(lines_csv)

    features = []
    missing_count = 0

    for ln in lines:
        line_id = ln.get("line_id", "Unknown")
        from_id = ln.get("from_id", "")
        to_id = ln.get("to_id", "")
        dist_km = ln.get("length_km", "")
        voltage_level = ln.get("voltage_level", "")

        # Get lat/lon for from_id and to_id
        if from_id not in node_locations or to_id not in node_locations:
            missing_count += 1
            continue

        lat1, lon1 = node_locations[from_id]
        lat2, lon2 = node_locations[to_id]

        feat = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [lon1, lat1],
                    [lon2, lat2]
                ]
            },
            "properties": {
                "line_id": line_id,
                "from_id": from_id,
                "to_id": to_id,
                "length_km": dist_km,
                "voltage_level": voltage_level
            }
        }
        features.append(feat)

    fc = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)
    print(f"[export_lines_geojson] Created '{output_geojson}' with {len(features)} line features.")
    if missing_count > 0:
        print(f"[export_lines_geojson] WARNING: {missing_count} lines missing node_locations.")


def export_building_assignments_geojson(buildings_csv, assignments_csv,
                                        output_geojson="assignments_demo.geojson"):
    """
    Produces a FeatureCollection of building points, each with a property
    for the assigned line and distance. Essentially merges building info with assignment info.

    geometry = Point at building lat/lon
    properties = { building_id, assigned_line_id, distance_km, ... }

    Note: This does NOT create line geometry from building to assigned line; it's just a point
    with properties. If you want a line from building->line, you'd do a small linestring.
    """
    if not os.path.exists(buildings_csv):
        print(f"[export_building_assignments_geojson] File not found: {buildings_csv}")
        return
    if not os.path.exists(assignments_csv):
        print(f"[export_building_assignments_geojson] File not found: {assignments_csv}")
        return

    buildings = load_csv_as_list_of_dict(buildings_csv)
    assignments = load_csv_as_list_of_dict(assignments_csv)

    # Build a dict to quickly get lat/lon from building_id
    bldg_coords = {}
    bldg_extra = {}
    for b in buildings:
        b_id = b.get("building_id", "")
        lat = float(b.get("lat", 0))
        lon = float(b.get("lon", 0))
        bldg_coords[b_id] = (lat, lon)
        bldg_extra[b_id] = b  # store entire row if needed

    features = []
    missing_count = 0

    for asg in assignments:
        b_id = asg.get("building_id", "")
        line_id = asg.get("line_id", "")
        dist_km = asg.get("distance_km", "")

        if b_id not in bldg_coords:
            missing_count += 1
            continue

        latB, lonB = bldg_coords[b_id]

        # Build the point feature
        props = {
            "building_id": b_id,
            "assigned_line_id": line_id,
            "distance_km": dist_km
        }
        # Optionally, also merge building_type, peak_load_kW, etc.
        if b_id in bldg_extra:
            props["building_type"] = bldg_extra[b_id].get("building_type", "")
            props["peak_load_kW"] = bldg_extra[b_id].get("peak_load_kW", "")

        feat = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lonB, latB]
            },
            "properties": props
        }
        features.append(feat)

    fc = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)
    print(f"[export_building_assignments_geojson] Created '{output_geojson}' with {len(features)} features.")
    if missing_count > 0:
        print(f"[export_building_assignments_geojson] WARNING: {missing_count} buildings not found in CSV.")


if __name__ == "__main__":
    """
    Example usage:
      1) We'll define a node_locations for lines (substation, feeders, etc.)
      2) We'll export lines_demo.csv -> lines_demo.geojson
      3) We'll export buildings_demo.csv -> buildings_demo.geojson
      4) We'll export building_assignments.csv -> assignments_demo.geojson
    """
    # 1) Suppose we have the same node_locations as in main.py
    node_locations = {
        "MainSubstation": (40.150, -3.550),
        "Feeder1": (40.160, -3.555),
        "Feeder1_LVbranch_1": (40.161, -3.556),
        "Feeder1_LVbranch_2": (40.162, -3.557),
        "Feeder2": (40.170, -3.560),
        "Feeder2_LVbranch_1": (40.171, -3.561),
        "Feeder2_LVbranch_2": (40.172, -3.562)
    }

    # 2) Export lines
    export_lines_geojson("lines_demo.csv", node_locations, "lines_demo.geojson")

    # 3) Export buildings
    export_buildings_geojson("buildings_demo.csv", "buildings_demo.geojson")

    # 4) Export assignments
    export_building_assignments_geojson("buildings_demo.csv", "building_assignments.csv",
                                        "assignments_demo.geojson")
