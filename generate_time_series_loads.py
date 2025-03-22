"""
generate_time_series_loads.py

Generates a wide-format CSV of time-series loads for multiple buildings
and multiple "Energy" categories (including new "cooling" and "battery_charge").

Output format (wide CSV):

| building_id | Energy            | 00:00:00 | 00:15:00 | 00:30:00 | ...
| B0001       | heating           |    0     |   0      |   11     | ...
| B0001       | cooling           |   12     |  10      |   15     | ...
| B0001       | facility          |   121    |  121     |   0      | ...
| B0001       | generation        | ...      | ...      |   ...    | ...
| B0001       | battery_charge    | ...      | ...      |   ...    | ...
| B0001       | total_electricity |   ...    | ...      |   ...    | ...
| B0002       | heating           | ...
...

We optionally use 'buildings_info' to check if a building has_solar or has_battery.
If so, we can produce non-zero generation or battery_charge. Otherwise zero.

Usage:
  python generate_time_series_loads.py
  -> By default, it will create 'time_series_loads.csv' for some sample building IDs.
"""

import csv
import random
from datetime import datetime, timedelta

def generate_time_stamps(
    start_time_str="2025-01-01 00:00:00",
    end_time_str="2025-01-01 06:00:00",
    step_minutes=15
):
    """
    Generates a list of time-step labels (HH:MM:SS) from 'start_time_str' to
    'end_time_str' in increments of 'step_minutes'. The end_time is exclusive.
    """
    fmt = "%Y-%m-%d %H:%M:%S"
    start_dt = datetime.strptime(start_time_str, fmt)
    end_dt = datetime.strptime(end_time_str, fmt)

    time_stamps = []
    current = start_dt
    while current < end_dt:
        time_str = current.strftime("%H:%M:%S")  # e.g. "00:00:00"
        time_stamps.append(time_str)
        current += timedelta(minutes=step_minutes)

    return time_stamps

def generate_random_profile(num_steps, category, has_solar=False, has_battery=False):
    """
    Returns a list (length=num_steps) of random values appropriate for the category.
    We incorporate logic for heating, cooling, facility, generation, battery_charge, etc.
    If has_solar=False, generation stays 0. If has_battery=False, battery stays 0.
    """
    values = []

    if category == "heating":
        # e.g. ~0..30 kW
        for _ in range(num_steps):
            val = round(random.uniform(0, 30), 1)
            values.append(val)

    elif category == "cooling":
        # e.g. ~0..25 kW
        for _ in range(num_steps):
            val = round(random.uniform(0, 25), 1)
            values.append(val)

    elif category == "facility":
        # e.g. ~50..150 kW
        for _ in range(num_steps):
            val = round(random.uniform(50, 150), 1)
            values.append(val)

    elif category == "generation":
        # if building has solar, produce some non-zero generation
        if has_solar:
            for _ in range(num_steps):
                val = round(random.uniform(0, 10), 1)
                values.append(val)
        else:
            values = [0.0]*num_steps

    elif category == "battery_charge":
        # if building has battery, produce random +/- flows
        if has_battery:
            for _ in range(num_steps):
                # e.g. + means charging, - means discharging
                val = round(random.uniform(-5, 5), 1)
                values.append(val)
        else:
            values = [0.0]*num_steps

    elif category == "storage":
        # legacy example category, e.g. 0..20 kW
        for _ in range(num_steps):
            val = round(random.uniform(0, 20), 1)
            values.append(val)

    # We won't generate random values for "total_electricity" here,
    # because we'll compute that as facility + generation + storage.
    elif category == "total_electricity":
        # Just return placeholder zeros; we'll overwrite outside.
        values = [0.0]*num_steps

    else:
        # fallback
        values = [0.0]*num_steps

    return values

def generate_time_series_loads(
    building_ids,
    categories=("heating","cooling","facility","generation","battery_charge","storage","total_electricity"),
    start_time="2025-01-01 00:00:00",
    end_time="2025-01-01 06:00:00",
    step_minutes=15,
    output_csv="time_series_loads.csv",
    buildings_info=None
):
    """
    Creates a CSV with columns: [building_id, Energy, <time_1>, <time_2>, ...].
    Each building has one row per 'Energy' category.

    If 'buildings_info' is provided as a dict:
        buildings_info[bldg_id] = {
            "has_solar": bool,
            "has_battery": bool,
            ...
        }
    then we can produce generation or battery load only for those that have solar/battery.
    Otherwise, we default to random or 0 as needed.

    IMPORTANT: total_electricity = facility + generation + storage
    """
    print(f"[generate_time_series_loads] Generating time-series loads for {len(building_ids)} buildings.")

    # 1) Create time stamps
    time_stamps = generate_time_stamps(start_time, end_time, step_minutes)
    num_steps = len(time_stamps)

    # 2) Header
    header = ["building_id","Energy"] + time_stamps

    # 3) Prepare rows
    rows = []

    for b_id in building_ids:
        # Determine if building has solar/battery
        has_solar = False
        has_battery = False
        if buildings_info and b_id in buildings_info:
            has_solar = bool(buildings_info[b_id].get("has_solar", False))
            has_battery = bool(buildings_info[b_id].get("has_battery", False))

        # First, generate random values for all categories except total_electricity.
        # We'll store them in a dict so we can compute total_electricity afterward.
        cat_profiles = {}

        for cat in categories:
            if cat != "total_electricity":
                cat_profiles[cat] = generate_random_profile(num_steps, cat, has_solar, has_battery)

        # Compute total_electricity as facility + generation + storage
        # (only if these categories exist in cat_profiles)
        total_vals = [0.0]*num_steps
        if "facility" in cat_profiles and "generation" in cat_profiles and "storage" in cat_profiles:
            for i in range(num_steps):
                total_vals[i] = (cat_profiles["facility"][i]
                                 + cat_profiles["generation"][i]
                                 + cat_profiles["storage"][i])
        else:
            # If any of them is missing, we just leave total_electricity as all zeros
            pass

        # Now store that into cat_profiles
        cat_profiles["total_electricity"] = total_vals

        # Finally, write one row per category
        for cat in categories:
            row = [b_id, cat] + cat_profiles[cat]
            rows.append(row)

    # 4) Write CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"[generate_time_series_loads] Created '{output_csv}' with {len(rows)} rows.")

if __name__ == "__main__":
    # Example usage if run standalone:
    test_building_ids = ["B0001","B0002","B0003"]
    # Suppose B0001 has solar, B0002 has battery, B0003 has neither
    bldg_info_example = {
        "B0001": {"has_solar": True,  "has_battery": False},
        "B0002": {"has_solar": False, "has_battery": True},
        "B0003": {"has_solar": False, "has_battery": False}
    }

    generate_time_series_loads(
        building_ids=test_building_ids,
        categories=["heating","cooling","facility","generation","battery_charge","storage","total_electricity"],
        start_time="2025-01-01 00:00:00",
        end_time="2025-01-01 06:00:00",
        step_minutes=15,
        output_csv="time_series_loads.csv",
        buildings_info=bldg_info_example
    )
