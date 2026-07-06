# visualize_occupancy_matplotlib.py
"""
Visualize IIT Delhi building occupancies over time of day for all weekdays (Monday to Friday)
using pure Matplotlib.

This script:
1. Loads the compiled building occupancy data from `building_occupancy_data.json`.
2. Identifies the most active buildings/hostels on campus.
3. Generates two premium visual representations:
   - A multi-panel heatmap showing the hourly density of top buildings for each weekday.
   - An occupancy curve chart tracking key campus building categories over 24 hours.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

WORKSPACE_DIR = "/Users/mohit/Documents/unisim"
DATA_JSON = os.path.join(WORKSPACE_DIR, "building_occupancy_data.json")
OUTPUT_HEATMAP = os.path.join(WORKSPACE_DIR, "campus_occupancy_heatmap.png")
OUTPUT_CURVES = os.path.join(WORKSPACE_DIR, "campus_occupancy_curves.png")

# Name mapping for cleaner visualization labels
name_aliases = {
    'lhc': 'Lecture Hall Complex',
    'LHC': 'Lecture Hall Complex',
    'DMS': 'Management Studies (DMS)',
    'dogra': 'Dogra Hall',
    'Dogra Hall': 'Dogra Hall',
    'ws': 'Central Workshop',
    'Central Workshop': 'Central Workshop',
    'main_building': 'Main Academic Block',
    'library': 'Central Library',
    'satpura': 'Satpura Hostel',
    'vindhyachal': 'Vindhyachal Hostel',
    'udaigiri': 'Udaigiri Hostel',
    'shivalik': 'Shivalik Hostel',
    'kailash': 'Kailash Hostel',
    'girnar': 'Girnar Hostel',
    'aravali': 'Aravali Hostel',
    'jwala': 'Jwala Hostel',
    'nilgiri': 'Nilgiri Hostel',
    'karakoram': 'Karakoram Hostel',
    'himadri': 'Himadri Hostel',
    'zanskar': 'Zanskar Hostel',
    'SDA': 'SDA Residence',
    'Type 4': 'Type IV Housing',
    'Nalanda Apt.': 'Nalanda Apartments',
    'chat': 'Chattpura (Off-Campus)'
}

def get_clean_name(name):
    return name_aliases.get(name, name)

def load_data():
    if not os.path.exists(DATA_JSON):
        raise FileNotFoundError(
            f"Compiled data not found at {DATA_JSON}. Please run `aggregate_occupancy.py` first."
        )
    with open(DATA_JSON) as f:
        return json.load(f)

def generate_heatmap(data):
    """Generate a 5-panel subplot heatmap of building occupancy for Monday-Friday using pure Matplotlib."""
    print("Generating building occupancy heatmaps...")
    
    occupancy = data["occupancy"]
    
    # 1. Identify top 25 buildings by peak occupancy to keep the plot readable
    building_peaks = {}
    for day in occupancy:
        for hour in occupancy[day]:
            for b_name, count in occupancy[day][hour].items():
                if "_" in b_name and not b_name.startswith("Type"):
                    continue
                building_peaks[b_name] = max(building_peaks.get(b_name, 0), count)
                
    top_buildings = sorted(building_peaks.keys(), key=lambda x: building_peaks[x], reverse=True)[:25]
    
    # Set up dark aesthetics
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 5, figsize=(24, 10), sharey=True)
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # We will track the final image plot to create a single synchronized colorbar
    last_im = None
    
    for i, day in enumerate(days):
        # Build matrix: building x hour
        matrix_data = []
        for b_name in top_buildings:
            row = []
            for hour in range(24):
                val = occupancy[day][str(hour)].get(b_name, 0)
                row.append(val)
            matrix_data.append(row)
            
        matrix_data = np.array(matrix_data)
        ax = axes[i]
        
        # Plot using Matplotlib's imshow with "inferno" colormap
        im = ax.imshow(matrix_data, cmap="inferno", aspect="auto", interpolation="nearest")
        last_im = im
        
        # Grid lines for clean boundaries
        ax.set_xticks(np.arange(24) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(top_buildings)) - 0.5, minor=True)
        ax.grid(which="minor", color="#111827", linestyle='-', linewidth=0.5)
        ax.tick_params(which="minor", size=0)
        
        # Label x-axis
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=8)
        ax.set_xlabel("Hour of Day", fontsize=11)
        
        # Label y-axis only on the leftmost panel
        if i == 0:
            ax.set_yticks(range(len(top_buildings)))
            ax.set_yticklabels([get_clean_name(b) for b in top_buildings], fontsize=9)
            ax.set_ylabel("Building / Zone Name", fontsize=12)
        else:
            ax.yaxis.set_visible(False)
            
        ax.set_title(day, fontsize=14, fontweight='bold', pad=10, color='#3b82f6')
        
    # Draw shared colorbar
    fig.subplots_adjust(right=0.92)
    cbar_ax = fig.add_axes([0.94, 0.15, 0.012, 0.7])
    fig.colorbar(last_im, cax=cbar_ax, label='Average Concurrent People')
    
    plt.suptitle("IIT Delhi Building Occupancy Timeline (Top 25 Buildings)", fontsize=18, fontweight='bold', y=0.98)
    plt.savefig(OUTPUT_HEATMAP, dpi=300)
    plt.close()
    print(f"Heatmap saved successfully to {OUTPUT_HEATMAP}")

def generate_curves(data):
    """Generate line curves tracking occupancy profiles for major zones."""
    print("Generating occupancy curves...")
    
    occupancy = data["occupancy"]
    
    # Define primary categories to aggregate
    categories = {
        "Academic complexes": ["LHC", "DMS", "main_building", "library", "Central Workshop", "Block 1", "Block 2", "Block 3", "Block 4", "Block 5", "Block 6"],
        "Student Hostels": ["satpura", "vindhyachal", "udaigiri", "shivalik", "kailash", "girnar", "aravali", "jwala", "nilgiri", "karakoram", "himadri", "zanskar"],
        "Residential Areas": ["SDA", "Type 4", "Nalanda Apt."]
    }
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    plt.style.use("dark_background")
    fig, axes = plt.subplots(5, 1, figsize=(12, 16), sharex=True)
    
    colors = {
        "Academic complexes": "#3b82f6",  # Blue
        "Student Hostels": "#f97316",     # Orange
        "Residential Areas": "#06b6d4"    # Cyan
    }
    
    for i, day in enumerate(days):
        ax = axes[i]
        
        # Calculate hourly sum for each category
        for cat_name, b_list in categories.items():
            hourly_sums = []
            for hour in range(24):
                hour_data = occupancy[day][str(hour)]
                cat_sum = sum(hour_data.get(b, 0) for b in b_list)
                hourly_sums.append(cat_sum)
                
            ax.plot(range(24), hourly_sums, label=cat_name, color=colors[cat_name], linewidth=2.5)
            
        ax.set_title(f"{day} Occupancy Profile", fontsize=12, fontweight='bold', color='#f3f4f6')
        ax.set_ylabel("Concurrent People", fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.15)
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45)
        
        if i == 0:
            ax.legend(loc="upper right", framealpha=0.8)
            
    axes[-1].set_xlabel("Hour of Day", fontsize=12)
    plt.suptitle("IIT Delhi Campus Occupancy Trends by Category", fontsize=16, fontweight='bold', y=0.99)
    plt.tight_layout()
    plt.savefig(OUTPUT_CURVES, dpi=300)
    plt.close()
    print(f"Curves saved successfully to {OUTPUT_CURVES}")

def main():
    data = load_data()
    generate_heatmap(data)
    generate_curves(data)
    print("All visualizations complete!")

if __name__ == "__main__":
    main()
