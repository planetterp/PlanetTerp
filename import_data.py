# * Only CSV files are allowed!
#
# * Ensure that the grade data you're importing has the grade cutoffs listed as:
#   A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W, OTHER
#
# * Remove column headers and check data for invalid entires (bottom of data)

import os
import csv

from django.core.wsgi import get_wsgi_application
from django.db.models import Q

# https://stackoverflow.com/a/43391786
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

from home.models import Professor, Course, Grade
from home.utils import semester_number

semester = input("Semester (Ex: spring 2021, winter 2020):")
semester = semester_number(semester)
filename = input("Filename: ")

filetype = filename.split('.')
if filetype[-1] != "csv":
    raise ValueError("File must be a .csv")


file = open(filename, newline=None)
reader = csv.reader(file, delimiter=',', quotechar="\"")

print("Importing data...")

def reject_DNE(type_):
    return f"{type_} doesn't exist"

def reject_missing(type_):
    return f"Missing {type_}"

def parse_course(name:str):
    if name is None:
        raise RuntimeError(reject_missing("Course"))

    department = name[:4]
    number = name[4:].strip()
    courses = Course.objects.filter(department=department, course_number=number)
    if not courses.exists():
        raise RuntimeError(reject_DNE("Course"))
    else:
        return courses.first()

def parse_professor(name:str):
    if name is None or name == "":
        return None

    names = name.strip().split(",")
    lastname = names[0]
    firstname = names[-1].strip().split()[0]
    professors = Professor.objects.filter(
        Q(name__istartswith=firstname) & Q(name__iendswith=lastname)
    )
    if professors.exists():
        return professors.first()

    raise RuntimeError(reject_DNE("Professor"))

grades = []
def add_grade(row):
    grades.append(
        Grade(
            semester = semester,
            course = parse_course(row[0]),
            section = row[1],
            professor = parse_professor(row[2]),
            num_students = row[3],
            a_plus = row[4],
            a = row[5],
            a_minus = row[6],
            b_plus = row[7],
            b = row[8],
            b_minus = row[9],
            c_plus = row[10],
            c = row[11],
            c_minus = row[12],
            d_plus = row[13],
            d = row[14],
            d_minus = row[15],
            f = row[16],
            w = row[17],
            other = row[18]
        )
    )


rejects = {
    "Missing Course": [],
    "Course doesn't exist": [],
    "Professor doesn't exist": []
}
for row in reader:
    try:
        add_grade(row)
    except RuntimeError as err:
        rejects[err.args[0]].append(row)
        continue

num_created = Grade.objects.bulk_create(grades)
print(f"Done (added {len(num_created)})")

if any(rejects):
    print("Exporting rejected data...")
    try:
        rejects_file = open("rejected_imports.csv", "w")
    except:
        os.system("touch rejected_imports.csv")
        rejects_file = open("rejected_imports.csv", "w")

    writer = csv.writer(rejects_file)
    for key in rejects.keys():
        if any(rejects[key]):
            writer.writerow([key])
        for row in rejects[key]:
            writer.writerow(row)

    print("**** Some data could not be imported and was stored in rejected_imports.csv ****\n")
