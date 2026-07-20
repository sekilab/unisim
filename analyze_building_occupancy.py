# analyze_building_occupancy.py
"""
Analyze IIT Delhi building occupancy at 30-minute intervals from 6 AM to 12 PM (noon)
and 6 AM to 12 AM (midnight) for LHC, combined blocks, hostels, and management buildings
using schedule.csv.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# Setup paths
WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
STUDENT_DATA_PATH = os.path.join(WORKSPACE_DIR, "student_data.csv")
PROF_DATA_PATH = os.path.join(WORKSPACE_DIR, "professor_data.csv")
STAFF_DATA_PATH = os.path.join(WORKSPACE_DIR, "staff_data.csv")
SCHEDULE_PATH = os.path.join(WORKSPACE_DIR, "schedule.csv")
OUTPUT_PLOT_PATH = os.path.join(WORKSPACE_DIR, "building_occupancy_analysis.png")

def load_agents():
    print("Loading agent home location details...")
    agent_info = {}
    
    # 1. Load students
    if os.path.exists(STUDENT_DATA_PATH):
        df = pd.read_csv(STUDENT_DATA_PATH)
        for _, row in df.iterrows():
            agent_info[row['Student ID']] = {
                'type': 'student',
                'home': row['Hostel']
            }
            
    # 2. Load professors
    if os.path.exists(PROF_DATA_PATH):
        df = pd.read_csv(PROF_DATA_PATH)
        for _, row in df.iterrows():
            agent_info[row['Professor ID']] = {
                'type': 'professor',
                'home': row['Locality']
            }
            
    # 3. Load staff
    if os.path.exists(STAFF_DATA_PATH):
        df = pd.read_csv(STAFF_DATA_PATH)
        for _, row in df.iterrows():
            agent_info[row['Staff ID']] = {
                'type': 'staff',
                'home': row['Locality']
            }
            
    print(f"Total agents loaded: {len(agent_info)}")
    return agent_info

def classify_location(loc_name, agent_type=None, home_loc=None):
    if not isinstance(loc_name, str):
        return None
    loc_upper = loc_name.strip().upper()
    
    # 1. LHC
    if 'LH ' in loc_upper or loc_upper == 'LHC' or 'LHC ' in loc_upper:
        return 'LHC'
        
    # 2. Hostels
    hostel_names = ['GIRNAR', 'NILGIRI', 'HIMADRI', 'SHIVALIK', 'ARAVALI', 'KAILASH', 'ZANSKAR', 
                     'VINDHYACHAL', 'KARAKORAM', 'JWALA', 'UDAIGIRI', 'KUMAON', 'SATPURA', 
                     'DRONAGIRI']
    if any(h in loc_upper for h in hostel_names) or loc_upper in hostel_names:
        return 'Hostels'
        
    # 3. Management Buildings
    if any(m in loc_upper for m in ['DMS', 'MANAGEMENT', 'BHARTI', 'SIT', 'SYNERGY']):
        return 'Management Buildings'
        
    # 4. Combined Blocks
    block_indicators = ['BLOCK', 'MAIN BUILDING', 'ACADEMIC COMPLEX', 'WORKSHOP', 'MATHEMATICS', 
                        'TEXTILE', 'MATERIAL SCIENCE', 'DH', 'DOD', 'WS', 'TX', 'ME', 'EE', 'AM', 'PH']
    if any(b in loc_upper for b in block_indicators) or loc_upper == 'ADMIN BUILDING':
        return 'Combined Blocks'
        
    # Check for Roman numerals at start of room name (e.g. III 336)
    tokens = loc_upper.split()
    if tokens:
        first_token = tokens[0]
        if first_token in ['I', 'II', 'III', 'IV', 'V', 'VI', 'IIA']:
            return 'Combined Blocks'
            
    # Fallback to home location if it is "HOME" or placeholder
    if loc_upper in ['HOME', 'NAN', 'TBA', '']:
        if home_loc:
            return classify_location(home_loc)
        elif agent_type == 'student':
            return 'Hostels'
            
    return None

def load_schedules():
    print("Loading schedule data...")
    schedule_map = defaultdict(list)
    
    if os.path.exists(SCHEDULE_PATH):
        df = pd.read_csv(SCHEDULE_PATH)
        for _, row in df.iterrows():
            agent_id = row['agent_id']
            day = row['day']
            
            # Parse times to minutes of day
            try:
                sh, sm = map(int, row['start_time'].split(':'))
                eh, em = map(int, row['end_time'].split(':'))
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                
                schedule_map[(agent_id, day)].append({
                    'start_min': start_min,
                    'end_min': end_min,
                    'room': row['room']
                })
            except Exception:
                continue
                
    # Sort schedules by start time
    for key in schedule_map:
        schedule_map[key].sort(key=lambda x: x['start_min'])
        
    print(f"Total schedules loaded: {len(schedule_map)} agent-day entries")
    return schedule_map

def main():
    agent_info = load_agents()
    schedule_map = load_schedules()
    
    # Define 30-minute intervals from 6 AM (360 mins) to 12 AM / Midnight (1440 mins)
    # 37 points (06:00 to 24:00 inclusive)
    time_steps = [360 + i * 30 for i in range(37)]
    time_labels = []
    for t in time_steps:
        h = t // 60
        m = t % 60
        period = "AM" if h < 12 or h == 24 else "PM"
        display_h = h if h <= 12 else h - 12
        if h == 24:
            display_h = 12
            period = "AM"
        time_labels.append(f"{display_h:02d}:{m:02d} {period}")
        
    categories = ['LHC', 'Combined Blocks', 'Hostels', 'Management Buildings']
    days = ['M', 'T', 'W', 'Th', 'F']
    days_names = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'Th': 'Thursday', 'F': 'Friday'}
    
    # Initialize occupancy tracker: occupancy[day][category] = array of counts for each step
    occupancy = {day: {cat: np.zeros(len(time_steps)) for cat in categories} for day in days}
    
    print("Running occupancy timeline calculation...")
    for day in days:
        print(f"  Processing {days_names[day]}...")
        for agent_id, info in agent_info.items():
            slots = schedule_map.get((agent_id, day), [])
            agent_type = info['type']
            home_loc = info['home']
            
            # Simple pointer to scan slots
            slot_idx = 0
            num_slots = len(slots)
            
            for t_idx, t_min in enumerate(time_steps):
                current_loc = home_loc
                
                # Find if any slot overlaps with current t_min
                while slot_idx < num_slots and slots[slot_idx]['end_min'] <= t_min:
                    slot_idx += 1
                    
                if slot_idx < num_slots and slots[slot_idx]['start_min'] <= t_min < slots[slot_idx]['end_min']:
                    current_loc = slots[slot_idx]['room']
                
                # Classify location
                cat = classify_location(current_loc, agent_type, home_loc)
                if cat in categories:
                    occupancy[day][cat][t_idx] += 1
                    
    # Average across all weekdays
    avg_occupancy = {cat: np.zeros(len(time_steps)) for cat in categories}
    for cat in categories:
        for day in days:
            avg_occupancy[cat] += occupancy[day][cat]
        avg_occupancy[cat] /= len(days)
        
    print("Creating visualizations...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    
    colors = {
        'LHC': '#ef4444',                  # Vibrant Red
        'Combined Blocks': '#3b82f6',      # Sleek Blue
        'Hostels': '#10b981',              # Emerald Green
        'Management Buildings': '#8b5cf6'  # Royal Purple
    }
    
    # 1. Plot & Save Average Weekday in ONE single plot
    plt.figure(figsize=(12, 6))
    for cat in categories:
        plt.plot(time_steps, avg_occupancy[cat], 
                 label=cat, color=colors[cat], marker='o', markersize=4, linewidth=2.5)
    plt.title("IIT Delhi Building Occupancy Curve (6:00 AM - 12:00 AM Midnight) - Average Weekday", fontsize=14, fontweight='bold', pad=15)
    plt.ylabel("Concurrent Population", fontsize=12)
    plt.xlabel("Time of Day", fontsize=12)
    plt.xticks(time_steps[::2], time_labels[::2], rotation=45)
    plt.legend(loc="upper right", framealpha=0.9, fontsize=10)
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT_PATH, dpi=300)
    plt.close()
    print(f"Successfully generated building occupancy curves and saved to {OUTPUT_PLOT_PATH}")
    
    # 2. Plot & Save Each Weekday Distinctively in ONE single plot per day
    for day in days:
        day_name = days_names[day]
        day_plot_path = os.path.join(WORKSPACE_DIR, f"building_occupancy_{day_name}.png")
        
        plt.figure(figsize=(12, 6))
        for cat in categories:
            plt.plot(time_steps, occupancy[day][cat], 
                     label=cat, color=colors[cat], marker='o', markersize=4, linewidth=2.5)
        plt.title(f"IIT Delhi Building Occupancy Curve (6:00 AM - 12:00 AM Midnight) - {day_name}", fontsize=14, fontweight='bold', pad=15)
        plt.ylabel("Concurrent Population", fontsize=12)
        plt.xlabel("Time of Day", fontsize=12)
        plt.xticks(time_steps[::2], time_labels[::2], rotation=45)
        plt.legend(loc="upper right", framealpha=0.9, fontsize=10)
        plt.tight_layout()
        plt.savefig(day_plot_path, dpi=300)
        plt.close()
        print(f"Successfully generated building occupancy curves and saved to {day_plot_path}")
    
    # Print summary statistics in console (using selected hourly points for readability)
    print("\n" + "="*50)
    print("OCCUPANCY SUMMARY (WEEKDAY AVERAGE)")
    print("="*50)
    print(f"{'Time':<12} | {'LHC':<8} | {'Blocks':<8} | {'Hostels':<8} | {'Management':<8}")
    print("-"*50)
    for t_idx in range(0, len(time_steps), 4): # show every 2 hours
        t_label = time_labels[t_idx]
        print(f"{t_label:<12} | {int(avg_occupancy['LHC'][t_idx]):<8} | "
              f"{int(avg_occupancy['Combined Blocks'][t_idx]):<8} | "
              f"{int(avg_occupancy['Hostels'][t_idx]):<8} | "
              f"{int(avg_occupancy['Management Buildings'][t_idx]):<8}")
    print("="*50)

if __name__ == "__main__":
    main()
