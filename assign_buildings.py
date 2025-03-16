"""
assign_buildings.py

Assigns each building to the nearest LV line by geospatial proximity.
We need:
  - A buildings file (CSV or JSON) with columns "building_id", "lat", "lon", ...
  - A lines file (CSV or JSON) with "line_id", "from_id", "to_id", "voltage_level"...
  - A node_locations dictionary that gives lat/lon for each node_id (substation, feeder, etc.),
    so we can reconstruct line segments.

We output a CSV (or JSON) that lists each building's assigned line and the distance.
"""

import csv
import json
import math

def load_buildings(buildings_path):
    """
    Loads building data from a CSV or JSON, returns list of dicts:
      [ { "building_id": ..., "lat": ..., "lon": ..., ...}, ...]
    """
    if buildings_path.lower().endswith(".csv"):
        with open(buildings_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        # assume JSON
        with open(buildings_path, "r", encoding="utf-8") as f:
            return json.load(f)

def load_lines(lines_path):
    """
    Loads line data from a CSV or JSON, returns list of dicts:
      [ { "line_id": ..., "from_id": ..., "to_id": ..., "voltage_level": ..., ...}, ...]
    """
    if lines_path.lower().endswith(".csv"):
        with open(lines_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        # assume JSON
        with open(lines_path, "r", encoding="utf-8") as f:
            return json.load(f)

def distance_lat_lon(lat1, lon1, lat2, lon2):
    """
    Returns approximate distance in km (haversine).
    """
    R = 6371.0
    lat1_r = math.radians(float(lat1))
    lon1_r = math.radians(float(lon1))
    lat2_r = math.radians(float(lat2))
    lon2_r = math.radians(float(lon2))

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (math.sin(dlat/2)**2
         + math.cos(lat1_r)*math.cos(lat2_r)*math.sin(dlon/2)**2)
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

def point_to_line_distance_km(px, py, x1, y1, x2, y2):
    """
    Computes the shortest distance from point P(px, py) to
    the line segment (x1, y1) -> (x2, y2), in km.
    1) Convert lat/lon to approximate local XY if the region is small,
       OR do an iterative approach with haversine for partial steps.
    2) For simplicity, we can do a rough "flat" approach if lat/lon bounding box is small.

    Below is a naive "flat earth" approach for short distances:
      - Convert lat/lon to approximate meters using a reference lat.
      - Do standard 2D point-line-segment distance.
      - Return result in km.

    If your region is large, consider a proper geodesic library or a simpler approach:
      - compare distance(P->A), distance(P->B), or find closest fraction along line.

    We'll do a simple approach that is acceptable for small bounding boxes.
    """

    # 1) Convert lat/lon to a rough meter grid
    # Choose a reference latitude for scale
    ref_lat = (y1 + y2) / 2
    # approx degrees to meters
    m_per_deg_lat = 111132.954
    m_per_deg_lon = 111132.954 * math.cos(math.radians(ref_lat))

    def latlon_to_xy(lat, lon):
        x = (lon - (-180)) * m_per_deg_lon  # naive shift, or do a local shift
        y = (lat - 0) * m_per_deg_lat
        return x, y

    # But let's do a simpler shift so we don't blow up the numbers
    # We'll shift relative to (ref_lat, mid of x1,x2).
    mid_lon = (x1 + x2)/2
    lat_shift = ref_lat
    lon_shift = mid_lon

    def local_xy(lat, lon):
        delta_lat = lat - lat_shift
        delta_lon = lon - lon_shift
        x_m = delta_lon * m_per_deg_lon
        y_m = delta_lat * m_per_deg_lat
        return x_m, y_m

    # Convert the line endpoints and point
    X1, Y1 = local_xy(y1, x1)
    X2, Y2 = local_xy(y2, x2)
    PX, PY = local_xy(py, px)

    # 2) Compute standard 2D point-line distance
    # Param of projection
    dx = X2 - X1
    dy = Y2 - Y1
    if dx == 0 and dy == 0:
        # from->to are same point
        dist_m = math.dist((PX, PY), (X1, Y1))
    else:
        t = ((PX - X1)*dx + (PY - Y1)*dy) / (dx*dx + dy*dy)
        if t < 0:
            # closest to segment start
            dist_m = math.dist((PX, PY), (X1, Y1))
        elif t > 1:
            # closest to segment end
            dist_m = math.dist((PX, PY), (X2, Y2))
        else:
            # projection in the middle
            projX = X1 + t*dx
            projY = Y1 + t*dy
            dist_m = math.dist((PX, PY), (projX, projY))

    dist_km = dist_m / 1000.0
    return dist_km

def assign_buildings_to_lines(buildings, lines, node_locations, only_lv=True):
    """
    :param buildings: list of dicts with {building_id, lat, lon, ...}
    :param lines: list of dicts with {line_id, from_id, to_id, voltage_level, ...}
    :param node_locations: dict { node_id: (lat, lon) }, for from_id/to_id
    :param only_lv: if True, we only consider lines where voltage_level == "LV"
    :return: list of assignments: [ { "building_id":..., "line_id":..., "distance_km":... }, ...]
    """
    assignments = []
    for b in buildings:
        b_id = b["building_id"]
        latB = float(b["lat"])
        lonB = float(b["lon"])

        best_line = None
        best_dist = 1e9

        for ln in lines:
            if only_lv and ln.get("voltage_level") != "LV":
                continue

            # get from_id lat/lon
            f_id = ln["from_id"]
            t_id = ln["to_id"]
            if f_id not in node_locations or t_id not in node_locations:
                # cannot compute geometry if we lack node coords
                continue

            lat1, lon1 = node_locations[f_id]
            lat2, lon2 = node_locations[t_id]

            # compute dist
            dist_km = point_to_line_distance_km(lonB, latB, lon1, lat1, lon2, lat2)
            # note the param order:
            #  point_to_line_distance_km(px, py, x1, y1, x2, y2)
            #  we used px=lonB, py=latB, x1=lon1, y1=lat1, etc.
            #  because we wrote it that way above.

            if dist_km < best_dist:
                best_dist = dist_km
                best_line = ln["line_id"]

        if best_line:
            assignments.append({
                "building_id": b_id,
                "line_id": best_line,
                "distance_km": round(best_dist, 5)
            })
        else:
            # no line found? Possibly store a negative or None
            assignments.append({
                "building_id": b_id,
                "line_id": None,
                "distance_km": None
            })

    return assignments

def write_assignments_csv(assignments, output_path="building_assignments.csv"):
    """
    Writes the assignment list to a CSV.
    """
    fieldnames = ["building_id", "line_id", "distance_km"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)

    print(f"[assign_buildings_to_lines] Wrote {len(assignments)} assignments to {output_path}")

if __name__ == "__main__":
    """
    Example usage:
      1) We have 'buildings_demo.csv' (with building_id, lat, lon).
      2) We have 'lines_demo.csv' (with line_id, from_id, to_id, voltage_level).
      3) We have a node_locations dict for "MainSubstation", "Feeder1", "Feeder2", 
         or any LV branch nodes used by lines.
    """
    # 1) Load building file
    buildings_file = "buildings_demo.csv"  # must contain lat/lon columns
    buildings_data = load_buildings(buildings_file)

    # 2) Load line file
    lines_file = "lines_demo.csv"
    lines_data = load_lines(lines_file)

    # 3) Suppose we keep node coords in a dictionary or from a file
    #    This must match "from_id"/"to_id" in lines_demo.csv
    node_locations = {
        "MainSubstation": (40.1000, -3.5000),
        "Feeder1": (40.1050, -3.5050),
        "Feeder2": (40.1100, -3.5200),
        "Feeder1_LVbranch_1": (40.1060, -3.5060),
        "Feeder1_LVbranch_2": (40.1070, -3.5070),
        "Feeder2_LVbranch_1": (40.1110, -3.5210),
        "Feeder2_LVbranch_2": (40.1120, -3.5220)
        # etc.
    }

    # 4) Assign buildings to nearest LV line
    assignments_list = assign_buildings_to_lines(buildings_data, lines_data, node_locations, only_lv=True)
    # 5) Write results
    write_assignments_csv(assignments_list, "building_assignments.csv")
