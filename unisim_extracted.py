import pandas as pd
import numpy as np


sm=pd.read_csv('data_source/Seat Matrix btech.csv')
df=pd.read_csv('data_source/offered courses.csv')

phd_sm=pd.read_csv('data_source/student matrix phd.csv')


df = df[['Course Code','Slot Name','Lecture Time','Room','Vacancy']]
df = df.dropna(subset=['Room'])
df['Slot Name'].unique().tolist()


sm.head()

sm=sm[['Branch','Seats Per Year','Description']]
sm.head()

import json
with open('data_source/btech_curriculum.json', 'r', encoding='utf-8') as f:
    courses = json.load(f)

import pandas as pd
import random
import re
import json

# ==========================================
# 1. Master Curriculum Data
# ==========================================
# Dynamically build curriculum_data for all branches from the courses dictionary
branch_map = {
    'BB': 'BB1',
    'CH': 'CH1',
    'CE': 'CE1',
    'CS1': 'CS1',
    'DD': 'DD1',
    'EE1': 'EE1',
    'EE3': 'EE3',
    'ES': 'ES1',
    'AM': 'AM1',
    'EP': 'PH1',
    'MS': 'MS1',
    'MT1': 'MT1',
    'ME1': 'ME1',
    'ME2': 'ME2',
    'CS5': 'CS5',
    'CH7': 'CH7',
    'MT6': 'MT6',
    'CM': 'CH1',
}

curriculum_data = {}
for branch in sm['Branch'].unique():
    # Year 1 courses
    curriculum_data[f"1{branch}"] = courses['1']
    
    # Year 2, 3, 4 courses
    map_code = branch_map.get(branch, branch + '1')
    for year in range(2, 6):
        course_key = f"{year}{map_code}"
        if course_key in courses:
            curriculum_data[f"{year}{branch}"] = courses[course_key]
        elif branch == 'TT':
            # Handle Textile Technology fallback using offered TXL/TXP courses
            tt_curriculum = {
                2: ['TXL212', 'TXL222', 'TXL232', 'TXL242', 'TXP222', 'TXP232', 'TXP242', 'SBL100'],
                3: ['TXL710', 'TXL712', 'TXL713', 'TXL731', 'TXL732', 'TXL747', 'HUL2XX'],
                4: ['TXD401', 'TXT800', 'TXL749', 'TXL753', 'OC1', 'DE1']
            }
            curriculum_data[f"{year}{branch}"] = tt_curriculum.get(year, [])

# Directly include dual degree and all courses keys into curriculum_data
for k, v in courses.items():
    if k != '1':
        curriculum_data[k] = v

# Load postgraduate curriculum data and populate curriculum_data
with open('data_source/pg_curriculum.json', 'r', encoding='utf-8') as f:
    pg_data = json.load(f)

for code, details in pg_data.items():
    semesters = details.get("semesters", {})
    curriculum_data[f"1{code}"] = semesters.get("I", []) + semesters.get("II", [])
    curriculum_data[f"2{code}"] = semesters.get("III", []) + semesters.get("IV", [])

# ==========================================
# 2. Core Student Class
# ==========================================
class Student:
    def __init__(self, student_id, course, year, hostel, group_number):
        # Demographics & Identifiers
        self.student_id = student_id
        self.course = course  # e.g., "CE", "CS1", "CYS"
        self.year = year
        self.hostel = hostel
        self.group_number = group_number

        # Auto-assigned batch number (e.g., "1CE", "2CYS")
        self.batchnumber = f"{self.year}{self.course}"

        # Course Tracking
        self.courses_alloted = []
        self.slots_alloted = []
        self.hul_course = None
        self.oc_course = None

        # Timetable
        self.timetable_with_location = {}

    def add_course(self, course_code, slot, category=None):
        if course_code not in self.courses_alloted:
            self.courses_alloted.append(course_code)
            self.slots_alloted.append(slot)

        if category == 'HUL':
            self.hul_course = course_code
        elif category == 'OC':
            self.oc_course = course_code

    def display_profile(self):
        return {
            "ID": self.student_id,
            "Batch": self.batchnumber,
            "Hostel": self.hostel,
            "Group": self.group_number,
            "Courses Registered": len(self.courses_alloted),
            "Course/Slot": list(zip(self.courses_alloted, self.slots_alloted))
        }

# ==========================================
# 3. Operations & Generators
# ==========================================
def generate_students(seat_matrix_df):
    """Generates B.Tech students for years 1 to 4 with random groups based on the seat matrix."""
    all_students = []
    current_year = 2024
    hostels = ['aravali', 'jwala', 'karakoram', 'nilgiri', 'kumaon', 'zanskar', 'shivalik', 'satpura', 'girnar', 'udaigiri', 'kailash', 'vindhyachal', 'himadri']
    weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]

    for _, row in seat_matrix_df.iterrows():
        branch = row['Branch']
        seats = int(row['Seats Per Year'])

        duration = 5 if branch in ["CS5", "CH7", "MT6"] or branch.endswith("5") or branch.endswith("7") or branch.endswith("6") else 4
        for year in range(1, duration + 1):
            entry_year = current_year - year + 1

            for i in range(1, seats + 1):
                student_id = f"{entry_year}{branch}{i:04d}"

                student = Student(
                    student_id=student_id,
                    course=branch,
                    year=year,
                    hostel=random.choices(hostels, weights=weights, k=1)[0],
                    group_number=random.randint(1, 4)
                )
                all_students.append(student)

    return all_students

def generate_pg_students(pg_data):
    """Generates PG students for years 1 to 2 with random groups based on pg_curriculum.json."""
    all_pg_students = []
    current_year = 2024
    hostels = ['aravali', 'jwala', 'karakoram', 'nilgiri', 'kumaon', 'zanskar', 'shivalik', 'satpura', 'girnar', 'udaigiri', 'kailash', 'vindhyachal', 'himadri']
    weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]

    for code, details in pg_data.items():
        seats = int(details.get("seats", 30))
        for year in [1, 2]:
            entry_year = current_year - year + 1
            for i in range(1, seats + 1):
                student_id = f"{entry_year}{code}{i:04d}"
                
                # Hostel allocation logic for PG students:
                # 50% live outside like PhD students (60% in JS, 40% in KS)
                # Remaining 50% live in Hostels (assigned to standard hostels)
                category = random.choices(['JS', 'KS', 'Standard'], weights=[30, 20, 50], k=1)[0]
                if category == 'Standard':
                    if year == 1:
                        hostel = random.choices(hostels, weights=weights, k=1)[0]
                    else:
                        hostel = "Dronagiri"
                else:
                    hostel = category
                    
                student = Student(
                    student_id=student_id,
                    course=code,
                    year=year,
                    hostel=hostel,
                    group_number=random.randint(1, 4)
                )
                all_pg_students.append(student)
                
    return all_pg_students

def generate_phd_students(phd_matrix_df, duration=5):
    """Generates PhD students for years 1 to duration with specific hostel rules."""
    all_phd_students = []
    current_year = 2024

    for _, row in phd_matrix_df.iterrows():
        branch = row['Branch']
        seats = int(row['Seats Per Year'])

        for year in range(1, duration + 1):
            entry_year = current_year - year + 1

            for i in range(1, seats + 1):
                student_id = f"{entry_year}{branch}{i:04d}"

                # Hostel allocation logic
                category = random.choices(['KS', 'JS', 'Standard'], weights=[20, 30, 50], k=1)[0]
                if category == 'Standard':
                    phd_standard_hostels = ['aravali', 'jwala', 'karakoram', 'nilgiri', 'kumaon', 'zanskar', 'shivalik', 'satpura', 'girnar', 'udaigiri', 'vindhyachal', 'sahadri']
                    phd_weights = [1]*11 + [3]
                    hostel = random.choices(phd_standard_hostels, weights=phd_weights, k=1)[0]
                else:
                    hostel = category

                student = Student(
                    student_id=student_id,
                    course=branch,
                    year=year,
                    hostel=hostel,
                    group_number=random.randint(1, 4)
                )
                all_phd_students.append(student)

    return all_phd_students

def assign_mandatory_courses(students_list, curriculum, course_df):
    """Assigns courses based on batchnumber and looks up slots via Pandas."""
    def is_excluded(course_code):
        for pattern in ['HUL', 'OC', 'DE', 'DC', 'OE', 'PE', 'XX', 'XXX']:
            if pattern in course_code:
                return True
        return False

    for student in students_list:
        batch = student.batchnumber  # e.g., '1CE', '2CE', '1CYS'

        if batch in curriculum:
            for course in curriculum[batch]:
                if not is_excluded(course):
                    # Look up the slot dynamically from the CSV DataFrame
                    matching_row = course_df[course_df['Course Code'] == course]

                    if not matching_row.empty:
                        slot = str(matching_row.iloc[0]['Slot Name'])
                    else:
                        slot = 'TBA'

                    student.add_course(course, slot)

def assign_hul_courses(students_list, curriculum, course_df):
    """Assigns HUL courses randomly based on free slots if HUL is mentioned in the student's curriculum."""
    # Filter course_df for HUL courses with rooms and lecture/seminar restriction
    hul_df = course_df[course_df['Course Code'].str.startswith('HUL', na=False)].dropna(subset=['Room']).copy()
    hul_df = hul_df[
        (~hul_df['Slot Name'].str.upper().isin(['TBA', 'NAN', ''])) &
        (~hul_df['Lecture Time'].str.upper().isin(['TBA', 'NAN', ''])) &
        (~hul_df['Room'].str.upper().isin(['TBA', 'NAN', '']))
    ]
    # Filter for lecture/seminar courses (3rd character of code must be 'L', 'V', or 'S')
    hul_df = hul_df[hul_df['Course Code'].str.len() >= 3]
    hul_df = hul_df[hul_df['Course Code'].str[2].isin(('L', 'V', 'S'))]
    
    # Get unique Course Code, Slot Name and its Vacancy
    # Group by code and slot and take the first Vacancy
    hul_candidates = hul_df.groupby(['Course Code', 'Slot Name'])['Vacancy'].first().reset_index()
    # Convert vacancy to float, default to 30.0
    hul_candidates['Vacancy'] = pd.to_numeric(hul_candidates['Vacancy'], errors='coerce').fillna(30.0)
    hul_candidates.loc[hul_candidates['Vacancy'] <= 0, 'Vacancy'] = 30.0
    
    hul_candidates_list = hul_candidates.values.tolist() # list of [code, slot, vacancy]

    for student in students_list:
        batch = student.batchnumber  # e.g., '1CE', '2CE'
        if batch not in curriculum:
            continue

        for course_placeholder in curriculum[batch]:
            if 'HUL' in course_placeholder:
                # Determine course level needed: 'HUL2' or 'HUL3'
                if 'HUL2' in course_placeholder:
                    prefix = 'HUL2'
                elif 'HUL3' in course_placeholder:
                    prefix = 'HUL3'
                else:
                    continue

                # Find all candidates of this level whose slot is NOT in the student's currently allotted slots
                valid_candidates = []
                for code, slot, vac in hul_candidates_list:
                    if code.startswith(prefix) and slot not in student.slots_alloted:
                        valid_candidates.append((code, slot, vac))

                if valid_candidates:
                    # Weighted random selection based on Vacancy
                    weights = [cand[2] for cand in valid_candidates]
                    chosen = random.choices(valid_candidates, weights=weights, k=1)[0]
                    student.add_course(chosen[0], chosen[1], category='HUL')

def get_dept_prefixes(branch):
    # Remove year prefix if any (e.g., '1CE' -> 'CE', '4CS5' -> 'CS5')
    branch = re.sub(r'^\d+', '', branch).upper()
    mapping = {
        'AM': ['APL', 'AMP', 'AMD', 'AML'],
        'AM1': ['APL', 'AMP', 'AMD', 'AML'],
        'BB': ['BBL', 'BBP', 'BBD', 'BBQ', 'BBV'],
        'BB1': ['BBL', 'BBP', 'BBD', 'BBQ', 'BBV'],
        'CH': ['CLL', 'CLP', 'CLD', 'CLQ'],
        'CH1': ['CLL', 'CLP', 'CLD', 'CLQ'],
        'CH7': ['CLL', 'CLP', 'CLD', 'CLQ'],
        'CE': ['CVL', 'CVP', 'CVD', 'CVC'],
        'CE1': ['CVL', 'CVP', 'CVD', 'CVC'],
        'CS': ['COL', 'COP', 'COD', 'COQ', 'COV', 'CON', 'COS'],
        'CS1': ['COL', 'COP', 'COD', 'COQ', 'COV', 'CON', 'COS'],
        'CS5': ['COL', 'COP', 'COD', 'COQ', 'COV', 'CON', 'COS'],
        'EE': ['ELL', 'ELP', 'EED', 'ELQ', 'ELS', 'ELV'],
        'EE1': ['ELL', 'ELP', 'EED', 'ELQ', 'ELS', 'ELV'],
        'EE3': ['ELL', 'ELP', 'EED', 'ELQ', 'ELS', 'ELV'],
        'ES': ['ESL', 'ESD', 'ESN', 'ESQ', 'ESS'],
        'ES1': ['ESL', 'ESD', 'ESN', 'ESQ', 'ESS'],
        'MS1': ['MLL', 'MLP', 'MLD', 'MLQ', 'MLV'],
        'ME': ['MCL', 'MCP', 'MCD', 'MCQ', 'MCV'],
        'ME1': ['MCL', 'MCP', 'MCD', 'MCQ', 'MCV'],
        'ME2': ['MCL', 'MCP', 'MCD', 'MCQ', 'MCV'],
        'MT': ['MTL', 'MTQ', 'MTD'],
        'MT1': ['MTL', 'MTQ', 'MTD'],
        'MT6': ['MTL', 'MTQ', 'MTD'],
        'PH': ['PYL', 'PYP', 'PYD', 'PYQ', 'PYV'],
        'PH1': ['PYL', 'PYP', 'PYD', 'PYQ', 'PYV'],
        'TT': ['TXL', 'TXP', 'TXD', 'TXQ', 'TXR', 'TXS', 'TXT'],
        'TT1': ['TXL', 'TXP', 'TXD', 'TXQ', 'TXR', 'TXS', 'TXT'],
        
        # PG Programs
        'CYS': ['COL', 'COP', 'COD', 'CON', 'COV'],
        'HCS': ['HSL', 'HSD', 'HSP'],
        'HES': ['HSL', 'HSD', 'HSP'],
        'MAS': ['MTL', 'MTD'],
        'PHS': ['PYL', 'PYP', 'PYD'],
        'BLS': ['BBL', 'BBP', 'BBD'],
        'DDS': ['DDL', 'DDP', 'DDR'],
        'HST': ['HSL', 'HSD', 'HSP'],
        'AMA': ['APL', 'AMP', 'AMD', 'AML'],
        'BEM': ['BBL', 'BBP', 'BBD'],
        'CHE': ['CLL', 'CLP', 'CLD'],
        'CEP': ['CVL', 'CVP', 'CVD'],
        'CES': ['CVL', 'CVP', 'CVD'],
        'CET': ['CVL', 'CVP', 'CVD'],
        'CEU': ['CVL', 'CVP', 'CVD'],
        'CEV': ['CVL', 'CVP', 'CVD'],
        'CEW': ['CVL', 'CVP', 'CVD'],
        'EEA': ['ELL', 'ELP', 'EED'],
        'EEE': ['ELL', 'ELP', 'EED'],
        'EEN': ['ELL', 'ELP', 'EED'],
        'EEP': ['ELL', 'ELP', 'EED'],
        'EES': ['ELL', 'ELP', 'EED'],
        'MSM': ['MSL', 'MSD'],
        'MSP': ['MSL', 'MSD'],
        'MEE': ['MCL', 'MCP', 'MCD'],
        'MEM': ['MCL', 'MCP', 'MCD'],
        'MEP': ['MCL', 'MCP', 'MCD'],
        'MET': ['MCL', 'MCP', 'MCD'],
        'PHA': ['PYL', 'PYP', 'PYD'],
        'PHM': ['PYL', 'PYP', 'PYD'],
        'TTE': ['TXL', 'TXP', 'TXD'],
        'TTC': ['TXL', 'TXP', 'TXD'],
        'TTF': ['TXL', 'TXP', 'TXD'],
        'CRF': ['CRL', 'CRP', 'CRD'],
        'AST': ['ASL', 'ASP', 'ASD'],
        'CTE': ['CTL', 'CTP', 'CTD'],
        'BMT': ['BML', 'BMD'],
        'JCS': ['JC'],
        'ESR': ['ESL', 'ESD'],
        'JIT': ['JI'],
        'JID': ['JI'],
        'JOP': ['OPL', 'OPD'],
        'JTM': ['JTL', 'JTD'],
        'JVD': ['JVL', 'JVD'],
        'JRB': ['JRL', 'JRD'],
        'PPM': ['SPL', 'SPD'],
        'MBA': ['MSL', 'MSD'],
    }
    if branch in mapping:
        return mapping[branch]
    short_branch = branch[:2]
    if short_branch in mapping:
        return mapping[short_branch]
    return []

def build_elective_candidates(course_df):
    ug_candidates = []
    pg_candidates = []
    
    clean_df = course_df.dropna(subset=['Course Code', 'Slot Name', 'Lecture Time', 'Room']).copy()
    clean_df = clean_df[
        (~clean_df['Slot Name'].str.upper().isin(['TBA', 'NAN', ''])) &
        (~clean_df['Lecture Time'].str.upper().isin(['TBA', 'NAN', ''])) &
        (~clean_df['Room'].str.upper().isin(['TBA', 'NAN', '']))
    ]
    
    for _, row in clean_df.iterrows():
        code = str(row['Course Code']).strip()
        slot = str(row['Slot Name']).strip()
        
        # Classroom and lecture/seminar/special course restriction
        # 3rd character must be 'L', 'V', or 'S'
        if len(code) >= 3 and code[2] in ('L', 'V', 'S'):
            try:
                vac_val = float(row.get('Vacancy', 30.0))
                if pd.isna(vac_val) or vac_val <= 0:
                    vac_val = 30.0
            except Exception:
                vac_val = 30.0
                
            match = re.search(r'\d', code)
            if match:
                level = int(match.group())
            else:
                level = 1
                
            candidate = (code, slot, vac_val)
            if level < 7:
                ug_candidates.append(candidate)
            else:
                pg_candidates.append(candidate)
                
    return ug_candidates, pg_candidates

def assign_elective_courses(students_list, curriculum, course_df):
    """Assigns electives (PE, DE, OE, OC) and department placeholders (COD3XX, etc.) dynamically based on student level and branch."""
    ug_candidates, pg_candidates = build_elective_candidates(course_df)
    
    def is_placeholder(item):
        for pattern in ['PE', 'DE', 'OE', 'OC', 'XX', 'XXX', 'HUL2', 'HUL3']:
            if pattern in item:
                return True
        return False
        
    for student in students_list:
        batch = student.batchnumber
        if batch not in curriculum:
            continue
            
        is_pg = student.course.endswith('Z') or student.course in pg_data
        candidates = pg_candidates if is_pg else ug_candidates
        dept_prefixes = get_dept_prefixes(student.course)
        
        for item in curriculum[batch]:
            if not is_placeholder(item):
                continue
            if 'HUL' in item:
                continue
                
            is_dept_elective = any(p in item for p in ['PE', 'DE', 'XX', 'XXX'])
            valid_candidates = []
            
            for code, slot, vac in candidates:
                if code in student.courses_alloted or slot in student.slots_alloted:
                    continue
                    
                has_dept_prefix = any(code.startswith(pref) for pref in dept_prefixes)
                
                if is_dept_elective:
                    if has_dept_prefix:
                        valid_candidates.append((code, slot, vac))
                else:
                    if not has_dept_prefix:
                        valid_candidates.append((code, slot, vac))
                        
            # Fallback if no specific open elective in other departments
            if not is_dept_elective and not valid_candidates:
                for code, slot, vac in candidates:
                    if code not in student.courses_alloted and slot not in student.slots_alloted:
                        valid_candidates.append((code, slot, vac))
                        
            if valid_candidates:
                # Weighted random selection based on Vacancy
                weights = [cand[2] for cand in valid_candidates]
                chosen = random.choices(valid_candidates, weights=weights, k=1)[0]
                student.add_course(chosen[0], chosen[1])

def build_student_timetable(student, course_dataframe):
    """Constructs a daily schedule dict based on the student's allocated courses."""
    timetable = {"M": {}, "T": {}, "W": {}, "Th": {}, "F": {}}

    # Filter the main DataFrame for only the courses this student is taking
    student_courses_df = course_dataframe[course_dataframe['Course Code'].isin(student.courses_alloted)]

    for _, row in student_courses_df.iterrows():
        course_code = row['Course Code']
        lecture_time = str(row['Lecture Time'])
        location = str(row['Room'])

        if lecture_time != 'nan' and lecture_time.strip():
            # Handle split schedules like "W 12:00-13:00 ,TF 17:00-18:00"
            time_blocks = lecture_time.split(',')

            for block in time_blocks:
                block = block.strip()
                if ' ' in block:
                    days_str, time_slot = block.split(' ', 1)
                    # Extract specific days using regex
                    days = re.findall(r'Th|M|T|W|F', days_str)

                    for day in days:
                        timetable[day][time_slot.strip()] = {
                            'course': course_code,
                            'location': location if location != 'nan' else 'TBA'
                        }

    # Save it to the student object
    student.timetable_with_location = timetable
    return timetable

# ==========================================
# 4. Execution Pipeline
# ==========================================
if __name__ == "__main__":
    # Generate B.Tech students based on the seat matrix
    campus_students = generate_students(sm)
    print(f"Generated {len(campus_students)} students total across all B.Tech branches.")

    # Generate PG students based on pg_curriculum.json
    pg_students = generate_pg_students(pg_data)
    print(f"Generated {len(pg_students)} students total across all PG branches.")
    campus_students.extend(pg_students)

    # Generate PhD students based on the PhD matrix
    phd_students = generate_phd_students(phd_sm, duration=5)
    print(f"Generated {len(phd_students)} students total across all PhD branches.")
    campus_students.extend(phd_students)

    # Assign the mandatory courses dynamically
    assign_mandatory_courses(campus_students, curriculum_data, df)

    # Assign elective courses (PE, DE, OE, OC)
    assign_elective_courses(campus_students, curriculum_data, df)

    # Assign HUL courses randomly based on free slots
    assign_hul_courses(campus_students, curriculum_data, df)
    
    # Build timetables for the students
    for student in campus_students:
        build_student_timetable(student, df)


    # Load iitd.json to map hostels and residential zones to coordinates
    with open('data_source/iitd.json') as f:
        geojson = json.load(f)

    # Build coordinates mapping and sub-points list from GeoJSON features
    sub_points = {
        'sda': [],
        'chat': [],
        'js': [],
        'ks': [],
        'type4': [],
        'type5': [],
        'staff': []
    }
    mapping = {}
    for feat in geojson['features']:
        props = feat.get('properties', {})
        name = props.get('name')
        if not name:
            continue
        gtype = feat['geometry']['type']
        coords = feat['geometry']['coordinates']
        
        if gtype == 'Point':
            coord = [coords[1], coords[0]]
            mapping[name] = coord
            
            # Check if this point belongs to a sub-point category (e.g. sda_1, type4_1_1)
            pid = props.get('@id')
            if pid in sub_points:
                sub_points[pid].append(coord)
        elif gtype in ('Polygon', 'MultiPolygon'):
            if gtype == 'Polygon':
                ring = coords[0]
            else:
                ring = coords[0][0]
            lats = [pt[1] for pt in ring if pt]
            lons = [pt[0] for pt in ring if pt]
            centroid = [sum(lats)/len(lats), sum(lons)/len(lons)]
            mapping[name] = centroid
            
            # Check if this polygon centroid belongs to a sub-point category (e.g. sda, type4, type5)
            pid = props.get('@id')
            if pid in sub_points and pid not in ('staff', 'type5', 'sda', 'chat', 'ks', 'js'):
                sub_points[pid].append(centroid)

    # Student hostel mapping to GeoJSON names or direct coordinates
    student_hostel_mapping = {
        'aravali': 'ara',
        'jwala': 'jwala',
        'karakoram': 'kara',
        'nilgiri': 'nil',
        'kumaon': 'kum',
        'zanskar': 'zans',
        'shivalik': 'shiv',
        'satpura': 'sat',
        'girnar': 'gir',
        'udaigiri': 'udai',
        'kailash': 'kailash',
        'vindhyachal': 'vind',
        'himadri': 'him',
        'sahadri': 'saha',
        'JS': 'js',
        'KS': 'ks',
        'Dronagiri': 'Dronagiri'
    }

    def get_student_coord(hostel):
        if hostel in student_hostel_mapping:
            mapped = student_hostel_mapping[hostel]
            # Randomly select from sub-building points if available (e.g. for js or ks)
            if mapped in sub_points and sub_points[mapped]:
                return random.choice(sub_points[mapped])
            if isinstance(mapped, list):
                return mapped
            return mapping.get(mapped, [28.545955, 77.18614])
        return [28.545955, 77.18614]

    student_data_list = []
    for student in campus_students:
        coord = get_student_coord(student.hostel)
        student_data_list.append({
            'Student ID': student.student_id,
            'Batch Number': student.batchnumber,
            'Year': student.year,
            'Branch': student.course,
            'Hostel': student.hostel,
            'Group Number': student.group_number,
            'Total Courses': 1 if student.course.endswith('Z') else len(student.courses_alloted),
            'Courses Allotted': "Doctoral Research Work" if student.course.endswith('Z') else ", ".join(student.courses_alloted),
            'Slots Allotted': "Work Hours: 08:00-17:00 (Mon-Fri) | Lunch Break: 12:00-13:00" if student.course.endswith('Z') else ", ".join(student.slots_alloted),
            'Home Latitude': coord[0],
            'Home Longitude': coord[1]
        })

    # Convert the list of dictionaries into a Pandas DataFrame
    student_df = pd.DataFrame(student_data_list)

    # Export the DataFrame to a CSV file inside the unisim folder
    student_df.to_csv('data_source/student_data.csv', index=False)
    print("Student data list saved to student_data.csv successfully!")

    # Display the first few rows to verify
    print(student_df.head())

    # ==========================================
    # 5. Professor Generation & Assignment
    # ==========================================
    def get_prof_coord(locality):
        if locality == 'SDA':
            if sub_points['sda']:
                return random.choice(sub_points['sda'])
            return mapping.get('SDA', [28.5488852, 77.1997977])
        elif locality == 'Type 4':
            if sub_points['type4']:
                return random.choice(sub_points['type4'])
            name = random.choice(['type4_1', 'type4_2'])
            return mapping.get(name, [28.546655, 77.184649])
        elif locality == 'Type 5':
            if sub_points['type5']:
                return random.choice(sub_points['type5'])
            return mapping.get('type5', [28.5437311, 77.197072])
        elif locality == 'Nalanda Apt.':
            return mapping.get('nalanda apt', [28.5459136, 77.1829884])
        elif locality == 'New Multi Story':
            name = random.choice(['tax', 'vik'])
            return mapping.get(name, [28.544161, 77.181316])
        elif locality == 'Chattpura':
            if sub_points['chat']:
                return random.choice(sub_points['chat'])
            return mapping.get('chat', [28.525859, 77.194400])
        return [28.545955, 77.18614]

    class Professor:
        def __init__(self, prof_id, branch, description, locality="", schedule="", home_lat=0.0, home_lon=0.0):
            self.prof_id = prof_id
            self.branch = branch
            self.description = description
            self.locality = locality
            self.schedule = schedule
            self.home_lat = home_lat
            self.home_lon = home_lon
            
        def to_dict(self):
            return {
                "Professor ID": self.prof_id,
                "Branch": self.branch,
                "Description": self.description,
                "Locality": self.locality,
                "Schedule": self.schedule,
                "Home Latitude": self.home_lat,
                "Home Longitude": self.home_lon
            }

    prof_dept_counts = {
        "All India JAM-2025 Organising": 1,
        "Central Library": 8,
        "Central Research Facility": 1,
        "Centre for Applied Research in Electronics": 16,
        "Centre for Atmospheric Sciences": 20,
        "Centre for Automotive Research and Tribology": 12,
        "Centre for Biomedical Engineering": 22,
        "Centre for Rural Development and Technology": 16,
        "Centre for Sensors, Instrumentation and Cyber Physical System Engineering": 10,
        "Computer Services Centre": 20,
        "Department of Applied Mechanics": 38,
        "Department of Biochemical Engineering and Biotechnology": 23,
        "Department of Chemical Engineering": 32,
        "Department of Chemistry": 38,
        "Department of Civil Engineering": 63,
        "Department of Computer Science and Engineering": 51,
        "Department of Design": 12,
        "Department of Electrical Engineering": 74,
        "Department of Energy Science and Engineering": 33,
        "Department of Humanities and Social Sciences": 49,
        "Department of Management Studies": 33,
        "Department of Materials Science and Engineering": 21,
        "Department of Mathematics": 37,
        "Department of Mechanical Engineering": 57,
        "Department of Physics": 59,
        "Department of Textile Technology": 27,
        "Office of Registrar": 1,
        "Optics and Photonics Centre": 9,
        "School of Biological Sciences": 22,
        "School of Public Policy": 14,
        "Transportation research and injury prevention - centre": 2,
        "TRIP Centre-Transportation Research and Injury Prevention Programme": 4,
        "Yardi school of artificial intelligence": 4
    }

    def get_acronym(name):
        clean_name = re.sub(r"\b(Department of|Centre for|School of|Office of)\b", "", name, flags=re.IGNORECASE).strip()
        words = [w for w in clean_name.split() if w.lower() not in ["and", "for", "of", "in", "the", "-", "centre", "department", "school"]]
        if len(words) == 1:
            return words[0][:3].upper()
        return "".join([w[0].upper() for w in words])

    localities = ["SDA", "Chattpura", "Type 5", "Type 4", "New Multi Story", "Nalanda Apt."]
    prof_weights = [44.5, 5.5, 12.5, 25.0, 6.25, 6.25]

    all_professors = []
    for dept, count in prof_dept_counts.items():
        acronym = get_acronym(dept)
        for i in range(1, count + 1):
            prof_id = f"PROF-{acronym}-{i:03d}"
            loc = random.choices(localities, weights=prof_weights, k=1)[0]
            s = "Work Hours: 08:00-17:00 (Mon-Fri) | Lunch Break: 12:00-13:00"
            coord = get_prof_coord(loc)
            prof = Professor(prof_id=prof_id, branch=acronym, description=dept, locality=loc, schedule=s, home_lat=coord[0], home_lon=coord[1])
            all_professors.append(prof)

    prof_df = pd.DataFrame([p.to_dict() for p in all_professors])
    prof_df.to_csv("data_source/professor_data.csv", index=False)
    print(f"Generated {len(prof_df)} professor records with coordinates saved to professor_data.csv")

    # ==========================================
    # 5.5 Non-Teaching Staff Generation
    # ==========================================
    from shapely.geometry import shape, Point

    class Staff:
        def __init__(self, staff_id, locality="", work_room="", schedule="", home_lat=0.0, home_lon=0.0):
            self.staff_id = staff_id
            self.locality = locality
            self.work_room = work_room
            self.schedule = schedule
            self.home_lat = home_lat
            self.home_lon = home_lon
            
        def to_dict(self):
            return {
                "Staff ID": self.staff_id,
                "Locality": self.locality,
                "Work Room": self.work_room,
                "Schedule": self.schedule,
                "Home Latitude": self.home_lat,
                "Home Longitude": self.home_lon
            }

    # Find the staff residence polygon from GeoJSON
    staff_polygon = None
    for feat in geojson['features']:
        if feat.get('properties', {}).get('@id') == 'staff' and feat['geometry']['type'] in ('Polygon', 'MultiPolygon'):
            staff_polygon = shape(feat['geometry'])
            break

    def get_staff_home_coord(poly):
        if poly is None:
            return [28.541725, 77.1929797]
        min_lon, min_lat, max_lon, max_lat = poly.bounds
        while True:
            lon = random.uniform(min_lon, max_lon)
            lat = random.uniform(min_lat, max_lat)
            point = Point(lon, lat)
            if poly.contains(point):
                return [lat, lon]

    # Staff Work Room Pools
    academic_blocks = [
        'Block 1', 'block 2', 'Block 3', 'Block 4', 'Block 5', 'Block 6',
        'SIT, IIT Delhi', 'Bharti School of Telecom Technology and Management',
        'Mathematics Department', 'Central Library', 'Admin Building', 'LHC',
        'Dogra Hall', 'DMS', 'Academic Complex East', 'Academic Complex West',
        'Synergy Building', 'Department of Material Science', 'Department of Textile Technology'
    ]
    
    hostels = [
        'ara', 'jwala', 'kara', 'nil', 'kum', 'zans', 'gir', 'udai', 'sat', 
        'vind', 'shiv', 'kailash', 'him', 'saha'
    ]
    
    all_buildings = academic_blocks + hostels + ['Central Workshop']

    all_staff = []
    for i in range(1, 491):
        staff_id = f"STAFF-{i:03d}"
        if sub_points.get('staff'):
            coord = sub_points['staff'][(i - 1) % len(sub_points['staff'])]
        else:
            coord = get_staff_home_coord(staff_polygon)
        locality = staff_id
        
        # TA/Adm (20% -> 98 members): only in academic blocks
        # Maintenance (80% -> 392 members): evenly in all campus buildings
        if i <= 98:
            work_room = random.choice(academic_blocks)
        else:
            work_room = random.choice(all_buildings)
            
        s_desc = "Work Hours: 08:00-18:00 (Mon-Fri) | Lunch Break: 12:00-14:00"
        
        staff_member = Staff(
            staff_id=staff_id,
            locality=locality,
            work_room=work_room,
            schedule=s_desc,
            home_lat=coord[0],
            home_lon=coord[1]
        )
        all_staff.append(staff_member)

    staff_df = pd.DataFrame([s.to_dict() for s in all_staff])
    staff_df.to_csv("data_source/staff_data.csv", index=False)
    print(f"Generated {len(staff_df)} non-teaching staff records with coordinates saved to staff_data.csv")

    # ==========================================
    # 6. Schedule Generation (Task 3)
    # ==========================================
    # Load offered courses for schedule details
    courses_df = pd.read_csv('data_source/offered courses.csv')
    course_dict = {}
    for _, row in courses_df.iterrows():
        code = str(row['Course Code']).strip()
        course_dict[code] = {
            'Lecture Time': str(row['Lecture Time']),
            'Room': str(row['Room'])
        }

    def parse_lecture_time(time_str):
        slots = []
        if not isinstance(time_str, str) or not time_str.strip() or time_str == 'nan':
            return slots
        
        blocks = time_str.split(',')
        for block in blocks:
            block = block.strip()
            if ' ' in block:
                days_str, time_slot = block.split(' ', 1)
                days = re.findall(r'Th|M|T|W|F', days_str)
                time_slot = time_slot.strip()
                
                time_parts = time_slot.split('-')
                if len(time_parts) == 2:
                    start_time, end_time = time_parts[0].strip(), time_parts[1].strip()
                else:
                    start_time, end_time = time_slot, time_slot
                
                for day in days:
                    slots.append({
                        'day': day,
                        'slot': time_slot,
                        'start_time': start_time,
                        'end_time': end_time
                    })
        return slots

    def get_building_by_branch(branch):
        if not branch or pd.isna(branch):
            return 'Main Building'
        b = str(branch).upper().strip()
        
        # Remove 'Z' suffix for PhD branches
        if b.endswith('Z') and len(b) > 2:
            b = b[:-1]
            
        # Design/Workshop
        if b in ('DD', 'DDS'):
            return 'Central Workshop'
            
        # Management Studies
        if b in ('MS', 'MSM', 'MSP', 'MBA', 'DMS'):
            return 'DMS'
            
        # Chemistry, Physics, Materials Science, CRF, Biomedical, AI
        if b in ('CY', 'CYS', 'EP', 'PHY', 'PH', 'PHS', 'PHA', 'PHM', 'MSE', 'CRF', 'BEM', 'BMT', 'YAI', 'AI', 'AIZ'):
            return 'Academic Complex East'
            
        # Mathematics
        if b in ('MAT', 'MAS', 'MT', 'MT1', 'MT6'):
            return 'Mathematics Department'
            
        # Textile
        if b in ('TT', 'TTE', 'TTC', 'TTF', 'TX'):
            return 'Department of Textile Technology'
            
        # Applied Mechanics, Civil Engineering
        if b in ('AM', 'AMA', 'CE', 'CEP', 'CES', 'CET', 'CEU', 'CEV', 'CEW'):
            return 'Block 4'
            
        # Biochemical, Biotech, Chemical
        if b in ('BEB', 'BB', 'BE', 'CHE'):
            if b == 'CHE':
                return 'block 2'
            return 'Block 1'
            
        # Chemical, Electrical, Computer Services Centre
        if b in ('CH', 'CHE', 'CM', 'EE', 'EE1', 'EE3', 'EEA', 'EEE', 'EEN', 'EEP', 'EES', 'SICPSE'):
            return 'block 2'
            
        # Computer Science, IT, Interdisciplinary
        if b in ('CS', 'CS1', 'CS5', 'CSE', 'JCS', 'JIT', 'JID', 'JVL', 'JRB', 'JIS', 'TRIP'):
            return 'SIT, IIT Delhi'
            
        # Telecom (Bharti School)
        if b in ('JTM', 'ARE'):
            return 'Bharti School of Telecom Technology and Management'
            
        # Mechanical, Design, Energy, Biotech, Public Policy, Biological Sciences
        if b in ('ME', 'ME1', 'ME2', 'MEE', 'MEM', 'MEP', 'MET', 'ES', 'ESR', 'BS', 'BLS', 'PP', 'PPM'):
            return 'Academic Complex West'
            
        # Humanities
        if b in ('HS', 'HSS', 'HCS', 'HES', 'HST'):
            return 'Block 5'
            
        # CARE, CART, CRDT
        if b in ('ART', 'CTE', 'RDT', 'RDZ'):
            return 'Block 3'
            
        if b in ('AS', 'AST', 'OP'):
            return 'Block 6'
            
        return 'Main Building'

    def get_room_coord(room):
        room = str(room).strip().upper()
        if not room or room in ('NAN', 'TBA', ''):
            return mapping.get('main_building', [28.5452719, 77.192312])
        
        if 'DOD' in room or 'WS' in room:
            return mapping.get('Central Workshop', [28.5435132, 77.1923034])
        elif 'DH' in room:
            return mapping.get('Dogra Hall', [28.5447903, 77.1920261])
        elif 'DMS' in room:
            return mapping.get('DMS', [28.5424921, 77.1830029])
        elif 'LH' in room:
            return mapping.get('LHC', [28.5430479, 77.1931553])
            
        # Match specific blocks based on Roman Numeral room prefixes
        if room.startswith('VI') or 'VI ' in room or 'VI_LT' in room:
            return mapping.get('Block 6', [28.5469632, 77.1908641])
        elif room.startswith('V') or 'V ' in room or 'V_LT' in room:
            return mapping.get('Block 5', [28.5466664, 77.1912254])
        elif room.startswith('IV') or 'IV ' in room or 'IV_LT' in room:
            return mapping.get('Block 4', [28.546407, 77.1917174])
        elif room.startswith('III') or 'III ' in room or 'III_LT' in room:
            return mapping.get('Block 3', [28.546046, 77.1920059])
        elif room.startswith('II') or 'II ' in room or 'II_LT' in room:
            return mapping.get('block 2', [28.5457203, 77.1921961])
        elif room.startswith('I') or 'I ' in room or 'I_LT' in room:
            return mapping.get('Block 1', [28.5458336, 77.1936198])
            
        # Match specific departments or subjects in room names
        if 'TX' in room:
            return mapping.get('Block 3', [28.546046, 77.1920059])
        elif 'ME' in room:
            return mapping.get('Block 3', [28.546046, 77.1920059])
        elif 'EE' in room:
            return mapping.get('block 2', [28.5457203, 77.1921961])
        elif 'AM' in room:
            return mapping.get('Block 4', [28.546407, 77.1917174])
        elif 'PH' in room:
            return mapping.get('Block 6', [28.5469632, 77.1908641])
            
        return mapping.get('main_building', [28.5452719, 77.192312])


    schedule_rows = []

    print("Generating B.Tech/M.Tech and PhD student schedules...")
    for _, row in student_df.iterrows():
        agent_id = row['Student ID']
        branch = row['Branch']
        
        if str(branch).endswith('Z'):
            # PhD Schedule: Mon-Fri: 08:00-12:00 and 13:00-17:00
            room = get_building_by_branch(branch)
            room_coord = mapping.get(room, mapping.get('main_building', [28.5452719, 77.192312]))
            

                
            for day in ['M', 'T', 'W', 'Th', 'F']:
                schedule_rows.append({
                    'agent_id': agent_id,
                    'day': day,
                    'slot': '08:00-12:00',
                    'start_time': '08:00',
                    'end_time': '12:00',
                    'room': room,
                    'room_lat': room_coord[0],
                    'room_lon': room_coord[1],
                    'activity': 'Research'
                })
                schedule_rows.append({
                    'agent_id': agent_id,
                    'day': day,
                    'slot': '13:00-17:00',
                    'start_time': '13:00',
                    'end_time': '17:00',
                    'room': room,
                    'room_lat': room_coord[0],
                    'room_lon': room_coord[1],
                    'activity': 'Research'
                })
        else:
            courses_str = str(row['Courses Allotted'])
            student_slots = []
            
            if courses_str and courses_str != 'nan':
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]
                for c in courses:
                    if c in course_dict:
                        lecture_time = course_dict[c]['Lecture Time']
                        room = course_dict[c]['Room']
                        room_coord = get_room_coord(room)
                        
                        parsed_slots = parse_lecture_time(lecture_time)
                        for ps in parsed_slots:
                            student_slots.append({
                                'agent_id': agent_id,
                                'day': ps['day'],
                                'slot': ps['slot'],
                                'start_time': ps['start_time'],
                                'end_time': ps['end_time'],
                                'room': room,
                                'room_lat': room_coord[0],
                                'room_lon': room_coord[1],
                                'activity': 'Class'
                            })
                            
            # Process attendance day-by-day
            if student_slots:
                slots_by_day = {d: [] for d in ['M', 'T', 'W', 'Th', 'F']}
                for s in student_slots:
                    slots_by_day[s['day']].append(s)
                    
                for day in ['M', 'T', 'W', 'Th', 'F']:
                    day_slots = slots_by_day[day]
                    if not day_slots:
                        continue
                    # Sort day_slots chronologically by start_time
                    day_slots.sort(key=lambda x: x['start_time'])
                    
                    prev_attended = None
                    prev_end_time = None
                    
                    for idx, slot_entry in enumerate(day_slots):
                        # Attendance decision
                        is_back_to_back = (prev_end_time is not None and slot_entry['start_time'] == prev_end_time)
                        
                        if is_back_to_back:
                            if prev_attended:
                                # 100% chance to attend if previous back-to-back class was attended
                                attend = True
                            else:
                                # 50% chance to attend if previous back-to-back class was skipped
                                attend = (random.random() < 0.50)
                        else:
                            # Reset to base probability of 75% for first class or after a break
                            attend = (random.random() < 0.75)
                            
                        if attend:
                            schedule_rows.append(slot_entry)
                            prev_attended = True
                        else:
                            # Redirect skipped class to Home location
                            skipped_entry = dict(slot_entry)
                            skipped_entry['room'] = row['Hostel']
                            skipped_entry['room_lat'] = float(row['Home Latitude'])
                            skipped_entry['room_lon'] = float(row['Home Longitude'])
                            skipped_entry['activity'] = 'Home'
                            schedule_rows.append(skipped_entry)
                            prev_attended = False
                            
                        prev_end_time = slot_entry['end_time']
            else:
                # Fallback for students with 0 scheduled class hours (e.g. M.Tech 2nd years doing Major Project/Thesis)
                room = get_building_by_branch(branch)
                room_coord = mapping.get(room, mapping.get('main_building', [28.5452719, 77.192312]))
                    
                for day in ['M', 'T', 'W', 'Th', 'F']:
                    schedule_rows.append({
                        'agent_id': agent_id,
                        'day': day,
                        'slot': '08:00-12:00',
                        'start_time': '08:00',
                        'end_time': '12:00',
                        'room': room,
                        'room_lat': room_coord[0],
                        'room_lon': room_coord[1],
                        'activity': 'Project'
                    })
                    schedule_rows.append({
                        'agent_id': agent_id,
                        'day': day,
                        'slot': '13:00-17:00',
                        'start_time': '13:00',
                        'end_time': '17:00',
                        'room': room,
                        'room_lat': room_coord[0],
                        'room_lon': room_coord[1],
                        'activity': 'Project'
                    })

    print("Generating professor schedules...")
    for _, row in prof_df.iterrows():
        agent_id = row['Professor ID']
        branch = row['Branch']
        
        room = get_building_by_branch(branch)
        room_coord = mapping.get(room, mapping.get('main_building', [28.5452719, 77.192312]))
            
        for day in ['M', 'T', 'W', 'Th', 'F']:
            schedule_rows.append({
                'agent_id': agent_id,
                'day': day,
                'slot': '08:00-12:00',
                'start_time': '08:00',
                'end_time': '12:00',
                'room': room,
                'room_lat': room_coord[0],
                'room_lon': room_coord[1],
                'activity': 'Work'
            })
            schedule_rows.append({
                'agent_id': agent_id,
                'day': day,
                'slot': '13:00-17:00',
                'start_time': '13:00',
                'end_time': '17:00',
                'room': room,
                'room_lat': room_coord[0],
                'room_lon': room_coord[1],
                'activity': 'Work'
            })
    print("Generating non-teaching staff schedules...")
    for idx, row in staff_df.iterrows():
        agent_id = row['Staff ID']
        room = row['Work Room']
        room_coord = mapping.get(room, mapping.get('main_building', [28.5452719, 77.192312]))
        
        # TA/Adm (20% -> 98 members): index 0 to 97
        # Maintenance Shift 1 (40% -> 196 members): index 98 to 293
        # Maintenance Shift 2 (40% -> 196 members): index 294 to 489
        if idx < 98:
            slots = [
                ('09:00-12:00', '09:00', '12:00'),
                ('13:00-18:00', '13:00', '18:00')
            ]
        elif idx < 294:
            slots = [
                ('08:00-14:00', '08:00', '14:00')
            ]
        else:
            slots = [
                ('14:00-20:00', '14:00', '20:00')
            ]
            
        for day in ['M', 'T', 'W', 'Th', 'F']:
            for slot_label, start_t, end_t in slots:
                schedule_rows.append({
                    'agent_id': agent_id,
                    'day': day,
                    'slot': slot_label,
                    'start_time': start_t,
                    'end_time': end_t,
                    'room': room,
                    'room_lat': room_coord[0],
                    'room_lon': room_coord[1],
                    'activity': 'Duty'
                })


    schedule_df = pd.DataFrame(schedule_rows)
    schedule_df.to_csv('data_source/schedule.csv', index=False)
    print(f"Schedule table with {len(schedule_df)} entries saved to schedule.csv successfully!")
