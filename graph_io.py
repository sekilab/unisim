import json
import networkx as nx
from shapely.geometry import shape, LineString, mapping as shapely_mapping

def save_graph_to_geojson(G, filepath):
    """
    Saves a NetworkX MultiDiGraph G to standard GeoJSON format (FeatureCollection),
    deduplicating bidirectional edges to show a single undirected segment per pathway.
    """
    features = []
    
    # 1. Export Nodes as Point features
    for node, data in G.nodes(data=True):
        lat = data.get("y")
        lon = data.get("x")
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "id": f"node_{node}",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "type": "node",
                "id": node,
                "name": data.get("name", "")
            }
        })
        
    # 2. Export Edges as LineString features (deduplicating bidirectional edges)
    seen_edges = set()
    for u, v, k, data in G.edges(keys=True, data=True):
        u_str, v_str = str(u), str(v)
        if u_str <= v_str:
            edge_key = (u, v, k)
        else:
            edge_key = (v, u, k)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        u_lat, u_lon = u_data.get("y"), u_data.get("x")
        v_lat, v_lon = v_data.get("y"), v_data.get("x")
        if None in (u_lat, u_lon, v_lat, v_lon):
            continue
            
        if "geometry" in data:
            geom_dict = shapely_mapping(data["geometry"])
        else:
            geom_dict = {
                "type": "LineString",
                "coordinates": [
                    [u_lon, u_lat],
                    [v_lon, v_lat]
                ]
            }
            
        features.append({
            "type": "Feature",
            "id": f"edge_{u}_{v}_{k}",
            "geometry": geom_dict,
            "properties": {
                "type": "edge",
                "u": u,
                "v": v,
                "key": k,
                "length": float(data.get("length", 0.0)),
                "highway": data.get("highway", "path")
            }
        })
        
    geojson_data = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": features
    }
    
    with open(filepath, "w") as f:
        json.dump(geojson_data, f, indent=2)

def load_graph_from_geojson(filepath):
    """
    Loads a custom GeoJSON format (FeatureCollection) into a NetworkX MultiDiGraph,
    re-creating bidirectional directed edges for routing from the undirected GeoJSON edges.
    """
    with open(filepath, "r") as f:
        geojson_data = json.load(f)
        
    G = nx.MultiDiGraph()
    G.graph["crs"] = "epsg:4326"
    
    # Pass 1: Add all nodes
    for feat in geojson_data["features"]:
        props = feat["properties"]
        if props.get("type") == "node":
            node_id = props["id"]
            try:
                node_id = int(node_id)
            except ValueError:
                pass
            lon, lat = feat["geometry"]["coordinates"]
            G.add_node(node_id, y=lat, x=lon, name=props.get("name", ""))
            
    # Pass 2: Add all edges in both directions (undirected -> directed MultiDiGraph representation)
    for feat in geojson_data["features"]:
        props = feat["properties"]
        if props.get("type") == "edge":
            u = props["u"]
            v = props["v"]
            k = props.get("key", 0)
            try:
                u = int(u)
            except ValueError:
                pass
            try:
                v = int(v)
            except ValueError:
                pass
            
            length = props.get("length", 0.0)
            highway = props.get("highway", "path")
            
            geom_obj = shape(feat["geometry"])
            if isinstance(geom_obj, LineString):
                geom_obj_rev = LineString(list(geom_obj.coords)[::-1])
            else:
                geom_obj_rev = geom_obj
                
            G.add_edge(u, v, key=k, length=length, highway=highway, geometry=geom_obj)
            G.add_edge(v, u, key=k, length=length, highway=highway, geometry=geom_obj_rev)
            
            # Infer missing node coordinates from geometry if they weren't explicitly defined
            geom = feat.get("geometry")
            if geom and "coordinates" in geom:
                coords = geom["coordinates"]
                if len(coords) >= 2:
                    # u coordinates are at coords[0] (lon, lat)
                    if "y" not in G.nodes[u] or "x" not in G.nodes[u]:
                        G.nodes[u]["x"] = coords[0][0]
                        G.nodes[u]["y"] = coords[0][1]
                    # v coordinates are at coords[-1] (lon, lat)
                    if "y" not in G.nodes[v] or "x" not in G.nodes[v]:
                        G.nodes[v]["x"] = coords[-1][0]
                        G.nodes[v]["y"] = coords[-1][1]
            
    connect_dead_ends(G, max_dist=20.0)
    connect_disconnected_components(G, max_dist=20.0)
    return G

def connect_dead_ends(G, max_dist=20.0):
    """
    Identifies dead-end nodes in G (undirected degree == 1) and connects them
    to the nearest node in the graph if the distance is <= max_dist meters.
    """
    # Convert G to undirected graph to check degrees
    U = nx.Graph(G)
    dead_ends = [node for node in U.nodes if U.degree(node) == 1]
    
    def dist_m(p1, p2):
        import math
        lat1, lon1 = p1
        lat2, lon2 = p2
        dy = (lat2 - lat1) * 111320.0
        dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
        return math.sqrt(dx*dx + dy*dy)
        
    connections_added = 0
    for d in dead_ends:
        # Node must have coordinates
        d_lat = G.nodes[d].get('y')
        d_lon = G.nodes[d].get('x')
        if d_lat is None or d_lon is None:
            continue
            
        d_coords = (d_lat, d_lon)
        neighbors = set(U.neighbors(d))
        
        closest_node = None
        min_dist = 999999.0
        
        for n in G.nodes:
            if n == d or n in neighbors:
                continue
            n_lat = G.nodes[n].get('y')
            n_lon = G.nodes[n].get('x')
            if n_lat is None or n_lon is None:
                continue
                
            dist = dist_m(d_coords, (n_lat, n_lon))
            if dist < min_dist:
                min_dist = dist
                closest_node = n
                
        if closest_node is not None and min_dist <= max_dist:
            # Add bidirectional edge
            G.add_edge(d, closest_node, key=0, length=min_dist, highway='connector')
            G.add_edge(closest_node, d, key=0, length=min_dist, highway='connector')
            U.add_edge(d, closest_node)  # Update undirected graph to prevent double-connecting
            connections_added += 1
            print(f"[graph_io] Connected dead-end node {d} to {closest_node} (distance: {min_dist:.2f}m)")
            
    if connections_added > 0:
        print(f"[graph_io] Automatically connected {connections_added} dead-end nodes within {max_dist}m.")

def connect_disconnected_components(G, max_dist=20.0):
    """
    Finds all connected components of the undirected version of G.
    For each component that is not the largest component, finds the closest
    pair of nodes (one in the small component, one in a different component)
    and connects them if the distance is <= max_dist meters.
    """
    def dist_m(p1, p2):
        import math
        lat1, lon1 = p1
        lat2, lon2 = p2
        dy = (lat2 - lat1) * 111320.0
        dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
        return math.sqrt(dx*dx + dy*dy)

    connections_added = 0
    while True:
        U = nx.Graph(G)
        comps = list(nx.connected_components(U))
        if len(comps) <= 1:
            break
            
        comps.sort(key=len, reverse=True)
        giant = comps[0]
        
        connection_made = False
        for comp in comps[1:]:
            closest_pair = None
            min_dist = 999999.0
            
            for u in comp:
                u_lat = G.nodes[u].get('y')
                u_lon = G.nodes[u].get('x')
                if u_lat is None or u_lon is None:
                    continue
                u_coords = (u_lat, u_lon)
                
                for v in G.nodes:
                    if v in comp:
                        continue
                    v_lat = G.nodes[v].get('y')
                    v_lon = G.nodes[v].get('x')
                    if v_lat is None or v_lon is None:
                        continue
                        
                    dist = dist_m(u_coords, (v_lat, v_lon))
                    if dist < min_dist:
                        min_dist = dist
                        closest_pair = (u, v)
                        
            if closest_pair is not None and min_dist <= max_dist:
                u, v = closest_pair
                G.add_edge(u, v, key=0, length=min_dist, highway='connector')
                G.add_edge(v, u, key=0, length=min_dist, highway='connector')
                print(f"[graph_io] Connected component node {u} to {v} (distance: {min_dist:.2f}m)")
                connection_made = True
                connections_added += 1
                break
                
        if not connection_made:
            break
            
    if connections_added > 0:
        print(f"[graph_io] Automatically connected {connections_added} disconnected components within {max_dist}m.")
