"""
determine_num_feeders.py

Calculates how many feeders we want and writes a CSV with each feeder's ID and lat/lon.

Steps:
  1. Read buildings CSV to determine number of buildings (or total load).
  2. Decide how many feeders by a simple ratio or load-based approach.
  3. Place feeders at random or user-defined lat/lon within the bounding box of the buildings.
  4. Write feeders.csv with columns: feeder_id, lat, lon
"""

import csv
import math
import random
import os

def get_num_feeders_simple(num_buildings, buildings_per_feeder=50):
    """
    Returns how many feeders if each feeder can handle up to 'buildings_per_feeder'.
    Example: 120 buildings, 50 per feeder -> 3 feeders.
    """
    feeders = math.ceil(num_buildings / buildings_per_feeder)
    return feeders

def get_num_feeders_by_load(total_load_kW, feeder_capacity_kW=2000):
    """
    Returns how many feeders if each feeder can handle up to 'feeder_capacity_kW'.
    Example: total_load=5500 kW, capacity=2000 kW -> 3 feeders
    """
    return math.ceil(total_load_kW / feeder_capacity_kW)

def determine_feeders(
    buildings_csv="buildings.csv",
    feeders_csv="feeders.csv",
    buildings_per_feeder=50,
    placement_mode="random_in_bounding_box",
    lat_buffer=0.01,
    lon_buffer=0.01
):
    """
    1) Reads 'buildings_csv' to find how many buildings (and optionally min/max lat/lon).
    2) Calculates how many feeders are needed (simple ratio).
    3) For each feeder, picks lat/lon either randomly in the bounding box
       or uses a simple pattern. 
    4) Writes 'feeders_csv' with columns: feeder_id, lat, lon

    :param buildings_csv: path to buildings data (must have lat, lon columns)
    :param feeders_csv: output CSV with feeder_id, lat, lon
    :param buildings_per_feeder: ratio for feeder count
    :param placement_mode: "random_in_bounding_box" or "center" or any custom approach
    :param lat_buffer, lon_buffer: extra padding around building bounding box
    """
    # 1) Load building data
    if not os.path.exists(buildings_csv):
        raise FileNotFoundError(f"Cannot find buildings file: {buildings_csv}")

    with open(buildings_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        buildings = list(reader)

    num_buildings = len(buildings)
    if num_buildings < 1:
        raise ValueError("No buildings found in the CSV. Cannot determine feeders.")

    # gather lat/lon min/max
    lat_values = []
    lon_values = []
    total_load = 0.0
    for b in buildings:
        lat_values.append(float(b["lat"]))
        lon_values.append(float(b["lon"]))
        # optionally gather load if you prefer a load-based approach
        if "peak_load_kW" in b:
            total_load += float(b["peak_load_kW"])

    min_lat, max_lat = min(lat_values), max(lat_values)
    min_lon, max_lon = min(lon_values), max(lon_values)

    # 2) Decide feeder count
    feeders_needed = get_num_feeders_simple(num_buildings, buildings_per_feeder)
    # (Or we could do get_num_feeders_by_load(total_load, feeder_capacity_kW=2000))

    # 3) Place feeders
    # We'll store them in a list of dict: { "feeder_id": ..., "lat": ..., "lon": ... }
    feeder_list = []
    for i in range(feeders_needed):
        fid = f"Feeder{i+1}"
        if placement_mode == "random_in_bounding_box":
            # pick random lat/lon in [min_lat - lat_buffer, max_lat + lat_buffer], etc.
            feeder_lat = random.uniform(min_lat - lat_buffer, max_lat + lat_buffer)
            feeder_lon = random.uniform(min_lon - lon_buffer, max_lon + lon_buffer)
        else:
            # fallback: center or other approach
            # e.g., place them evenly spaced across bounding box
            frac = (i+1)/(feeders_needed+1)  # fraction in [1/(N+1), ..., N/(N+1)]
            feeder_lat = (1-frac)*(min_lat - lat_buffer) + frac*(max_lat + lat_buffer)
            feeder_lon = (1-frac)*(min_lon - lon_buffer) + frac*(max_lon + lon_buffer)

        feeder_list.append({
            "feeder_id": fid,
            "lat": round(feeder_lat, 6),
            "lon": round(feeder_lon, 6)
        })

    # 4) Write feeders.csv
    with open(feeders_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["feeder_id", "lat", "lon"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(feeder_list)

    print(f"[determine_num_feeders] Found {num_buildings} buildings, placed {feeders_needed} feeders.")
    print(f"  bounding box: lat=[{min_lat:.4f}, {max_lat:.4f}], lon=[{min_lon:.4f}, {max_lon:.4f}]")
    print(f"  feeders saved to '{feeders_csv}'")

    return feeder_list


if __name__ == "__main__":
    # Example usage:
    # 1) Suppose we have a buildings_demo.csv with lat/lon columns
    # 2) We want 1 feeder per 5 buildings
    # 3) We'll place feeders randomly in the bounding box
    buildings_file = "buildings_demo.csv"
    feeders_file = "feeders.csv"
    determine_feeders(
        buildings_csv=buildings_file,
        feeders_csv=feeders_file,
        buildings_per_feeder=5,
        placement_mode="random_in_bounding_box",
        lat_buffer=0.01,
        lon_buffer=0.01
    )
