import os
import json
import osmnx as ox
import networkx as nx
import folium
from shapely.geometry import Point, shape

print("Loading data...")
WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
with open(os.path.join(WORKSPACE_DIR, 'data_source', 'iitd.json')) as f:
    geojson = json.load(f)

# Find boundary and map coordinates
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


# Compute bbox bounds of all agents/classrooms to download same graph G
import pandas as pd
students_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'student_data.csv'))
profs_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'professor_data.csv'))
schedule_df = pd.read_csv(os.path.join(WORKSPACE_DIR, 'data_source', 'schedule.csv'))

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

import graph_io
geojson_path = os.path.join(WORKSPACE_DIR, 'data_source', 'graph.geojson')

# Fast distance helper (must be defined first for use in both branches)
def get_distance_meters(p1, p2):
    import math
    lat1, lon1 = p1
    lat2, lon2 = p2
    dy = (lat2 - lat1) * 111320.0
    dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dx*dx + dy*dy)

if os.path.exists(geojson_path):
    print(f"Loading custom waypoint graph from {geojson_path}...")
    G = graph_io.load_graph_from_geojson(geojson_path)
    
    # Re-identify connected gate nodes for folium FeatureGroups visualization
    gate_lat, gate_lon = mapping.get('ks_gate', (28.5417095, 77.189291))
    inside_node, outside_node = None, None
    min_dist_in, min_dist_out = 999.0, 999.0
    for n in G.nodes:
        n_lat = G.nodes[n]['y']
        n_lon = G.nodes[n]['x']
        dist = get_distance_meters((gate_lat, gate_lon), (n_lat, n_lon))
        if dist < 30.0:
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
    else:
        dist_m = 0.0
                                      
    js_gate_lat, js_gate_lon = mapping.get('js_gate', (28.5470903, 77.1888363))
    js_inside_node, js_outside_node = None, None
    js_min_dist_in, js_min_dist_out = 999.0, 999.0
    js_gate_node_id = 99999902
    
    for n in G.nodes:
        if n == js_gate_node_id:
            continue
        n_lat = G.nodes[n]['y']
        n_lon = G.nodes[n]['x']
        dist = get_distance_meters((js_gate_lat, js_gate_lon), (n_lat, n_lon))
        if dist < 50.0:
            p = Point(n_lon, n_lat)
            if boundary_geom.contains(p):
                if dist < js_min_dist_in:
                    js_min_dist_in = dist
                    js_inside_node = n
            else:
                if dist < js_min_dist_out:
                    js_min_dist_out = dist
                    js_outside_node = n
                    
    if js_inside_node is not None and js_outside_node is not None:
        js_dist_in = get_distance_meters((js_gate_lat, js_gate_lon), (G.nodes[js_inside_node]['y'], G.nodes[js_inside_node]['x']))
        js_dist_out = get_distance_meters((js_gate_lat, js_gate_lon), (G.nodes[js_outside_node]['y'], G.nodes[js_outside_node]['x']))
    else:
        js_dist_in = 0.0
        js_dist_out = 0.0
else:
    print("Loading Walk network from OSMnx...")
    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type='walk')

    # Connect the KS gate (bridge the gap between inside and outside nodes near the gate)
    gate_lat, gate_lon = mapping.get('ks_gate', (28.5417095, 77.189291))
    inside_node, outside_node = None, None
    min_dist_in, min_dist_out = 999.0, 999.0
    for n in G.nodes:
        n_lat = G.nodes[n]['y']
        n_lon = G.nodes[n]['x']
        dist = get_distance_meters((gate_lat, gate_lon), (n_lat, n_lon))
        if dist < 30.0:
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
        print(f"Connected ks_gate: {inside_node} <-> {outside_node}")

    # Connect the JS gate (js_gate)
    js_gate_lat, js_gate_lon = mapping.get('js_gate', (28.5470903, 77.1888363))
    js_inside_node, js_outside_node = None, None
    js_min_dist_in, js_min_dist_out = 999.0, 999.0
    for n in G.nodes:
        n_lat = G.nodes[n]['y']
        n_lon = G.nodes[n]['x']
        dist = get_distance_meters((js_gate_lat, js_gate_lon), (n_lat, n_lon))
        if dist < 50.0:
            p = Point(n_lon, n_lat)
            if boundary_geom.contains(p):
                if dist < js_min_dist_in:
                    js_min_dist_in = dist
                    js_inside_node = n
            else:
                if dist < js_min_dist_out:
                    js_min_dist_out = dist
                    js_outside_node = n

    if js_inside_node is not None and js_outside_node is not None:
        js_gate_node_id = 99999902
        G.add_node(js_gate_node_id, y=js_gate_lat, x=js_gate_lon)
        js_dist_in = get_distance_meters((js_gate_lat, js_gate_lon), (G.nodes[js_inside_node]['y'], G.nodes[js_inside_node]['x']))
        js_dist_out = get_distance_meters((js_gate_lat, js_gate_lon), (G.nodes[js_outside_node]['y'], G.nodes[js_outside_node]['x']))
        G.add_edge(js_gate_node_id, js_inside_node, key=0, length=js_dist_in, highway='path')
        G.add_edge(js_inside_node, js_gate_node_id, key=0, length=js_dist_in, highway='path')
        G.add_edge(js_gate_node_id, js_outside_node, key=0, length=js_dist_out, highway='path')
        G.add_edge(js_outside_node, js_gate_node_id, key=0, length=js_dist_out, highway='path')
        print(f"Connected js_gate: {js_inside_node} <-> {js_gate_node_id} <-> {js_outside_node}")
        
    graph_io.connect_dead_ends(G, max_dist=20.0)
    graph_io.connect_disconnected_components(G, max_dist=20.0)
    print(f"Exporting Walk network to {geojson_path} for manual customization...")
    graph_io.save_graph_to_geojson(G, geojson_path)


print("Building map...")
m = folium.Map(location=[28.545, 77.19], zoom_start=15, tiles="cartodbpositron")

# Create Folium FeatureGroups
fg_edges = folium.FeatureGroup(name="OSM Walk Edges", show=True)
fg_nodes = folium.FeatureGroup(name="OSM Walk Nodes", show=True)
fg_ks_gate = folium.FeatureGroup(name="KS Gate Connection", show=True)
fg_js_gate = folium.FeatureGroup(name="JS Gate Connection", show=True)

# Add campus boundary to map
folium.GeoJson(
    boundary_geom.__geo_interface__,
    name="Campus Boundary (IITD)",
    style_function=lambda x: {'fillColor': 'green', 'color': 'green', 'weight': 2, 'fillOpacity': 0.05}
).add_to(m)

# Draw all edges in G
drawn_edges = set()
for u, v, k, data in G.edges(keys=True, data=True):
    pair = tuple(sorted([u, v]))
    if pair in drawn_edges:
        continue
    drawn_edges.add(pair)
    
    u_lat, u_lon = G.nodes[u]['y'], G.nodes[u]['x']
    v_lat, v_lon = G.nodes[v]['y'], G.nodes[v]['x']
    
    if (u == inside_node and v == outside_node) or (u == outside_node and v == inside_node):
        folium.PolyLine(
            locations=[[u_lat, u_lon], [v_lat, v_lon]],
            color="red",
            weight=5,
            opacity=1.0,
            tooltip=f"KS Gate Bridged Edge: {u} <-> {v} ({dist_m:.2f}m)"
        ).add_to(fg_ks_gate)
    elif u == js_gate_node_id or v == js_gate_node_id:
        seg_dist = js_dist_in if (u == js_inside_node or v == js_inside_node) else js_dist_out
        folium.PolyLine(
            locations=[[u_lat, u_lon], [v_lat, v_lon]],
            color="purple",
            weight=5,
            opacity=1.0,
            tooltip=f"JS Gate Bridged Edge: {u} <-> {v} ({seg_dist:.2f}m)"
        ).add_to(fg_js_gate)
    else:
        folium.PolyLine(
            locations=[[u_lat, u_lon], [v_lat, v_lon]],
            color="#7a7a7a",
            weight=2,
            opacity=0.6,
            tooltip=f"Walk Path: {u} -> {v} ({data.get('length', 0):.1f}m)"
        ).add_to(fg_edges)

# Draw all nodes in G
for n in G.nodes:
    n_lat = G.nodes[n]['y']
    n_lon = G.nodes[n]['x']
    
    p = Point(n_lon, n_lat)
    is_inside = boundary_geom.contains(p)
    
    if n in (inside_node, outside_node):
        role = "KS INSIDE Gate Node" if n == inside_node else "KS OUTSIDE Gate Node"
        folium.CircleMarker(
            location=[n_lat, n_lon],
            radius=8,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.8,
            popup=f"<b>{role}</b><br>ID: {n}<br>Lat: {n_lat:.6f}<br>Lon: {n_lon:.6f}"
        ).add_to(fg_ks_gate)
    elif n in (js_gate_node_id, js_inside_node, js_outside_node):
        if n == js_gate_node_id:
            role = "JS Gate Node (Bridging Point)"
        elif n == js_inside_node:
            role = "JS INSIDE Gate Node"
        else:
            role = "JS OUTSIDE Gate Node"
        folium.CircleMarker(
            location=[n_lat, n_lon],
            radius=8,
            color="purple",
            fill=True,
            fill_color="purple",
            fill_opacity=0.8,
            popup=f"<b>{role}</b><br>ID: {n}<br>Lat: {n_lat:.6f}<br>Lon: {n_lon:.6f}"
        ).add_to(fg_js_gate)
    else:
        color = "#1f77b4" if is_inside else "#ff7f0e"
        status = "Inside Campus" if is_inside else "Outside Campus (Neighborhood)"
        folium.CircleMarker(
            location=[n_lat, n_lon],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=f"<b>{status}</b><br>ID: {n}<br>Lat: {n_lat:.6f}<br>Lon: {n_lon:.6f}"
        ).add_to(fg_nodes)

# Add layer controls
fg_edges.add_to(m)
fg_nodes.add_to(m)
fg_ks_gate.add_to(m)
fg_js_gate.add_to(m)
folium.LayerControl().add_to(m)

map_path = os.path.join(WORKSPACE_DIR, 'analysis_output', 'graph_nodes_map.html')
m.save(map_path)
print(f"Map successfully saved to {map_path}")
