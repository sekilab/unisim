# Graph Report - unisim  (2026-07-16)

## Corpus Check
- 13 files · ~10,885,670 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 101 nodes · 123 edges · 12 communities (10 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3b317267`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- 3. Core Mathematical and Modeling Concepts
- graph_io.py
- unisim_extracted.py
- Student
- sim_engine_2t_0.2s_5m.py
- simulation_engine.py
- simulation_engine_1min_0.2_sampling.py
- aggregate_occupancy.py
- generate_heatmap_animation.py
- graphify.md
- graphify.md
- analyze_building_occupancy.py

## God Nodes (most connected - your core abstractions)
1. `Student` - 7 edges
2. `3. Core Mathematical and Modeling Concepts` - 7 edges
3. `assign_elective_courses()` - 5 edges
4. `UniSim: IIT Delhi Campus Mobility Simulation & Analytics Pipeline` - 5 edges
5. `2. Complete Execution Pipeline` - 5 edges
6. `main()` - 4 edges
7. `load_graph_from_geojson()` - 4 edges
8. `get_distance_meters()` - 3 edges
9. `get_shortest_path_coords()` - 3 edges
10. `connect_dead_ends()` - 3 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (12 total, 2 thin omitted)

### Community 0 - "3. Core Mathematical and Modeling Concepts"
Cohesion: 0.18
Nodes (10): 1. Directory Structure & Key Files, 2. Complete Execution Pipeline, 4. Key Database Schema, `schedule.csv`, Step 1: Build the Population and Schedules, Step 2: Route Walk Trajectories, Step 3: Generate the Play/Pause Motion Heatmap, Step 4: Run Building Occupancy Diagnostics (+2 more)

### Community 1 - "graph_io.py"
Cohesion: 0.22
Nodes (8): connect_dead_ends(), connect_disconnected_components(), load_graph_from_geojson(), Identifies dead-end nodes in G (undirected degree == 1) and connects them     to, Finds all connected components of the undirected version of G.     For each comp, Saves a NetworkX MultiDiGraph G to standard GeoJSON format (FeatureCollection),, Loads a custom GeoJSON format (FeatureCollection) into a NetworkX MultiDiGraph,, save_graph_to_geojson()

### Community 2 - "unisim_extracted.py"
Cohesion: 0.09
Nodes (12): assign_elective_courses(), assign_hul_courses(), assign_mandatory_courses(), build_elective_candidates(), build_student_timetable(), get_dept_prefixes(), Professor, Assigns courses based on batchnumber and looks up slots via Pandas. (+4 more)

### Community 3 - "Student"
Cohesion: 0.22
Nodes (7): generate_pg_students(), generate_phd_students(), generate_students(), Generates B.Tech students for years 1 to 4 with random groups based on the seat, Generates PG students for years 1 to 2 with random groups based on pg_curriculum, Generates PhD students for years 1 to duration with specific hostel rules., Student

### Community 4 - "sim_engine_2t_0.2s_5m.py"
Cohesion: 0.39
Nodes (5): get_distance_meters(), get_nearest_node(), get_shortest_path_coords(), get_snapped_coord(), interpolate_coords()

### Community 5 - "simulation_engine.py"
Cohesion: 0.39
Nodes (5): get_distance_meters(), get_nearest_node(), get_shortest_path_coords(), get_snapped_coord(), interpolate_coords()

### Community 7 - "simulation_engine_1min_0.2_sampling.py"
Cohesion: 0.48
Nodes (5): get_distance_meters(), get_nearest_node(), get_shortest_path_coords(), get_snapped_coord(), interpolate_coords()

### Community 8 - "aggregate_occupancy.py"
Cohesion: 0.29
Nodes (7): 1. Planar Distance Formula, 2. Path Interpolation, 3. Core Mathematical and Modeling Concepts, 3. Spatial Jittering (Heatmap Rendering), 4. Dynamic Elective Course Allocation, 5. Conditional Student Attendance Model, 6. Non-Teaching Staff & Duty Timetables

### Community 9 - "generate_heatmap_animation.py"
Cohesion: 0.53
Nodes (4): get_distance_meters(), get_nearest_node(), get_shortest_path_coords(), interpolate_coords()

### Community 16 - "analyze_building_occupancy.py"
Cohesion: 0.70
Nodes (4): classify_location(), load_agents(), load_schedules(), main()

## Knowledge Gaps
- **15 isolated node(s):** `graphify`, `Workflow: graphify`, `1. Directory Structure & Key Files`, `Step 1: Build the Population and Schedules`, `Step 2: Route Walk Trajectories` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `UniSim: IIT Delhi Campus Mobility Simulation & Analytics Pipeline` connect `3. Core Mathematical and Modeling Concepts` to `aggregate_occupancy.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `3. Core Mathematical and Modeling Concepts` connect `aggregate_occupancy.py` to `3. Core Mathematical and Modeling Concepts`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `Student` connect `Student` to `unisim_extracted.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `graphify`, `Workflow: graphify`, `1. Directory Structure & Key Files` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `unisim_extracted.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09333333333333334 - nodes in this community are weakly interconnected._