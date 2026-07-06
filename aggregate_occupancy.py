# aggregate_occupancy.py
"""
Process the 1GB trajectory.csv file in chunks to aggregate building occupancy
for each hour of each day of the week (Monday to Friday).

Outputs a compact building_occupancy_data.json that contains:
1. Hourly occupancies: day -> hour -> building -> average_agents
2. Coordinates of all buildings for drawing on the map.
"""

import os
import json
import pandas as pd
import numpy as np

WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
TRAJECTORY_CSV = os.path.join(WORKSPACE_DIR, "trajectory.csv")
OUTPUT_JSON = os.path.join(WORKSPACE_DIR, "building_occupancy_data.json")

DAYS_MAP = {
    "2026-07-06": "Monday",
    "2026-07-07": "Tuesday",
    "2026-07-08": "Wednesday",
    "2026-07-09": "Thursday",
    "2026-07-10": "Friday"
}

def load_buildings_and_coords():
    """Load building definitions and coordinates from iitd.json."""
    with open(os.path.join(WORKSPACE_DIR, "iitd.json")) as f:
        geojson = json.load(f)
    
    building_coords = {}
    building_styles = {}  # Store building type for styling on map
    
    for feat in geojson["features"]:
        props = feat.get("properties", {})
        name = props.get("name")
        gtype = feat["geometry"]["type"]
        coords = feat["geometry"]["coordinates"]
        b_id = props.get("@id", "")
        
        if not name:
            continue
            
        # Get centroid
        if gtype == "Point":
            centroid = (coords[1], coords[0])
        elif gtype in ("Polygon", "MultiPolygon"):
            if gtype == "Polygon":
                ring = coords[0]
            else:
                ring = coords[0][0]
            lats = [pt[1] for pt in ring if pt]
            lons = [pt[0] for pt in ring if pt]
            centroid = (sum(lats)/len(lats), sum(lons)/len(lons))
        else:
            continue
            
        # Categorize building type
        b_type = "academic"
        if "hostel" in b_id or name in ["satpura", "vindhyachal", "udaigiri", "shivalik", "kailash", "girnar", "aravali", "jwala", "nilgiri", "karakoram", "himadri", "zanskar"]:
            b_type = "hostel"
        elif name in ["SDA", "Type 4", "nalanda apt", "chat", "chattpura"] or "type" in name.lower() or "apt" in name.lower():
            b_type = "residential"
        elif "gate" in name.lower():
            b_type = "gate"
            
        building_coords[name] = centroid
        building_styles[name] = b_type
        
    return building_coords, building_styles

def load_agent_homes():
    """Load all agent home coordinates for fallback mapping."""
    agent_homes = {}
    
    # Load students
    students_file = os.path.join(WORKSPACE_DIR, "student_data.csv")
    if os.path.exists(students_file):
        df = pd.read_csv(students_file)
        for _, row in df.iterrows():
            agent_homes[row["Student ID"]] = (row["Home Latitude"], row["Home Longitude"], row["Hostel"])
            
    # Load professors
    profs_file = os.path.join(WORKSPACE_DIR, "professor_data.csv")
    if os.path.exists(profs_file):
        df = pd.read_csv(profs_file)
        for _, row in df.iterrows():
            agent_homes[row["Professor ID"]] = (row["Home Latitude"], row["Home Longitude"], row["Locality"])
            
    # Load staff
    staff_file = os.path.join(WORKSPACE_DIR, "staff_data.csv")
    if os.path.exists(staff_file):
        df = pd.read_csv(staff_file)
        for _, row in df.iterrows():
            agent_homes[row["Staff ID"]] = (row["Home Latitude"], row["Home Longitude"], row["Locality"])
            
    return agent_homes

def main():
    print("Loading building coordinate configurations...")
    building_coords, building_styles = load_buildings_and_coords()
    
    print("Loading agent home location mappings...")
    agent_homes = load_agent_homes()
    
    # Create reverse coordinate lookup (rounded to 5 decimals)
    coord_to_building = {}
    for name, (lat, lon) in building_coords.items():
        coord_to_building[(round(lat, 5), round(lon, 5))] = name
        
    # Also index agent home coordinates to map home pings exactly
    agent_home_to_loc = {}
    for agent_id, (lat, lon, loc_name) in agent_homes.items():
        agent_home_to_loc[agent_id] = loc_name
        
    # Initialize occupancy data structure
    # day -> hour -> building -> sum of pings
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    occupancy_pings = {day: {hour: {} for hour in range(24)} for day in days}
    
    # Process trajectory.csv in chunks
    chunk_size = 1000000
    total_processed = 0
    
    print(f"Reading and aggregating trajectories from {TRAJECTORY_CSV}...")
    
    # Track mapping helper cache to speed up lookups
    mapping_cache = {}
    
    for chunk in pd.read_csv(TRAJECTORY_CSV, chunksize=chunk_size):
        # Filter out commuting pings if needed
        # (Though we can still look them up, excluding them is cleaner for building occupancy)
        chunk = chunk[chunk["activity"] != "Commuting"]
        if chunk.empty:
            continue
            
        # Parse day name
        chunk["date_str"] = chunk["timestamp"].str.slice(0, 10)
        chunk["day"] = chunk["date_str"].map(DAYS_MAP)
        chunk = chunk.dropna(subset=["day"])
        if chunk.empty:
            continue
            
        # Parse hour
        chunk["hour"] = chunk["timestamp"].str.slice(11, 13).astype(int)
        
        # Round coordinates for mapping
        chunk["lat_r"] = chunk["lat"].round(5)
        chunk["lon_r"] = chunk["lon"].round(5)
        
        # Group by coordinates, day, hour, and activity
        for (lat_r, lon_r, day, hour), group in chunk.groupby(["lat_r", "lon_r", "day", "hour"]):
            coord_key = (lat_r, lon_r)
            
            # Resolve building name
            if coord_key in coord_to_building:
                b_name = coord_to_building[coord_key]
            else:
                # Cache lookup for performance
                if coord_key in mapping_cache:
                    b_name = mapping_cache[coord_key]
                else:
                    # Find closest building coordinate within 15 meters
                    best_name = None
                    best_dist = 9999.0
                    for name, (b_lat, b_lon) in building_coords.items():
                        dy = (b_lat - lat_r) * 111320.0
                        dx = (b_lon - lon_r) * 111320.0 * 0.88
                        dist = (dx*dx + dy*dy)**0.5
                        if dist < best_dist:
                            best_dist = dist
                            best_name = name
                    
                    if best_dist < 15.0:
                        b_name = best_name
                    else:
                        b_name = "Unknown"
                    mapping_cache[coord_key] = b_name
            
            if b_name != "Unknown":
                if b_name not in occupancy_pings[day][hour]:
                    occupancy_pings[day][hour][b_name] = 0
                occupancy_pings[day][hour][b_name] += len(group)
            else:
                # If building is unknown but agent is at Home, map to their home locality
                home_group = group[group["activity"] == "Home"]
                if not home_group.empty:
                    for agent_id, count in home_group["agent_id"].value_counts().items():
                        loc = agent_home_to_loc.get(agent_id, "Unknown")
                        if loc != "Unknown":
                            if loc not in occupancy_pings[day][hour]:
                                occupancy_pings[day][hour][loc] = 0
                            occupancy_pings[day][hour][loc] += count
                            
        total_processed += len(chunk)
        print(f"Processed {total_processed} pings...")

    # Normalize counts: divide by 12 to get average concurrent occupancy
    # Round to 1 decimal place to save space and display nicely
    final_occupancy = {}
    for day in days:
        final_occupancy[day] = {}
        for hour in range(24):
            final_occupancy[day][str(hour)] = {}
            for b_name, pings in occupancy_pings[day][hour].items():
                avg_occ = round(pings / 12.0, 1)
                if avg_occ > 0.1:
                    final_occupancy[day][str(hour)][b_name] = avg_occ
                    
    # Format building coordinates and styles for output JSON
    building_data = {}
    for name, centroid in building_coords.items():
        building_data[name] = {
            "lat": centroid[0],
            "lon": centroid[1],
            "type": building_styles.get(name, "academic")
        }

    output_data = {
        "building_data": building_data,
        "occupancy": final_occupancy
    }
    
    print(f"Saving compiled occupancy data to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, "w") as f_out:
        json.dump(output_data, f_out, indent=2)
        
    print("Aggregation complete!")

if __name__ == "__main__":
    main()
