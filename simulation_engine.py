import os
import re
import json
import math
import random
import pandas as pd
import numpy as np
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import folium
from shapely.geometry import shape

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

print("Starting simulation engine...")

# Directory paths
WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
ARTIFACTS_DIR = "/Users/mohit/.gemini/antigravity-ide/brain/bf91313d-4439-4159-84c3-6e663cbf1db5"

# 1. Load data
print("Loading data...")
with open(os.path.join(WORKSPACE_DIR, 'iitd.json')) as f:
    geojson = json.load(f)

students_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'student_data.csv'))
profs_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'professor_data.csv'))
schedule_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'schedule.csv'))

# Create mapping of building coordinates from GeoJSON
mapping = {}
boundary_geom = None
for feat in geojson['features']:
    name = feat.get('properties', {}).get('name')
    gtype = feat['geometry']['type']
    coords = feat['geometry']['coordinates']
    
    if feat.get('properties', {}).get('@id') == 'boundary' and name == 'IITD':
        boundary_geom = shape(feat['geometry'])
        
    if not name:
        continue
    
    if gtype == 'Point':
        mapping[name] = (coords[1], coords[0])  # (lat, lon)
    elif gtype in ('Polygon', 'MultiPolygon'):
        if gtype == 'Polygon':
            ring = coords[0]
        else:
            ring = coords[0][0]
        lats = [pt[1] for pt in ring if pt]
        lons = [pt[0] for pt in ring if pt]
        centroid = (sum(lats)/len(lats), sum(lons)/len(lons))
        mapping[name] = centroid

if boundary_geom is None:
    raise ValueError("Campus boundary geometry not found in iitd.json")

# 2. Get OpenStreetMap walk network
print("Loading Walk network from OSMnx...")
buffered_boundary = boundary_geom.buffer(0.005)  # 500m buffer
G = ox.graph_from_polygon(buffered_boundary, network_type='walk')
print(f"OSM Walk network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")

# Fast distance helper
def get_distance_meters(p1, p2):
    lat1, lon1 = p1
    lat2, lon2 = p2
    dy = (lat2 - lat1) * 111320.0
    dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dx*dx + dy*dy)

# 3. Path Pre-computation
print("Pre-computing paths...")
node_cache = {}
def get_nearest_node(lat, lon):
    key = (round(lat, 6), round(lon, 6))
    if key not in node_cache:
        node_cache[key] = ox.distance.nearest_nodes(G, lon, lat)
    return node_cache[key]

# Cache paths between unique node pairs
path_coords_cache = {}
def get_shortest_path_coords(start_lat, start_lon, end_lat, end_lon):
    start_node = get_nearest_node(start_lat, start_lon)
    end_node = get_nearest_node(end_lat, end_lon)
    
    if start_node == end_node:
        return [(start_lat, start_lon)]
        
    pair_key = (start_node, end_node)
    if pair_key not in path_coords_cache:
        try:
            path = nx.shortest_path(G, start_node, end_node, weight='length')
            # Extract lat, lon of each node
            coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
            # Replace ends with exact coordinates for precision
            coords[0] = (start_lat, start_lon)
            coords[-1] = (end_lat, end_lon)
            path_coords_cache[pair_key] = coords
        except nx.NetworkXNoPath:
            path_coords_cache[pair_key] = [(start_lat, start_lon), (end_lat, end_lon)]
            
    return path_coords_cache[pair_key]

# Linear interpolation along path
def interpolate_coords(path_coords, num_steps):
    if not path_coords:
        return []
    if len(path_coords) == 1 or num_steps <= 1:
        return [path_coords[0]] * num_steps
        
    # Calculate cumulative distance along path
    dists = [0.0]
    for i in range(1, len(path_coords)):
        dists.append(dists[-1] + get_distance_meters(path_coords[i-1], path_coords[i]))
        
    total_dist = dists[-1]
    if total_dist == 0:
        return [path_coords[0]] * num_steps
        
    step_coords = []
    for step in range(num_steps):
        fraction = step / max(1, num_steps - 1)
        target_dist = fraction * total_dist
        
        idx = 0
        while idx < len(dists) - 1 and dists[idx+1] < target_dist:
            idx += 1
            
        p1 = path_coords[idx]
        p2 = path_coords[idx+1]
        d1 = dists[idx]
        d2 = dists[idx+1]
        
        seg_fraction = (target_dist - d1) / (d2 - d1)
        lat = p1[0] + seg_fraction * (p2[0] - p1[0])
        lon = p1[1] + seg_fraction * (p2[1] - p1[1])
        step_coords.append((lat, lon))
        
    return step_coords

# 4. Map agent ids to home coordinates
print("Mapping agents to home coords...")
agent_home = {}
for _, row in students_df.iterrows():
    agent_home[row['Student ID']] = (row['Home Latitude'], row['Home Longitude'])
for _, row in profs_df.iterrows():
    agent_home[row['Professor ID']] = (row['Home Latitude'], row['Home Longitude'])

# Map schedules by agent and day
print("Indexing schedule data...")
# Index schedules: schedule_dict[agent_id][day] = list of (start_min, end_min, lat, lon)
schedule_dict = {}
for _, row in schedule_df.iterrows():
    agent_id = row['agent_id']
    day = row['day']
    
    # Parse start and end times to minutes of day
    try:
        sh, sm_ = map(int, row['start_time'].split(':'))
        eh, em_ = map(int, row['end_time'].split(':'))
        start_min = sh * 60 + sm_
        end_min = eh * 60 + em_
    except Exception:
        continue
        
    if agent_id not in schedule_dict:
        schedule_dict[agent_id] = {}
    if day not in schedule_dict[agent_id]:
        schedule_dict[agent_id][day] = []
        
    schedule_dict[agent_id][day].append({
        'start_min': start_min,
        'end_min': end_min,
        'lat': row['room_lat'],
        'lon': row['room_lon']
    })

# Sort schedules by start time
for agent_id in schedule_dict:
    for day in schedule_dict[agent_id]:
        schedule_dict[agent_id][day].sort(key=lambda x: x['start_min'])

# 5. Simulation Logic
print("Running trajectory simulation...")
days_map = {
    'M': '2026-07-06',
    'T': '2026-07-07',
    'W': '2026-07-08',
    'Th': '2026-07-09',
    'F': '2026-07-10'
}

walking_speed_mps = 1.2
timestep_min = 5
step_distance_limit = walking_speed_mps * (timestep_min * 60) # 360 meters per 5 mins

# Open file for writing trajectories
trajectory_file_path = os.path.join(WORKSPACE_DIR, 'trajectory.csv')

# Pre-determine agents list to run
all_agents = list(agent_home.keys())

print(f"Total agents to simulate: {len(all_agents)}")
simulated_count = 0

with open(trajectory_file_path, 'w') as f_out:
    f_out.write("agent_id,timestamp,lat,lon\n")
    
    for agent_idx, agent_id in enumerate(all_agents):
        home_lat, home_lon = agent_home[agent_id]
        agent_schedules = schedule_dict.get(agent_id, {})
        
        if agent_idx > 0 and agent_idx % 2000 == 0:
            print(f"Simulated trajectories for {agent_idx} agents...")
            
        for day_code, date_str in days_map.items():
            day_schedule = agent_schedules.get(day_code, [])
            
            # Construct hourly schedule plan (288 steps)
            # Default target is home
            target_coords = [(home_lat, home_lon)] * 288
            
            # Overlay scheduled classes/work
            for activity in day_schedule:
                start_step = activity['start_min'] // timestep_min
                end_step = activity['end_min'] // timestep_min
                # Make sure bounds are clean
                start_step = max(0, min(287, start_step))
                end_step = max(0, min(287, end_step))
                
                for step in range(start_step, end_step):
                    target_coords[step] = (activity['lat'], activity['lon'])
            
            # Apply transition smoothing (routing)
            actual_coords = list(target_coords)
            
            # Identify transition intervals
            step = 1
            while step < 288:
                prev_loc = actual_coords[step-1]
                curr_loc = actual_coords[step]
                
                # If target changes, we need a transition routing
                if prev_loc != curr_loc:
                    # Calculate shortest path distance
                    path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
                    path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
                    
                    # Estimate steps needed for transition (walking speed = 1.2 m/s)
                    duration_sec = path_dist / walking_speed_mps
                    duration_steps = int(math.ceil(duration_sec / (timestep_min * 60)))
                    duration_steps = max(1, duration_steps)
                    
                    # We start walking prior to the transition
                    start_transition_step = max(0, step - duration_steps)
                    end_transition_step = step
                    
                    # Interpolate along the path
                    transition_len = end_transition_step - start_transition_step
                    interpolated = interpolate_coords(path_points, transition_len)
                    
                    for t_idx, t_step in enumerate(range(start_transition_step, end_transition_step)):
                        actual_coords[t_step] = interpolated[t_idx]
                        
                    # Skip checked steps
                    step = end_transition_step
                step += 1
            
            # Write trajectory to CSV
            for step in range(288):
                total_min = step * timestep_min
                hh = total_min // 60
                mm = total_min % 60
                timestamp_str = f"{date_str} {hh:02d}:{mm:02d}:00"
                lat, lon = actual_coords[step]
                f_out.write(f"{agent_id},{timestamp_str},{lat:.6f},{lon:.6f}\n")

print(f"Trajectory generation complete! Saved to {trajectory_file_path}")

# 6. Validation & Plotting (Task 5)
print("Analyzing trajectories for validation plots...")
# To analyze occupancy, we read a sample of the trajectory data to avoid memory overflow,
# or we compute it on the fly or load the generated file.

off_campus_homes = {}
for agent_id, coord in agent_home.items():
    from shapely.geometry import Point
    p = Point(coord[1], coord[0])
    off_campus_homes[agent_id] = not boundary_geom.contains(p)

print("Calculating hourly occupancy...")
sample_fraction = 1.0
sample_agents = random.sample(all_agents, int(len(all_agents) * sample_fraction))
print(f"Using a {sample_fraction*100}% sample ({len(sample_agents)} agents) for occupancy curve...")

# Occupancy grid: 5 days (Mon-Fri) x 24 hours
occupancy_counts = {day: [0]*24 for day in days_map.keys()}
arrival_times = []
departure_times = []

for agent_id in sample_agents:
    home_lat, home_lon = agent_home[agent_id]
    agent_schedules = schedule_dict.get(agent_id, {})
    is_off_campus = off_campus_homes[agent_id]
    
    for day_code in days_map.keys():
        day_schedule = agent_schedules.get(day_code, [])
        target_coords = [(home_lat, home_lon)] * 288
        for activity in day_schedule:
            start_step = max(0, min(287, activity['start_min'] // timestep_min))
            end_step = max(0, min(287, activity['end_min'] // timestep_min))
            for step in range(start_step, end_step):
                target_coords[step] = (activity['lat'], activity['lon'])
                
        actual_coords = list(target_coords)
        step = 1
        while step < 288:
            prev_loc = actual_coords[step-1]
            curr_loc = actual_coords[step]
            if prev_loc != curr_loc:
                path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
                path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
                duration_steps = max(1, int(math.ceil((path_dist / walking_speed_mps) / (timestep_min * 60))))
                start_transition_step = max(0, step - duration_steps)
                interpolated = interpolate_coords(path_points, step - start_transition_step)
                for t_idx, t_step in enumerate(range(start_transition_step, step)):
                    actual_coords[t_step] = interpolated[t_idx]
            step += 1
            
        on_campus_profile = [False] * 288
        for step in range(288):
            lat, lon = actual_coords[step]
            if not is_off_campus:
                on_campus_profile[step] = True
            else:
                on_campus_profile[step] = (abs(lat - home_lat) > 0.0001 or abs(lon - home_lon) > 0.0001)
        
        for hour in range(24):
            steps_in_hour = on_campus_profile[hour*12 : (hour+1)*12]
            if any(steps_in_hour):
                occupancy_counts[day_code][hour] += 1
                
        if is_off_campus and any(on_campus_profile):
            first_step = on_campus_profile.index(True)
            last_step = len(on_campus_profile) - 1 - on_campus_profile[::-1].index(True)
            
            arrival_times.append((first_step * timestep_min) / 60.0)
            departure_times.append((last_step * timestep_min) / 60.0)

# Scale counts back up to represent total population
scaling_factor = 1.0 / sample_fraction
for day in occupancy_counts:
    occupancy_counts[day] = [int(count * scaling_factor) for count in occupancy_counts[day]]

# Plot 1: Campus Occupancy Curve
plt.figure(figsize=(10, 6))
days_names = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'Th': 'Thursday', 'F': 'Friday'}
for day_code, counts in occupancy_counts.items():
    plt.plot(range(24), counts, label=days_names[day_code], linewidth=2.5)
plt.title('Hourly Campus Occupancy Curve (IIT Delhi)', fontsize=14, fontweight='bold')
plt.xlabel('Hour of Day (24h)', fontsize=12)
plt.ylabel('Number of Agents on Campus', fontsize=12)
plt.xticks(range(24))
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(fontsize=10)
plt.tight_layout()
plt.show()

# Plot 2: Arrival & Departure Time Distributions
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.hist(arrival_times, bins=24, range=(0, 24), color='skyblue', edgecolor='black', alpha=0.8)
plt.title('Agent Arrival Time Distribution', fontsize=12, fontweight='bold')
plt.xlabel('Hour of Entry', fontsize=10)
plt.ylabel('Frequency (Sample Count)', fontsize=10)
plt.xticks(range(0, 25, 2))
plt.grid(True, linestyle='--', alpha=0.5)

plt.subplot(1, 2, 2)
plt.hist(departure_times, bins=24, range=(0, 24), color='salmon', edgecolor='black', alpha=0.8)
plt.title('Agent Departure Time Distribution', fontsize=12, fontweight='bold')
plt.xlabel('Hour of Exit', fontsize=10)
plt.ylabel('Frequency (Sample Count)', fontsize=10)
plt.xticks(range(0, 25, 2))
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# 7. Interactive Map Visualization (Folium)
print("Generating folium interactive map with sample trajectories...")
campus_centroid = [boundary_geom.centroid.y, boundary_geom.centroid.x]
m = folium.Map(location=campus_centroid, zoom_start=15, tiles="CartoDB positron")

folium.GeoJson(
    data=boundary_geom.__geo_interface__,
    style_function=lambda x: {
        'fillColor': '#1a73e8',
        'color': '#1a73e8',
        'weight': 2.5,
        'fillOpacity': 0.08
    },
    name="IIT Delhi Campus Boundary"
).add_to(m)

sample_visualization_agents = []
# B.Tech
bt_candidates = students_df[~students_df['Branch'].str.endswith('Z')]['Student ID'].tolist()
if bt_candidates:
    sample_visualization_agents.append((random.choice(bt_candidates), 'blue', 'B.Tech Student'))
# PhD
phd_candidates = students_df[students_df['Branch'].str.endswith('Z')]['Student ID'].tolist()
if phd_candidates:
    sample_visualization_agents.append((random.choice(phd_candidates), 'green', 'PhD Student'))
# Professor
prof_candidates = profs_df['Professor ID'].tolist()
if prof_candidates:
    sample_visualization_agents.append((random.choice(prof_candidates), 'red', 'Professor'))

for agent_id, color, label in sample_visualization_agents:
    home_lat, home_lon = agent_home[agent_id]
    agent_schedules = schedule_dict.get(agent_id, {})
    day_schedule = agent_schedules.get('M', [])
    
    target_coords = [(home_lat, home_lon)] * 288
    for activity in day_schedule:
        start_step = max(0, min(287, activity['start_min'] // timestep_min))
        end_step = max(0, min(287, activity['end_min'] // timestep_min))
        for step in range(start_step, end_step):
            target_coords[step] = (activity['lat'], activity['lon'])
            
    actual_coords = list(target_coords)
    step = 1
    while step < 288:
        prev_loc = actual_coords[step-1]
        curr_loc = actual_coords[step]
        if prev_loc != curr_loc:
            path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
            path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
            duration_steps = max(1, int(math.ceil((path_dist / walking_speed_mps) / (timestep_min * 60))))
            start_transition_step = max(0, step - duration_steps)
            interpolated = interpolate_coords(path_points, step - start_transition_step)
            for t_idx, t_step in enumerate(range(start_transition_step, step)):
                actual_coords[t_step] = interpolated[t_idx]
        step += 1
        
    route_points = []
    for lat, lon in actual_coords:
        if not route_points or route_points[-1] != [lat, lon]:
            route_points.append([lat, lon])
            
    folium.PolyLine(
        locations=route_points,
        color=color,
        weight=4,
        opacity=0.8,
        tooltip=f"{label} ({agent_id}) Monday Route"
    ).add_to(m)
    
    folium.CircleMarker(
        location=[home_lat, home_lon],
        radius=6,
        color=color,
        fill=True,
        fill_color='white',
        popup=f"{label} Home"
    ).add_to(m)
    
    destinations = set()
    for activity in day_schedule:
        destinations.add((activity['lat'], activity['lon']))
    for d_lat, d_lon in destinations:
        folium.CircleMarker(
            location=[d_lat, d_lon],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            popup=f"{label} Activity Room"
        ).add_to(m)

folium.LayerControl().add_to(m)
map_html_path = os.path.join(WORKSPACE_DIR, 'sample_trajectories_map.html')
m.save(map_html_path)
m.save(os.path.join(ARTIFACTS_DIR, 'sample_trajectories_map.html'))
print(f"Sample trajectories interactive map saved to {map_html_path}")

print("Simulation engine pipeline executed successfully!")
