"""
generate_buildings.py

Creates a 'buildings_demo.csv' with richer data:
 - building_id
 - building_function
 - building_type
 - year_range
 - infiltration rates, occupant density, etc.
 - lat, lon
 - peak_load_kW
 - has_solar, solar_capacity_kWp
 - has_battery, battery_capacity_kWh, battery_power_kW

Usage:
  python generate_buildings.py
  -> generates a default 'buildings_demo.csv' with random data.
"""

import csv
import random

def weighted_choice(choices):
    """
    Given a list of (item, weight) tuples, randomly select an item
    according to the specified probabilities.
    """
    total = sum(weight for item, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for item, weight in choices:
        if upto + weight >= r:
            return item
        upto += weight
    return choices[-1][0]  # fallback

def generate_rich_building_data(num_buildings=20):
    """
    Generate synthetic building data with infiltration, occupant density,
    building function, building type, etc. Also includes solar/battery info.
    Returns a list of dicts, each representing one building row.
    """

    building_function_choices = [
        ("residential", 0.60),
        ("non_residential", 0.40),
    ]
    residential_type_choices = [
        ("Two-and-a-half-story House", 0.3),
        ("Corner House", 0.3),
        ("Apartment", 0.4),
    ]
    nonres_type_choices = [
        ("Office Function", 0.5),
        ("Meeting Function", 0.3),
        ("Education Function", 0.2),
    ]
    year_range_choices = [
        ("< 1945", 0.1),
        ("1945 - 1964", 0.1),
        ("1965 - 1974", 0.1),
        ("1975 - 1991", 0.2),
        ("1992 - 2005", 0.3),
        ("2006 - 2014", 0.1),
        ("2015 and later", 0.1)
    ]

    def random_infiltration_rate(build_func):
        if build_func == "residential":
            return (round(random.uniform(0.5, 0.8), 2),
                    round(random.uniform(0.8, 1.0), 2))
        else:
            return (round(random.uniform(0.7, 1.0), 2),
                    round(random.uniform(1.0, 1.3), 2))

    def random_occupant_density(build_func):
        # occupant_density_m2_per_person
        if build_func == "residential":
            min_val = random.choice([10, 12, 15])
            max_val = min_val + random.randint(5, 10)
            return (min_val, max_val)
        else:
            min_val = random.choice([5, 8, 10])
            max_val = min_val + random.randint(3, 10)
            return (min_val, max_val)

    def random_dhw_usage(build_func):
        # liters_per_person_per_day
        if build_func == "residential":
            return (random.randint(30, 50), random.randint(50, 70))
        else:
            # Non-res might have minimal usage
            return (random.randint(0, 5), random.randint(5, 15))

    def random_heating_setpoint():
        # e.g. day_min ~ [19..20], day_max = day_min+1
        day_min = round(random.uniform(19.0, 20.0), 1)
        day_max = round(day_min + 1.0, 1)
        return (day_min, day_max)

    def random_cooling_setpoint():
        # e.g. day_min ~ [23.5..24.5], day_max=day_min+1
        day_min = round(random.uniform(23.5, 24.5), 1)
        day_max = round(day_min + 1.0, 1)
        return (day_min, day_max)

    def random_lpd(build_func):
        if build_func == "residential":
            return (round(random.uniform(3,5),1),
                    round(random.uniform(5,7),1))
        else:
            return (round(random.uniform(8,12),1),
                    round(random.uniform(12,16),1))

    buildings = []
    for i in range(num_buildings):
        b_id = f"B{i+1:04d}"  # B0001, B0002,...

        build_func = weighted_choice(building_function_choices)
        if build_func == "residential":
            b_type = weighted_choice(residential_type_choices)
        else:
            b_type = weighted_choice(nonres_type_choices)

        year_range = weighted_choice(year_range_choices)
        inf_min, inf_max = random_infiltration_rate(build_func)
        occd_min, occd_max = random_occupant_density(build_func)
        dhw_min, dhw_max = random_dhw_usage(build_func)
        h_min, h_max = random_heating_setpoint()
        c_min, c_max = random_cooling_setpoint()
        lpd_min, lpd_max = random_lpd(build_func)

        area_val = random.randint(30,300)
        perimeter_val = random.randint(20,100)
        height_val = random.uniform(3.0,12.0)

        # random lat/lon for demonstration
        lat_val = round(random.uniform(40.10, 40.20),5)
        lon_val = round(random.uniform(-3.60, -3.50),5)

        # Optional peak_load_kW
        peak_load = round(random.uniform(5, 200), 1)

        # ------------------ NEW: solar & battery info ------------------
        # Decide if building has solar
        has_solar = (random.random() < 0.4)  # 40% chance
        solar_capacity_kWp = 0.0
        if has_solar:
            solar_capacity_kWp = round(random.uniform(2.0, 15.0), 1)

        # Decide if building has battery
        has_battery = (random.random() < 0.3)  # 30% chance
        battery_capacity_kWh = 0.0
        battery_power_kW = 0.0
        if has_battery:
            battery_capacity_kWh = round(random.uniform(5.0, 30.0), 1)
            battery_power_kW = round(random.uniform(3.0, 10.0), 1)

        row = {
            "building_id": b_id,
            "lat": lat_val,
            "lon": lon_val,
            "peak_load_kW": peak_load,

            "ogc_fid": random.randint(1000000,9999999),
            "pand_id": f"{random.uniform(1e13,2e13):.2E}",
            "label": random.choice(["A","B","C","D"]),
            "gem_hoogte": random.randint(2,8),
            "gem_bouwlagen": random.randint(1,4),
            "b3_dak_type": random.choice(["flat","pitched","multiple horizontal"]),
            "b3_opp_dak_plat": random.randint(20,100),
            "b3_opp_dak_schuin": random.randint(10,60),
            "postcode": f"{random.randint(1000,9999)}{random.choice(['AB','CD','EF','GH','XZ'])}",
            "area": area_val,
            "perimeter": perimeter_val,
            "height": round(height_val,1),
            "bouwjaar": random.randint(1930,2023),
            "age_range": year_range,
            "average_wwr": round(random.uniform(0.1,0.4),2),
            "building_function": build_func,
            "building_type": b_type,

            # infiltration, occupant density, etc.
            "infiltration_rate_min": inf_min,
            "infiltration_rate_max": inf_max,
            "occupant_density_min": occd_min,
            "occupant_density_max": occd_max,
            "dhw_liters_per_person_day_min": dhw_min,
            "dhw_liters_per_person_day_max": dhw_max,
            "heating_day_setpoint_min": h_min,
            "heating_day_setpoint_max": h_max,
            "cooling_day_setpoint_min": c_min,
            "cooling_day_setpoint_max": c_max,
            "lighting_power_density_wm2_min": lpd_min,
            "lighting_power_density_wm2_max": lpd_max,

            "fan_power_w": random.randint(30,200),
            "hrv_efficiency": 0.75,

            # NEW columns for solar/battery
            "has_solar": has_solar,
            "solar_capacity_kWp": solar_capacity_kWp,
            "has_battery": has_battery,
            "battery_capacity_kWh": battery_capacity_kWh,
            "battery_power_kW": battery_power_kW
        }
        buildings.append(row)

    return buildings

def write_buildings_to_csv(buildings, csv_filename="buildings_demo.csv"):
    """
    Writes the generated building data to CSV.
    """
    if not buildings:
        print("[generate_buildings] No buildings to write.")
        return

    fieldnames = list(buildings[0].keys())
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(buildings)

    print(f"[generate_buildings] Wrote {len(buildings)} buildings => {csv_filename}")

def generate_buildings_table(
    num_buildings=20,
    output_format="csv",
    output_path="buildings_demo.csv",
    lat_range=(40.10,40.20),
    lon_range=(-3.60,-3.50),
    demand_range=(5,60),
    building_type_distribution=None
):
    """
    Replaces or overrides the old function. 
    Now we call generate_rich_building_data(...) 
    to produce a more "rich" building CSV with solar/battery columns.
    """
    buildings = generate_rich_building_data(num_buildings=num_buildings)
    write_buildings_to_csv(buildings, csv_filename=output_path)

if __name__ == "__main__":
    # If run standalone:
    generate_buildings_table(num_buildings=12, output_path="buildings_demo.csv")
