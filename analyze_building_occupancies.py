import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt

print("Starting building occupancy analysis...")

WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
ARTIFACTS_DIR = "/Users/mohit/.gemini/antigravity-ide/brain/bf91313d-4439-4159-84c3-6e663cbf1db5"

DAYS_MAP = {
    'Monday': '2026-07-06',
    'Tuesday': '2026-07-07',
    'Wednesday': '2026-07-08',
    'Thursday': '2026-07-09',
    'Friday': '2026-07-10'
}

# 1. Parse chosen day from command line arguments, default to "All"
SELECTED_DAY = "All"  # Options: Monday, Tuesday, Wednesday, Thursday, Friday, All

if len(sys.argv) > 1:
    arg = sys.argv[1].strip().capitalize()
    if arg in DAYS_MAP or arg == "All":
        SELECTED_DAY = arg
    else:
        print(f"Unknown option '{sys.argv[1]}'. Options are: Monday, Tuesday, Wednesday, Thursday, Friday, All.")
        print(f"Defaulting to: {SELECTED_DAY}")

print(f"Selected analysis range: {SELECTED_DAY}")

# 2. Load building coordinates from iitd.json
print("Loading building coordinate definitions...")
with open(os.path.join(WORKSPACE_DIR, 'iitd.json')) as f:
    geojson = json.load(f)

# Extract points and polygon centroids
building_coords = {}
for feat in geojson['features']:
    name = feat.get('properties', {}).get('name')
    gtype = feat['geometry']['type']
    coords = feat['geometry']['coordinates']
    
    if not name:
        continue
    
    if gtype == 'Point':
        building_coords[name] = (coords[1], coords[0])  # lat, lon
    elif gtype in ('Polygon', 'MultiPolygon'):
        if gtype == 'Polygon':
            ring = coords[0]
        else:
            ring = coords[0][0]
        lats = [pt[1] for pt in ring if pt]
        lons = [pt[0] for pt in ring if pt]
        centroid = (sum(lats)/len(lats), sum(lons)/len(lons))
        building_coords[name] = centroid

# Reverse lookup dictionary (coordinates rounded to 5 decimal places)
# This handles floating point representation differences
coord_to_building = {}
for name, (lat, lon) in building_coords.items():
    key = (round(lat, 5), round(lon, 5))
    coord_to_building[key] = name

# Buildings of interest to plot
target_buildings = ['lhc', 'DMS', 'blocks', 'dogra', 'ws']
building_occupancy = {b: [0]*24 for b in target_buildings}

# 3. Read trajectory.csv in chunks and filter for selected range
trajectory_path = os.path.join(WORKSPACE_DIR, 'trajectory.csv')
print(f"Reading and analyzing trajectory pings from {trajectory_path}...")

chunk_size = 1000000
pings_counted = 0

for chunk in pd.read_csv(trajectory_path, chunksize=chunk_size):
    # Filter based on selection
    if SELECTED_DAY in DAYS_MAP:
        day_chunk = chunk[chunk['timestamp'].str.startswith(DAYS_MAP[SELECTED_DAY])].copy()
    else:
        # "All" -> include all 5 weekdays
        day_chunk = chunk[chunk['timestamp'].str.slice(0, 10).isin(list(DAYS_MAP.values()))].copy()
        
    if day_chunk.empty:
        continue
        
    # Extract hour
    day_chunk['hour'] = day_chunk['timestamp'].str[11:13].astype(int)
    
    # Round coordinates to match building keys
    day_chunk['lat_r'] = day_chunk['lat'].round(5)
    day_chunk['lon_r'] = day_chunk['lon'].round(5)
    
    # Map coordinates to building names
    for (lat_r, lon_r), group in day_chunk.groupby(['lat_r', 'lon_r']):
        b_name = coord_to_building.get((lat_r, lon_r))
        if b_name in target_buildings:
            hour_counts = group['hour'].value_counts()
            for hr, count in hour_counts.items():
                # Divide count to reflect average concurrent occupancy:
                # - If single day: 12 pings/hour.
                # - If All days: 12 pings/hour * 5 days = 60 pings/hour.
                divider = 60.0 if SELECTED_DAY == "All" else 12.0
                building_occupancy[b_name][hr] += count / divider
                
    pings_counted += len(day_chunk)
    print(f"Processed {pings_counted} pings...")

# Round occupancies to integers
for b in target_buildings:
    building_occupancy[b] = [int(round(val)) for val in building_occupancy[b]]

# 4. Print report table
print(f"\n--- HOURLY OCCUPANCY SUMMARY ({SELECTED_DAY.upper()}) ---")
print(f"{'Hour':<6} | {'LHC':<6} | {'DMS':<6} | {'Blocks':<6} | {'Dogra':<6} | {'Workshop':<8}")
print("-" * 50)
for hr in range(24):
    print(f"{hr:02d}:00  | {building_occupancy['lhc'][hr]:<6} | {building_occupancy['DMS'][hr]:<6} | {building_occupancy['blocks'][hr]:<6} | {building_occupancy['dogra'][hr]:<6} | {building_occupancy['ws'][hr]:<8}")

# 5. Generate Plot
print("\nGenerating occupancy curves plot...")
plt.figure(figsize=(10, 6))
colors = {'lhc': '#1a73e8', 'DMS': '#34a853', 'blocks': '#ea4335', 'dogra': '#fbbc05', 'ws': '#ab47bc'}
names = {'lhc': 'Lecture Hall Complex (LHC)', 'DMS': 'Dept of Management Studies (DMS)', 'blocks': 'Academic Blocks', 'dogra': 'Dogra Hall', 'ws': 'Workshop (WS)'}

for b in target_buildings:
    plt.plot(range(24), building_occupancy[b], label=names[b], color=colors[b], linewidth=2.5)

title_label = "IIT Delhi - Average Weekday" if SELECTED_DAY == "All" else f"IIT Delhi - {SELECTED_DAY}"
plt.title(f'Hourly Building Occupancy Curves ({title_label})', fontsize=14, fontweight='bold')
plt.xlabel('Hour of Day (24h)', fontsize=12)
plt.ylabel('Concurrent Occupancy (Average Agents)', fontsize=12)
plt.xticks(range(24))
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend(fontsize=10, loc='upper left')
plt.tight_layout()
plt.show()
print("Analysis complete!")
