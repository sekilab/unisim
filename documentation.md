# UniSim: IIT Delhi Campus Mobility Simulation & Analytics Pipeline

UniSim is an agent-based campus mobility simulator designed to model the spatial-temporal trajectories of students (B.Tech, M.Tech, PhD) and faculty members across the IIT Delhi campus. The simulator converts daily academic timetables and demographic distributions into 5-minute sampling GPS coordinates routed over a pedestrian pathway network downloaded from OpenStreetMap.

---

## 1. Directory Structure & Key Files

The project contains the following core files:

```text
├── iitd.json                        # GeoJSON mapping campus boundary, hostels, gates, and academic buildings
├── offered courses.csv              # Course registry containing lecture time blocks, slots, and classroom rooms
├── student matrix phd.csv           # PG seat distributions per branch/department
├── Seat Matrix btech.csv            # UG seat distributions per branch/department
│
├── unisim_extracted.py              # STEP 1: Demographic generation and weekly schedule mapping
├── simulation_engine.py             # STEP 2: Walk network shortest-path routing & GPS trajectory interpolation
├── generate_heatmap_animation.py    # STEP 3: Folium/Leaflet time-lapse motion heatmap builder (Play/Pause)
├── analyze_building_occupancies.py  # STEP 4: Generalized hourly occupancy analyzer for specific buildings/days
│
├── student_data.csv                 # Generated agent metadata (hostel, coordinates, course slots)
├── professor_data.csv               # Generated faculty metadata (department, coordinates, work hours)
├── schedule.csv                     # Compiled weekly timetable schedule for all 11,945 agents
└── trajectory.csv                   # Output dataset: 17.2M rows of 5-minute spatial-temporal coordinate pings
```

---

## 2. Complete Execution Pipeline

To run the simulation from scratch and view the results, execute the following commands in order:

### Step 1: Build the Population and Schedules
Generates the student/faculty agents, allocates their homes (hostels or off-campus locations), parses their course enrollments, and outputs a daily scheduling matrix.
```bash
python3 unisim_extracted.py
```
* **Inputs:** `iitd.json`, `offered courses.csv`, `Seat Matrix btech.csv`, `student matrix phd.csv`
* **Outputs:** [student_data.csv](file:///Users/mohit/Documents/unisim/student_data.csv), [professor_data.csv](file:///Users/mohit/Documents/unisim/professor_data.csv), [schedule.csv](file:///Users/mohit/Documents/unisim/schedule.csv)

### Step 2: Route Walk Trajectories
Downloads the pedestrian walking network of the campus via `osmnx`, runs shortest-path routing, interpolates coordinate positions at 1.2 m/s walking speed for every 5-minute interval (Mon-Fri), and renders validation plots.
```bash
python3 simulation_engine.py
```
* **Inputs:** `iitd.json`, `student_data.csv`, `professor_data.csv`, `schedule.csv`
* **Outputs:** [trajectory.csv](file:///Users/mohit/Documents/unisim/trajectory.csv), [sample_trajectories_map.html](file:///Users/mohit/Documents/unisim/sample_trajectories_map.html) (interactive path visualizer), and screen plots of overall occupancy curves.

### Step 3: Generate the Play/Pause Motion Heatmap
Compiles Monday's trajectories for all 11,945 agents into a 5-minute interval Leaflet time-lapse heatmap with a play/pause timeline slider.
```bash
python3 generate_heatmap_animation.py
```
* **Inputs:** `iitd.json`, `student_data.csv`, `professor_data.csv`, `schedule.csv`
* **Outputs:** [campus_motion_heatmap.html](file:///Users/mohit/Documents/unisim/campus_motion_heatmap.html)

### Step 4: Run Building Occupancy Diagnostics
Runs a diagnostics check to count how many unique agents are present inside specific buildings (e.g., LHC, DMS, Academic Blocks) at each hour of the day.
```bash
# Analyze a specific day (e.g., Wednesday)
python3 analyze_building_occupancies.py Wednesday

# Analyze average daily occupancy across all weekdays (Monday-Friday)
python3 analyze_building_occupancies.py All
```
* **Inputs:** `iitd.json`, `trajectory.csv`
* **Outputs:** Renders interactive line plots on screen and prints a text-based hourly occupancy matrix.

---

## 3. Core Mathematical and Modeling Concepts

### 1. Planar Distance Formula
To keep computations fast, geodesic distances between coordinates $p_1 = (lat_1, lon_1)$ and $p_2 = (lat_2, lon_2)$ are calculated using a cosine-scaled flat-plane approximation:
$$dy = (lat_2 - lat_1) \times 111320.0$$
$$dx = (lon_2 - lon_1) \times 111320.0 \times \cos\left(\frac{lat_1 + lat_2}{2} \times \frac{\pi}{180}\right)$$
$$Distance = \sqrt{dx^2 + dy^2}$$

### 2. Path Interpolation
When traveling between locations, agents walk at a constant velocity of **1.2 m/s**. If the route distance is $D$, the commute duration is $T = \frac{D}{1.2}$ seconds. The engine shifts the agent's departure time backward by $T_{steps} = \lceil \frac{T}{300} \rceil$ steps to guarantee they arrive at their destination exactly on schedule. The position of the agent is linearly interpolated along the nodes of the graph for each intermediate 5-minute step.

### 3. Spatial Jittering (Heatmap Rendering)
To prevent thousands of agents from stacking on the exact same latitude/longitude coordinate point (which saturates heatmaps), the animation engine injects a random uniform spatial jitter:
$$lat_{jitter} = lat + U(-0.00008, 0.00008)$$
$$lon_{jitter} = lon + U(-0.00008, 0.00008)$$
This distributes the heat spots across the actual physical footprint of the buildings.

### 4. Dynamic Elective Course Allocation
To prevent students from having incomplete or empty schedules (which results in static agents), the engine maps elective placeholders (`PE`, `DE`, `OE`, `OC`, `XX`, `XXX`) to actual active courses from `offered courses.csv`:
* **Department Mapping:** Maps each student's branch/course code to its corresponding department prefixes (e.g. `CS1` / `CS5` $\rightarrow$ `CO`/`CS`, `EE1` $\rightarrow$ `EL`/`EE`, `PPM` $\rightarrow$ `SP`).
* **Departmental Electives (PE / DE / XX):** Filters offered courses that match the student's department prefix and academic level (UG vs. PG), randomly assigning one.
* **Open Electives (OE / OC):** Assigns an offered course from a different department to simulate inter-departmental learning.
* **Conflict Resolution:** Electives are only assigned if they do not introduce schedule slot collisions with the student's existing core courses.

---

## 4. Key Database Schema

### `schedule.csv`
Defines the target locations and timetables for B.Tech, M.Tech, PhDs, and Professors:
* `agent_id`: Unique identifier (e.g. `2024BB0001`, `PROF-CS-001`)
* `day`: Day code (`M`, `T`, `W`, `Th`, `F`)
* `slot`: Timetable block (e.g., `A`, `E`, `Work Hours`)
* `start_time` / `end_time`: 24-hour time range (e.g., `08:00`, `09:00`)
* `room`: Physical location label (e.g., `LH 108`, `DMS`, `Blocks`)
* `room_lat` / `room_lon`: Destination coordinates

### `trajectory.csv`
The high-fidelity spatial trace database:
* `agent_id`: Unique agent identifier
* `timestamp`: Date and 24-hour time (pings recorded at 5-minute sampling rates, e.g. `2026-07-06 08:35:00`)
* `lat`: Instantaneous Latitude coordinate
* `lon`: Instantaneous Longitude coordinate
