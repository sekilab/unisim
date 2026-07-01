import os
import re
import json
import math
import random
import pandas as pd
import numpy as np
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import HeatMapWithTime
from shapely.geometry import shape

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

print("Starting Heatmap Animation Generator...")

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
        mapping[name] = (coords[1], coords[0])
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

# 2. Load OSM walk network
print("Loading OSM Walk network...")
buffered_boundary = boundary_geom.buffer(0.005)
G = ox.graph_from_polygon(buffered_boundary, network_type='walk')

# Geodesic distance approximation
def get_distance_meters(p1, p2):
    lat1, lon1 = p1
    lat2, lon2 = p2
    dy = (lat2 - lat1) * 111320.0
    dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dx*dx + dy*dy)

# Shortest path lookups
node_cache = {}
def get_nearest_node(lat, lon):
    key = (round(lat, 6), round(lon, 6))
    if key not in node_cache:
        node_cache[key] = ox.distance.nearest_nodes(G, lon, lat)
    return node_cache[key]

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
            coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
            coords[0] = (start_lat, start_lon)
            coords[-1] = (end_lat, end_lon)
            path_coords_cache[pair_key] = coords
        except nx.NetworkXNoPath:
            path_coords_cache[pair_key] = [(start_lat, start_lon), (end_lat, end_lon)]
    return path_coords_cache[pair_key]

def interpolate_coords(path_coords, num_steps):
    if not path_coords:
        return []
    if len(path_coords) == 1 or num_steps <= 1:
        return [path_coords[0]] * num_steps
        
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

# 3. Choose sample agents
all_students = students_df['Student ID'].tolist()
all_profs = profs_df['Professor ID'].tolist()
all_agents = all_students + all_profs

# We use 100% of the population for the heat map density animation
sample_fraction = 1.0
sample_agents = random.sample(all_agents, int(len(all_agents) * sample_fraction))

agent_home = {}
for _, row in students_df.iterrows():
    agent_home[row['Student ID']] = (row['Home Latitude'], row['Home Longitude'])
for _, row in profs_df.iterrows():
    agent_home[row['Professor ID']] = (row['Home Latitude'], row['Home Longitude'])

# Index Monday schedules
monday_schedule = {}
for _, row in schedule_df.iterrows():
    if row['day'] != 'M':
        continue
    agent_id = row['agent_id']
    try:
        sh, sm_ = map(int, row['start_time'].split(':'))
        eh, em_ = map(int, row['end_time'].split(':'))
        start_min = sh * 60 + sm_
        end_min = eh * 60 + em_
    except Exception:
        continue
        
    if agent_id not in monday_schedule:
        monday_schedule[agent_id] = []
    monday_schedule[agent_id].append({
        'start_min': start_min,
        'end_min': end_min,
        'lat': row['room_lat'],
        'lon': row['room_lon']
    })

for agent_id in monday_schedule:
    monday_schedule[agent_id].sort(key=lambda x: x['start_min'])

# 4. Simulate Monday trajectories
print(f"Simulating Monday trajectories for {len(sample_agents)} sample agents...")
walking_speed_mps = 1.2
timestep_min = 5

# We will collect coordinates at 15-minute intervals (96 intervals per day)
# each interval is 3 steps of 5-minutes
heatmap_steps = 96
heatmap_data = [[] for _ in range(heatmap_steps)]
index_labels = []

for step in range(heatmap_steps):
    total_min = step * 15
    hh = total_min // 60
    mm = total_min % 60
    index_labels.append(f"{hh:02d}:{mm:02d}")

for agent_id in sample_agents:
    home_lat, home_lon = agent_home[agent_id]
    day_schedule = monday_schedule.get(agent_id, [])
    
    # 288 steps (5-minute timesteps)
    target_coords = [(home_lat, home_lon)] * 288
    for activity in day_schedule:
        start_step = max(0, min(287, activity['start_min'] // timestep_min))
        end_step = max(0, min(287, activity['end_min'] // timestep_min))
        for s in range(start_step, end_step):
            target_coords[s] = (activity['lat'], activity['lon'])
            
    actual_coords = list(target_coords)
    s_idx = 1
    while s_idx < 288:
        prev_loc = actual_coords[s_idx-1]
        curr_loc = actual_coords[s_idx]
        if prev_loc != curr_loc:
            path_points = get_shortest_path_coords(prev_loc[0], prev_loc[1], curr_loc[0], curr_loc[1])
            path_dist = sum(get_distance_meters(path_points[i-1], path_points[i]) for i in range(1, len(path_points)))
            duration_steps = max(1, int(math.ceil((path_dist / walking_speed_mps) / (timestep_min * 60))))
            start_transition_step = max(0, s_idx - duration_steps)
            interpolated = interpolate_coords(path_points, s_idx - start_transition_step)
            for t_idx, t_step in enumerate(range(start_transition_step, s_idx)):
                actual_coords[t_step] = interpolated[t_idx]
        s_idx += 1
        
    # Pick every 3rd step (corresponding to 15-minute intervals)
    for step in range(heatmap_steps):
        lat, lon = actual_coords[step * 3]
        # Add a tiny random jitter (approx +/- 10 meters) so overlapping agents spread out over building shapes
        jitter_lat = lat + random.uniform(-0.00008, 0.00008)
        jitter_lon = lon + random.uniform(-0.00008, 0.00008)
        heatmap_data[step].append([jitter_lat, jitter_lon, 0.01])

# 5. Build Folium HeatMapWithTime Map
print("Building Leaflet map with HeatMapWithTime...")
campus_centroid = [boundary_geom.centroid.y, boundary_geom.centroid.x]
m = folium.Map(location=campus_centroid, zoom_start=15, tiles="CartoDB dark_matter")

# Add campus boundary outline
folium.GeoJson(
    data=boundary_geom.__geo_interface__,
    style_function=lambda x: {
        'fillColor': '#ffffff',
        'color': '#ffffff',
        'weight': 1.5,
        'fillOpacity': 0.02
    },
    name="Campus Outline"
).add_to(m)

# Add HeatMapWithTime
hm = HeatMapWithTime(
    data=heatmap_data,
    index=index_labels,
    radius=8,  # Slightly smaller to resolve fine density clusters
    min_opacity=0.03,
    max_opacity=0.35,  # Lower opacity to prevent solid red saturation
    scale_radius=False,
    use_local_extrema=True,  # Scales heatmap locally per timestep rather than globally
    auto_play=True,
    max_speed=5,
    speed_step=1,
    position="bottomleft"
)
hm.add_to(m)

# Save map
workspace_map_path = os.path.join(WORKSPACE_DIR, 'campus_motion_heatmap.html')
artifacts_map_path = os.path.join(ARTIFACTS_DIR, 'campus_motion_heatmap.html')

m.save(workspace_map_path)
m.save(artifacts_map_path)

print(f"Heatmap animation successfully saved to: {workspace_map_path}")
