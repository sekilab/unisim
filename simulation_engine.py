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
SAMPLING = 1
# Fast distance helper
def get_distance_meters(p1, p2):
    lat1, lon1 = p1
    lat2, lon2 = p2
    dy = (lat2 - lat1) * 111320.0
    dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dx*dx + dy*dy)

print("Starting simulation engine...")

# Directory paths
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, "output")

# 1. Load data
print("Loading data...")
with open(os.path.join(WORKSPACE_DIR, 'data_source', 'iitd.json')) as f:
    geojson = json.load(f)

students_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'student_data.csv'))
profs_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'professor_data.csv'))
schedule_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'schedule.csv'))

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
import graph_io
geojson_path = os.path.join(WORKSPACE_DIR, 'data_source', 'graph.geojson')
if os.path.exists(geojson_path):
    print(f"Loading custom waypoint graph from {geojson_path}...")
    G = graph_io.load_graph_from_geojson(geojson_path)
else:
    print("Loading Walk network from OSMnx...")
    all_lats = list(students_df['Home Latitude']) + list(profs_df['Home Latitude']) + list(schedule_df['room_lat'].dropna())
    all_lons = list(students_df['Home Longitude']) + list(profs_df['Home Longitude']) + list(schedule_df['room_lon'].dropna())
    staff_data_path = os.path.join(WORKSPACE_DIR, 'data_source', 'staff_data.csv')
    if os.path.exists(staff_data_path):
        s_df = pd.read_csv(staff_data_path)
        all_lats += list(s_df['Home Latitude'])
        all_lons += list(s_df['Home Longitude'])

    west = min(all_lons) - 0.002
    south = min(all_lats) - 0.002
    east = max(all_lons) + 0.002
    north = max(all_lats) + 0.002

    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type='walk')
    print(f"OSM Walk network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # Connect gates (ks_gate, js_gate) to bridge inside/outside network gaps
    gates_to_connect = [
        ('ks_gate', 30.0),
        ('js_gate', 50.0)
    ]

    from shapely.geometry import Point
    for gate_name, search_radius in gates_to_connect:
        gate_coords = mapping.get(gate_name)
        if not gate_coords:
            continue
        gate_lat, gate_lon = gate_coords
        
        inside_node, outside_node = None, None
        min_dist_in, min_dist_out = 999.0, 999.0
        for n in G.nodes:
            n_lat = G.nodes[n]['y']
            n_lon = G.nodes[n]['x']
            dist = get_distance_meters((gate_lat, gate_lon), (n_lat, n_lon))
            if dist < search_radius:
                p = Point(n_lon, n_lat)
                if boundary_geom.contains(p):
                    if dist < min_dist_in:
                        min_dist_in = dist
                        inside_node = n
                else:
                    if dist < min_dist_out:
                        min_dist_out = dist
                        outside_node = n
                        
        if inside_node is not None and outside_node is not None:
            dist_m = get_distance_meters((G.nodes[inside_node]['y'], G.nodes[inside_node]['x']),
                                          (G.nodes[outside_node]['y'], G.nodes[outside_node]['x']))
            G.add_edge(inside_node, outside_node, key=0, length=dist_m, highway='path')
            G.add_edge(outside_node, inside_node, key=0, length=dist_m, highway='path')
            print(f"Connected {gate_name}: node {inside_node} (inside) <-> node {outside_node} (outside), distance {dist_m:.2f}m")
            
    graph_io.connect_dead_ends(G, max_dist=20.0)
    graph_io.connect_disconnected_components(G, max_dist=20.0)
    print(f"Exporting Walk network to {geojson_path} for manual customization...")
    graph_io.save_graph_to_geojson(G, geojson_path)






# 3. Path Pre-computation
print("Pre-computing paths...")
G_routing = G.subgraph([n for n in G.nodes if G.degree(n) > 0])
node_cache = {}
def get_nearest_node(lat, lon):
    key = (round(lat, 6), round(lon, 6))
    if key not in node_cache:
        node_cache[key] = ox.distance.nearest_nodes(G_routing, lon, lat)
    return node_cache[key]

def get_snapped_coord(lat, lon):
    node = get_nearest_node(lat, lon)
    return (G_routing.nodes[node]['y'], G_routing.nodes[node]['x'])

path_coords_cache = {}
def get_shortest_path_coords(start_lat, start_lon, end_lat, end_lon):
    start_node = get_nearest_node(start_lat, start_lon)
    end_node = get_nearest_node(end_lat, end_lon)
    
    if start_node == end_node:
        coord = (G.nodes[start_node]['y'], G.nodes[start_node]['x'])
        return [coord, coord]
        
    pair_key = (start_node, end_node)
    if pair_key not in path_coords_cache:
        try:
            path = nx.shortest_path(G, start_node, end_node, weight='length')
            coords = []
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                u_coord = (G.nodes[u]['y'], G.nodes[u]['x'])
                v_coord = (G.nodes[v]['y'], G.nodes[v]['x'])
                
                edge_data = G.get_edge_data(u, v)
                edge_coords = []
                if edge_data:
                    best_key = min(edge_data.keys(), key=lambda k: edge_data[k].get('length', float('inf')))
                    data = edge_data[best_key]
                    if 'geometry' in data:
                        geom_coords = [(lat, lon) for lon, lat in data['geometry'].coords]
                        if len(geom_coords) > 1:
                            dist_start = get_distance_meters(u_coord, geom_coords[0])
                            dist_end = get_distance_meters(u_coord, geom_coords[-1])
                            if dist_end < dist_start:
                                geom_coords.reverse()
                        edge_coords = geom_coords
                    else:
                        edge_coords = [u_coord, v_coord]
                else:
                    edge_coords = [u_coord, v_coord]
                    
                if not coords:
                    coords.extend(edge_coords)
                else:
                    coords.extend(edge_coords[1:])
            path_coords_cache[pair_key] = coords
        except nx.NetworkXNoPath:
            path_coords_cache[pair_key] = None
            
    res = path_coords_cache[pair_key]
    if res is None:
        return None
    return list(res)

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
        seg_fraction = (target_dist - d1) / (d2 - d1) if (d2 - d1) != 0 else 0.0
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

# Load and map non-teaching staff home coordinates
staff_data_path = os.path.join(WORKSPACE_DIR, 'data_source', 'staff_data.csv')
if os.path.exists(staff_data_path):
    staff_df = pd.read_csv(staff_data_path)
    for _, row in staff_df.iterrows():
        agent_home[row['Staff ID']] = (row['Home Latitude'], row['Home Longitude'])

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
        
        # Add random offset of +/- 5 minutes
        start_min = max(0, min(1439, start_min + random.randint(-5, 5)))
        end_min = max(start_min + 5, min(1440, end_min + random.randint(-5, 5)))
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
        'lon': row['room_lon'],
        'activity': row['activity']
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

# Pre-generate time and speed offsets per agent for consistency
random.seed(42)
agent_speed_dict = {}
agent_time_offset_dict = {}
for agent_id in agent_home:
    agent_speed_dict[agent_id] = random.uniform(1.0, 1.4)
    agent_time_offset_dict[agent_id] = random.randint(-120, 120)  # offset in seconds (±2 mins)

def get_agent_speed(agent_id=None):
    if agent_id is not None:
        return agent_speed_dict.get(agent_id, 1.2)
    return random.uniform(1.0, 1.4)

def get_agent_time_offset(agent_id):
    return agent_time_offset_dict.get(agent_id, 0)

walking_speed_mps = 1.2
timestep_min = 1
steps_per_day = 1440 // timestep_min
step_distance_limit = walking_speed_mps * (timestep_min * 60)

# Open file for writing trajectories
trajectory_file_path = os.path.join(WORKSPACE_DIR, 'trajectories', 'trajectory.csv')

# Sample a subset of agents (e.g., 10% of the total population)
sample_fraction = SAMPLING  # Set to 0.1 for 10%, 0.5 for 50%, etc.
all_agents = random.sample(list(agent_home.keys()), int(len(agent_home) * sample_fraction))

print(f"Total agents to simulate: {len(all_agents)}")
simulated_count = 0

with open(trajectory_file_path, 'w') as f_out:
    f_out.write("agent_id,timestamp,lat,lon,activity\n")
    
    for agent_idx, agent_id in enumerate(all_agents):
        home_lat_raw, home_lon_raw = agent_home[agent_id]
        home_lat, home_lon = get_snapped_coord(home_lat_raw, home_lon_raw)
        agent_schedules = schedule_dict.get(agent_id, {})
        agent_speed = get_agent_speed(agent_id)
        
        if agent_idx > 0 and agent_idx % 2000 == 0:
            print(f"Simulated trajectories for {agent_idx} agents...")
            
        for day_code, date_str in days_map.items():
            day_schedule = agent_schedules.get(day_code, [])
            
            # Construct hourly schedule plan (steps_per_day steps)
            # Default target is home
            target_coords = [(home_lat, home_lon)] * steps_per_day
            target_activities = ["Home"] * steps_per_day
            
            # Overlay scheduled classes/work
            for activity in day_schedule:
                start_step = activity['start_min'] // timestep_min
                end_step = activity['end_min'] // timestep_min
                # Make sure bounds are clean
                start_step = max(0, min(steps_per_day - 1, start_step))
                end_step = max(0, min(steps_per_day - 1, end_step))
                
                # Determine activity name from schedule data
                act_name = activity['activity']
                act_lat, act_lon = get_snapped_coord(activity['lat'], activity['lon'])
                
                for step in range(start_step, end_step):
                    target_coords[step] = (act_lat, act_lon)
                    target_activities[step] = act_name
            
            # Apply block-based transition routing for realistic early departures
            actual_coords = [(0.0, 0.0)] * steps_per_day
            actual_activities = [""] * steps_per_day
            
            # Extract desired schedule blocks
            desired_blocks = []
            current_act = target_activities[0]
            current_loc = target_coords[0]
            start_step = 0
            for step in range(1, steps_per_day):
                if target_activities[step] != current_act or target_coords[step] != current_loc:
                    desired_blocks.append({
                        'name': current_act,
                        'loc': current_loc,
                        'start': start_step,
                        'end': step - 1
                    })
                    current_act = target_activities[step]
                    current_loc = target_coords[step]
                    start_step = step
            desired_blocks.append({
                'name': current_act,
                'loc': current_loc,
                'start': start_step,
                'end': steps_per_day - 1
            })
            
            last_arrival_step = 0
            
            for i in range(len(desired_blocks)):
                block = desired_blocks[i]
                if i == 0:
                    pass
                else:
                    prev_block = desired_blocks[i-1]
                    # Calculate shortest path distance
                    if prev_block['loc'] == block['loc']:
                        duration_steps = 0
                        interpolated = []
                    else:
                        path_points = get_shortest_path_coords(prev_block['loc'][0], prev_block['loc'][1], block['loc'][0], block['loc'][1])
                        if path_points is None:
                            duration_steps = 1
                            interpolated = [block['loc']]
                        else:
                            path_dist = sum(get_distance_meters(path_points[k-1], path_points[k]) for k in range(1, len(path_points)))
                            duration_sec = path_dist / agent_speed
                            duration_steps = max(1, int(math.ceil(duration_sec / (timestep_min * 60))))
                            interpolated = interpolate_coords(path_points, duration_steps)
                        
                    target_arrival = block['start']
                    # Back-propagate commute duration to find departure time
                    commute_start = target_arrival - duration_steps
                    
                    # If leaving from Class to Home or Work, can only leave when 10 minutes are remaining for class to end
                    if prev_block['name'] == 'Class' and block['name'] in ['Home', 'Work']:
                        earliest_departure = (prev_block['end'] + 1) - 10
                        if commute_start < earliest_departure:
                            commute_start = earliest_departure

                    # Prevent teleportation/time-travel: cannot depart before arriving at previous location!
                    if commute_start < last_arrival_step:
                        commute_start = last_arrival_step
                        
                    actual_arrival = commute_start + duration_steps
                    
                    # Stay at previous location until commute starts
                    for t in range(last_arrival_step, commute_start):
                        if t < steps_per_day:
                            actual_coords[t] = prev_block['loc']
                            actual_activities[t] = prev_block['name']
                            
                    # Commute to new location
                    for idx, t in enumerate(range(commute_start, actual_arrival)):
                        if t < steps_per_day:
                            actual_coords[t] = interpolated[idx] if idx < len(interpolated) else block['loc']
                            actual_activities[t] = "Commuting"
                            
                    last_arrival_step = actual_arrival

            # Stay at final location for the rest of the day
            final_block = desired_blocks[-1]
            for t in range(last_arrival_step, steps_per_day):
                actual_coords[t] = final_block['loc']
                actual_activities[t] = final_block['name']
            
            # Write trajectory to CSV (only write when moving or transitioning states to save space)
            import datetime
            base_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            time_offset = get_agent_time_offset(agent_id)
            
            for step in range(steps_per_day):
                # Write if:
                # 1. First or last step of the day (starting/ending baseline)
                # 2. Coordinates or activity changed from previous step (start of movement, arrival, or activity change)
                # 3. Coordinates or activity will change in the next step (last step before departure or activity change)
                is_first_last = (step == 0 or step == steps_per_day - 1)
                changed_from_prev = (step > 0 and (actual_coords[step] != actual_coords[step-1] or actual_activities[step] != actual_activities[step-1]))
                will_change_next = (step < steps_per_day - 1 and (actual_coords[step] != actual_coords[step+1] or actual_activities[step] != actual_activities[step+1]))
                
                if is_first_last or changed_from_prev or will_change_next:
                    total_sec = step * timestep_min * 60 + time_offset
                    # Ensure the time does not go negative
                    total_sec = max(0, total_sec)
                    dt = base_date + datetime.timedelta(seconds=total_sec)
                    timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    lat, lon = actual_coords[step]
                    act = actual_activities[step]
                    f_out.write(f"{agent_id},{timestamp_str},{lat:.6f},{lon:.6f},{act}\n")

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
arrival_times = {day: [] for day in days_map.keys()}
departure_times = {day: [] for day in days_map.keys()}

for agent_id in sample_agents:
    home_lat, home_lon = agent_home[agent_id]
    agent_schedules = schedule_dict.get(agent_id, {})
    is_off_campus = off_campus_homes[agent_id]
    agent_speed = get_agent_speed(agent_id)
    time_offset = get_agent_time_offset(agent_id)
    time_offset_hours = time_offset / 3600.0
    
    for day_code in days_map.keys():
        day_schedule = agent_schedules.get(day_code, [])
        target_coords = [(home_lat, home_lon)] * steps_per_day
        for activity in day_schedule:
            start_step = max(0, min(steps_per_day - 1, activity['start_min'] // timestep_min))
            end_step = max(0, min(steps_per_day - 1, activity['end_min'] // timestep_min))
            act_lat, act_lon = get_snapped_coord(activity['lat'], activity['lon'])
            for step in range(start_step, end_step):
                target_coords[step] = (act_lat, act_lon)
                
        actual_coords = list(target_coords)
        step = 1
        while step < steps_per_day:
            prev_loc = actual_coords[step-1]
            curr_loc = target_coords[step]
            if prev_loc != curr_loc:
                path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
                if path_points is None:
                    actual_coords[step] = prev_loc
                    step += 1
                    continue
                path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
                duration_steps = max(1, int(math.ceil((path_dist / agent_speed) / (timestep_min * 60))))
                
                start_transition_step = step
                end_transition_step = min(steps_per_day, step + duration_steps)
                
                transition_len = end_transition_step - start_transition_step
                interpolated = interpolate_coords(path_points, transition_len)
                for t_idx, t_step in enumerate(range(start_transition_step, end_transition_step)):
                    actual_coords[t_step] = interpolated[t_idx]
                    
                for t_step in range(end_transition_step, steps_per_day):
                    actual_coords[t_step] = curr_loc
                    
                step = end_transition_step
            else:
                step += 1
            
        on_campus_profile = [False] * steps_per_day
        for step in range(steps_per_day):
            lat, lon = actual_coords[step]
            if not is_off_campus:
                on_campus_profile[step] = True
            else:
                on_campus_profile[step] = (abs(lat - home_lat) > 0.0001 or abs(lon - home_lon) > 0.0001)
        
        steps_per_hour = 60 // timestep_min
        for hour in range(24):
            steps_in_hour = on_campus_profile[hour*steps_per_hour : (hour+1)*steps_per_hour]
            if any(steps_in_hour):
                occupancy_counts[day_code][hour] += 1
                
        is_student = str(agent_id)[0].isdigit()
        if is_student or is_off_campus:
            away_profile = [False] * steps_per_day
            for step in range(steps_per_day):
                lat, lon = actual_coords[step]
                away_profile[step] = (abs(lat - home_lat) > 0.0001 or abs(lon - home_lon) > 0.0001)
                
            if any(away_profile):
                first_step = away_profile.index(True)
                last_step = len(away_profile) - 1 - away_profile[::-1].index(True)
                
                arrival_times[day_code].append((first_step * timestep_min) / 60.0 + time_offset_hours)
                departure_times[day_code].append((last_step * timestep_min) / 60.0 + time_offset_hours)

# Scale counts back up to represent total population
# scaling_factor = 1.0 / sample_fraction
# for day in occupancy_counts:
#     occupancy_counts[day] = [int(count * scaling_factor) for count in occupancy_counts[day]]

# # Plot 1: Campus Occupancy Curve
# plt.figure(figsize=(10, 6))
# days_names = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'Th': 'Thursday', 'F': 'Friday'}
# for day_code, counts in occupancy_counts.items():
#     plt.plot(range(24), counts, label=days_names[day_code], linewidth=2.5)
# plt.title('Hourly Campus Occupancy Curve (IIT Delhi)', fontsize=14, fontweight='bold')
# plt.xlabel('Hour of Day (24h)', fontsize=12)
# plt.ylabel('Number of Agents on Campus', fontsize=12)
# plt.xticks(range(24))
# plt.grid(True, linestyle='--', alpha=0.6)
# plt.legend(fontsize=10)
# plt.tight_layout()
# plt.show()

# # Plot 2: Arrival & Departure Time Distributions for each of the 5 days
# for day_code, day_name in days_names.items():
#     plt.figure(figsize=(12, 5))
#     plt.subplot(1, 2, 1)
#     weights_arr = np.ones_like(arrival_times[day_code]) * (1.0 / sample_fraction)
#     plt.hist(arrival_times[day_code], bins=24, range=(0, 24), weights=weights_arr, color='skyblue', edgecolor='black', alpha=0.8)
#     plt.title(f'Agent Arrival Time Distribution - {day_name}', fontsize=12, fontweight='bold')
#     plt.xlabel('Hour of Entry', fontsize=10)
#     plt.ylabel('Number of Agents', fontsize=10)
#     plt.xticks(range(0, 25, 2))
#     plt.grid(True, linestyle='--', alpha=0.5)

#     plt.subplot(1, 2, 2)
#     weights_dep = np.ones_like(departure_times[day_code]) * (1.0 / sample_fraction)
#     plt.hist(departure_times[day_code], bins=24, range=(0, 24), weights=weights_dep, color='salmon', edgecolor='black', alpha=0.8)
#     plt.title(f'Agent Departure Time Distribution - {day_name}', fontsize=12, fontweight='bold')
#     plt.xlabel('Hour of Exit', fontsize=10)
#     plt.ylabel('Number of Agents', fontsize=10)
#     plt.xticks(range(0, 25, 2))
#     plt.grid(True, linestyle='--', alpha=0.5)
#     plt.tight_layout()
    
#     dist_plot_path = os.path.join(WORKSPACE_DIR, 'analysis_output', f'arrival_departure_{day_name}.png')
#     plt.savefig(dist_plot_path, dpi=300)
#     plt.close()
#     print(f"Arrival & departure distribution plot for {day_name} saved to {dist_plot_path}")

# # 7. Interactive Map Visualization (Folium)
# print("Generating folium interactive map with sample trajectories...")
# campus_centroid = [boundary_geom.centroid.y, boundary_geom.centroid.x]
# m = folium.Map(location=campus_centroid, zoom_start=15, tiles="CartoDB positron")

# folium.GeoJson(
#     data=boundary_geom.__geo_interface__,
#     style_function=lambda x: {
#         'fillColor': '#1a73e8',
#         'color': '#1a73e8',
#         'weight': 2.5,
#         'fillOpacity': 0.08
#     },
#     name="IIT Delhi Campus Boundary"
# ).add_to(m)

# sample_visualization_agents = []
# # B.Tech
# bt_candidates = students_df[~students_df['Branch'].str.endswith('Z')]['Student ID'].tolist()
# if bt_candidates:
#     sample_visualization_agents.append((random.choice(bt_candidates), 'blue', 'B.Tech Student'))
# # PhD
# phd_candidates = students_df[students_df['Branch'].str.endswith('Z')]['Student ID'].tolist()
# if phd_candidates:
#     sample_visualization_agents.append((random.choice(phd_candidates), 'green', 'PhD Student'))
# # Professor
# prof_candidates = profs_df['Professor ID'].tolist()
# if prof_candidates:
#     sample_visualization_agents.append((random.choice(prof_candidates), 'red', 'Professor'))

# for agent_id, color, label in sample_visualization_agents:
#     home_lat, home_lon = agent_home[agent_id]
#     agent_schedules = schedule_dict.get(agent_id, {})
#     agent_speed = get_agent_speed(agent_id)
#     day_schedule = agent_schedules.get('M', [])
    
#     target_coords = [(home_lat, home_lon)] * 288
#     for activity in day_schedule:
#         start_step = max(0, min(287, activity['start_min'] // timestep_min))
#         end_step = max(0, min(287, activity['end_min'] // timestep_min))
#         for step in range(start_step, end_step):
#             target_coords[step] = (activity['lat'], activity['lon'])
            
#     actual_coords = list(target_coords)
#     step = 1
#     while step < 288:
#         prev_loc = actual_coords[step-1]
#         curr_loc = actual_coords[step]
#         if prev_loc != curr_loc:
#             path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
#             if path_points is None:
#                 actual_coords[step] = prev_loc
#                 step += 1
#                 continue
#             path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
#             duration_steps = max(1, int(math.ceil((path_dist / agent_speed) / (timestep_min * 60))))
#             start_transition_step = max(0, step - duration_steps)
#             interpolated = interpolate_coords(path_points, step - start_transition_step)
#             for t_idx, t_step in enumerate(range(start_transition_step, step)):
#                 actual_coords[t_step] = interpolated[t_idx]
#         step += 1
        
#     route_points = []
#     for lat, lon in actual_coords:
#         if not route_points or route_points[-1] != [lat, lon]:
#             route_points.append([lat, lon])
            
#     folium.PolyLine(
#         locations=route_points,
#         color=color,
#         weight=4,
#         opacity=0.8,
#         tooltip=f"{label} ({agent_id}) Monday Route"
#     ).add_to(m)
    
#     folium.CircleMarker(
#         location=[home_lat, home_lon],
#         radius=6,
#         color=color,
#         fill=True,
#         fill_color='white',
#         popup=f"{label} Home"
#     ).add_to(m)
    
#     destinations = set()
#     for activity in day_schedule:
#         destinations.add((activity['lat'], activity['lon']))
#     for d_lat, d_lon in destinations:
#         folium.CircleMarker(
#             location=[d_lat, d_lon],
#             radius=6,
#             color=color,
#             fill=True,
#             fill_color=color,
#             popup=f"{label} Activity Room"
#         ).add_to(m)

# folium.LayerControl().add_to(m)
# map_html_path = os.path.join(WORKSPACE_DIR, 'analysis_output', 'sample_trajectories_map.html')
# m.save(map_html_path)
# m.save(os.path.join(ARTIFACTS_DIR, 'sample_trajectories_map.html'))
# print(f"Sample trajectories interactive map saved to {map_html_path}")

print("Simulation engine pipeline executed successfully!")
