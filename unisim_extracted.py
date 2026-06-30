import pandas as pd
import numpy as np


sm=pd.read_csv('Seat Matrix btech.csv')
df=pd.read_csv('offered courses.csv')

phd_sm=pd.read_csv('student matrix phd.csv')


df = df[['Course Code','Slot Name','Lecture Time','Room']]
df = df.dropna(subset=['Room'])
df['Slot Name'].unique().tolist()


sm.head()

sm=sm[['Branch','Seats Per Year','Description']]
sm.head()

courses = {
    '1':['APL100','CML101','MTL100','MCP100','MCP101','NIN100','NEN110','NLN100'],

    '2AM1': ['MLL100', 'APL106', 'APL104', 'APL101', 'SBL100', 'APL103', 'COL106', 'MTL107', 'ELL201', 'CVL100', 'APL206'],
    '3AM1': ['APL203', 'APL205', 'AMP262', 'APL302', 'HUL2XX', 'APL207', 'APL331', 'APL321', 'APL311', 'OC1', 'APL405'],
    '4AM1': ['DE1', 'APL410', 'APL361', 'APL390', 'HUL2XX', 'DE2', 'APD411', 'DE3', 'DE4', 'OC3', 'OC4', 'OC2'],

    '2BB1': ['MLL100', 'CLL110', 'SBL100', 'BBL131', 'BBL132', 'BBL133', 'CLL251', 'CLL122', 'CLL231', 'CVL100', 'MTL102', 'HUL2XX'],
    '3BB1': ['BBL231', 'CLL252', 'CLP301', 'CLL261', 'BBP332', 'BBL331', 'HUL2XX', 'CLP302', 'BBL434', 'BBL432', 'BBL433', 'BBL431'],
    '4BB1': ['HUL3XX', 'OC1', 'BBL731', 'BED451', 'BBL732', 'BBL733', 'DE1', 'DE2', 'OC2', 'DE3', 'OC3'],

    '2CH1': ['CLL110', 'CLL111', 'CLL113', 'CML103', 'HUL2XX', 'CLL121', 'CLL122', 'CLL231', 'CLL251', 'SBL100', 'MLL100'],
    '3CH1': ['CLL252', 'CLL222', 'CLL331', 'CLL141', 'CLL261', 'CVL100', 'CLP301', 'CLL352', 'DE1', 'CLL271', 'CLL371', 'CLL361', 'CLP302', 'HUL2XX'],
    '4CH1': ['DE2', 'DE3/OC1', 'OC2', 'CLP303', 'CLD411', 'HUL2XX', 'OC1/DE3', 'DE4', 'OC3', 'HUL3XX'],

    '2CH7': ['CLL110', 'CLL111', 'HUL2XX', 'CLL113', 'CML103', 'CLL121', 'CLL122', 'CLL251', 'CLL231', 'SBL100', 'MLL100'],
    '3CH7': ['CLL252', 'CLL222', 'CLL331', 'CLL261', 'CLL141', 'CLP301', 'CVL100', 'CLL352', 'DE1', 'CLL371', 'CLL271', 'CLL361', 'HUL2XX', 'CLP302'],
    '4CH7': ['DE2', 'PE1', 'CLP303', 'PE2', 'OC1', 'CLL703', 'HUL2XX', 'PE3', 'DE3', 'HUL3XX', 'CLD880', 'CLL731', 'CLL733'],
    '5CH7': ['CLD881', 'PE4', 'OE1', 'CLD882'],

    '2CE1': ['CVL121', 'CVP121', 'CVL111', 'CVL141', 'APL107', 'APL108', 'HUL2XX', 'CVL222', 'CVP222', 'CVL242', 'CVP242', 'CVL261', 'CVP261', 'CVL281', 'CVP281', 'CVL100'],
    '3CE1': ['CVL243', 'CVP243', 'CVL245', 'CVL282', 'CVL321', 'CVP321', 'CVL341', 'SBL100', 'CVL212', 'CVL244', 'CVL342', 'CVP342', 'CVL381', 'OC1', 'HUL2XX'],
    '4CE1': ['DE1', 'DE2', 'DE3/OC2', 'CVP441', 'HUL3XX', 'CVD411', 'DE5', 'DE4', 'OC2/DE3', 'OC3'],

    '2CS1': ['COL202', 'COL215', 'COL106', 'MTL106', 'PYL102', 'COL226', 'COL216', 'ELL205', 'CVL100', 'HUL2XX', 'COP290'],
    '3CS1': ['COL333/DE1', 'COL334', 'COL351', 'SBL100', 'HUL2XX', 'COD3XX', 'COL362/DE1', 'DE2', 'COL331', 'OC1', 'COL352', 'COD490/492', 'MTLXXX', 'COL380'],
    '4CS1': ['OC2', 'OC3', 'DE3', 'HUL3XX'],

    '2CS5': ['COL202', 'COL215', 'COL106', 'PYLXXX', 'MTL106', 'COL226', 'ELL205', 'COL216', 'HUL2XX', 'CVL100', 'COP290'],
    '3CS5': ['COL333/DE1', 'COL334', 'COL351', 'SBL100', 'HUL2XX', 'COL362/DE1', 'COL331', 'COL352', 'MTLXXX', 'COL380'],
    '4CS5': ['DE2', 'DE3', 'COL703', 'OC1', 'PE1', 'COD891', 'COL726', 'HUL3XX', 'PE2', 'PE3', 'OC'],
    '5CS5': ['PE4', 'PE5', 'COD892', 'OC', 'COD893'],

    '2DD1': ['DDL211', 'DDL212', 'DDL213', 'DDL215', 'DDL214', 'DDP216', 'DDL217', 'DDL321', 'DDL222', 'DDL223', 'DDL224', 'DDD320', 'DDL225', 'DDL226', 'CLV100'],
    '3DD1': ['DDL311', 'DDL312', 'DDL313', 'DDL314', 'DDD310', 'DDL315', 'PE1', 'DDL228', 'DDD410', 'PE2', 'OE1', 'OE2'],
    '4DD1': ['DDL411', 'DDD510', 'OE3', 'PE4', 'PE5', 'DSD620', 'DDR422'],

    '2EE1': ['ELL202', 'COL106', 'ELL203', 'ELL211', 'ELL205', 'HUL2XX', 'ELL201', 'SBL100', 'ELL212', 'MTL106', 'ELL225', 'ELP203'],
    '3EE1': ['ELL304', 'ELL311', 'CVL100', 'ELL302', 'ELL305', 'ELP225', 'ELP212', 'MCL142', 'PYL102', 'ELL303', 'DE1', 'ELP305', 'ELP311', 'ELP302'],
    '4EE1': ['DE2', 'HUL2XX', 'OC1', 'ELD411', 'ELP303', 'DE3', 'OC3', 'OC2', 'HUL3XX'],

    '2EE3': ['ELL202', 'SBL100', 'ELL203', 'COL106', 'ELL205', 'ELL201', 'CVL100', 'ELL231', 'MTL106', 'ELL225', 'ELP203', 'HUL2XX'],
    '3EE3': ['ELL304', 'DE1', 'ELL302', 'ELL305', 'HUL2XX', 'ELP225', 'MCL142', 'ELL365', 'PYL102', 'ELL303', 'ELL332', 'ELP305', 'ELP302'],
    '4EE3': ['HUL2XX', 'ELL363', 'ELD431', 'OC1', 'ELP303', 'ELP332', 'DE2', 'DE3', 'OC2', 'HUL3XX', 'OC3'],

    '2ES1': ['MCL140', 'MLL100', 'CVL100', 'ESL371', 'ESL372', 'HUL2XX', 'ESL100', 'APL105', 'ESL200', 'ESL280', 'ESL263'],
    '3ES1': ['ESL373', 'ESL361', 'ESL390', 'ESL400', 'ESL261', 'ESL260', 'ESL220', 'ESL262', 'SBL100', 'ESL370', 'ESL341', 'ESL352', 'DE1', 'HUL2XX', 'MCL242', 'ESP260', 'ESP300', 'ESD400'],
    '4ES1': ['DE2', 'DE3', 'OC1', 'OC2', 'OC3', 'ESD406'],

    '2MS1': ['APL104', 'SBL100', 'MLL100', 'MLL103', 'HUL2XX', 'MLL102', 'MLL104', 'MLL202', 'MLL212', 'MLL242', 'MTL107'],
    '3MS1': ['CLL110', 'MLL251', 'MLL253', 'MLL213', 'MLL371', 'CVL100', 'DE1', 'DE2', 'MLL452', 'MLL372', 'MLS302', 'MLL264', 'MLP352', 'MLP354', 'HUL2XX'],
    '4MS1': ['MLP473', 'MLL181', 'MLD411', 'MLL262', 'DE3', 'OC1', 'HUL2XX', 'DE4', 'OC2', 'OC3', 'HUL3XX'],

    '2ME1': ['MLL100', 'APL106', 'APL104', 'MCL140', 'MCL111', 'SBL100', 'MCL131', 'MCL241', 'MTL108', 'HUL2XX', 'MCL201'],
    '3ME1': ['MCL261', 'MCL242', 'MCL231', 'MTL107', 'MCP231', 'MCL211', 'HUL2XX', 'MCL361', 'MCL431', 'MCL311', 'MCL212', 'DE1', 'MCD411', 'MCP301', 'OC1', 'CVL100', 'MCP331', 'MCP401'],
    '4ME1': ['DE2', 'HUL2XX', 'DE3', 'OC2', 'OC3', 'DE4', 'HUL3XX'],

    '2ME2': ['MLL100', 'APL104', 'MCL141', 'MCL111', 'HUL2XX', 'SBL100', 'MCL132', 'MTL108', 'MCL133', 'MCL201'],
    '3ME2': ['MCL261', 'MCL134', 'MTL107', 'MCL135', 'MCL211', 'MCP232', 'MCL262', 'MCL361', 'MCL212', 'MCP261', 'MCL311', 'MCP332', 'MCL136', 'MCL331', 'CVL100'],
    '4ME2': ['MCL431', 'MCD411', 'OC1', 'MCP361', 'HUL2XX', 'DE1', 'DE2', 'OC2', 'DE3', 'OC3', 'HUL3XX', 'DE4'],

    '2MT1': ['COL106', 'MTL180', 'PYL102', 'CVL100', 'HUL2XX', 'MTL104', 'MTL122', 'ELL201', 'MTL103', 'SBL100', 'MTP290'],
    '3MT1': ['MTL106', 'ELL305', 'MTL105', 'MTL107', 'MTL342', 'HUL2XX', 'MTL102', 'MTL782', 'MTL390', 'MTL411', 'ELP305', 'DE1'],
    '4MT1': ['MTL712', 'MTL783', 'DE2', 'MTL458', 'HUL3XX', 'OC1', 'OC2', 'OC3', 'DE3', 'DE4', 'MTD421'],

    '2MT6': ['COL106', 'MTL180', 'PYL102', 'CVL100', 'MTL104', 'HUL2XX', 'MTL122', 'ELL201', 'MTL103', 'SBL100', 'MTP290'],
    '3MT6': ['MTL106', 'ELL305', 'MTL105', 'MTL107', 'MTL342', 'HUL2XX', 'MTL102', 'MTL782', 'MTL390', 'MTL411', 'DE1', 'ELP305'],
    '4MT6': ['MTL712', 'MTL783', 'DE2', 'MTL458', 'OC1', 'HUL3XX', 'OC2', 'OE1', 'PE1', 'PE2', 'PE3', 'PE4', 'PE5', 'PE6', 'OE2'],
    '5MT6': ['MTD851', 'MTL781', 'MTL766', 'MTD852'],

    '2PH1': ['PYL127', 'PYL121', 'PYL123', 'PYL125', 'HUL2XX', 'PYP111', 'PYL122', 'PYL208', 'PYL206', 'ELL201', 'ESL350', 'PYP212'],
    '3PH1': ['PYL209', 'PYL205', 'ELL205', 'HUL2XX', 'PYP223', 'CML102', 'PYL202', 'PYL204', 'DE1', 'PYP224', 'SBL100'],
    '4PH1': ['DE2', 'OC1', 'HUL3XX', 'PYD411', 'CVL100', 'DE3', 'DE4', 'OC2', 'OC3']
}

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
with open('pg_curriculum.json', 'r', encoding='utf-8') as f:
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
                # Remaining 50% live in Hostels (Year 1: standard hostels, Year 2: Dronagiri)
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
                category = random.choices(['PQ', 'KS', 'JS', 'Standard'], weights=[10, 20, 30, 40], k=1)[0]
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
        for pattern in ['HUL', 'OC', 'DE', 'DC', 'OE', 'PE']:
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
    # Filter course_df for only HUL courses with rooms
    hul_df = course_df[course_df['Course Code'].str.startswith('HUL', na=False)]
    hul_candidates = hul_df[['Course Code', 'Slot Name']].drop_duplicates().values.tolist()

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
                for code, slot in hul_candidates:
                    if code.startswith(prefix) and slot not in student.slots_alloted:
                        valid_candidates.append((code, slot))

                if valid_candidates:
                    # Select one candidate randomly
                    chosen_code, chosen_slot = random.choice(valid_candidates)
                    student.add_course(chosen_code, chosen_slot, category='HUL')

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

    # Assign HUL courses randomly based on free slots
    assign_hul_courses(campus_students, curriculum_data, df)
    
    # Build timetables for the students
    for student in campus_students:
        build_student_timetable(student, df)


student_data_list=[]
for student in campus_students:
    student_data_list.append({
        'Student ID': student.student_id,
        'Batch Number': student.batchnumber,
        'Year': student.year,
        'Branch': student.course,
        'Hostel': student.hostel,
        'Group Number': student.group_number,
        'Total Courses': 1 if student.course.endswith('Z') else len(student.courses_alloted),
        'Courses Allotted': "Doctoral Research Work" if student.course.endswith('Z') else ", ".join(student.courses_alloted),
        'Slots Allotted': "Work Hours: 08:00-17:00 (Mon-Fri) | Lunch Break: 12:00-13:00" if student.course.endswith('Z') else ", ".join(student.slots_alloted)
    })

# Convert the list of dictionaries into a Pandas DataFrame
student_df = pd.DataFrame(student_data_list)

# Export the DataFrame to a CSV file inside the unisim folder
student_df.to_csv('student_data.csv', index=False)
print("Student data list saved to student_data.csv successfully!")

# Display the first few rows to verify
print(student_df)


#postgraduate data

