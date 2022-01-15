# DO NOT RUN THIS SCRIPT YOURSELF

import os
import web
from django.core.wsgi import get_wsgi_application
from planetterp.config import USER, PASSWORD

# https://stackoverflow.com/a/43391786
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

from home.models import *

web.config.debug = False
db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')

def _instantiate(model, row, mapping):
    kwargs = {}
    for django_name, value in mapping.items():
        if isinstance(value, str):
            kwargs[django_name] = row[value]
        elif callable(value):
            kwargs[django_name] = value(row)
        else:
            kwargs[django_name] = value

    return model(**kwargs)

def _create(model, row, mapping):
    instance = _instantiate(model, row, mapping)
    instance.save()

def _create_table(table, model, mapping):
    objs = {}
    for row in db.select(table):
        id_ = row["id"]

        # because of bad design decisions in the original database, we have a
        # dummy user with a pk of 0 that we need to ignore
        # because of bad design decisions in the original database, we have
        # dummy users with pk of 0 and -1 that we need to ignore
        if table == "users" and id_ <= 0:
            continue

        obj = _instantiate(model, row, mapping)
        objs[id_] = obj

    # can't bulk create or we won't be able to use these objects in foreign keys
    # later
    for obj in objs.values():
        obj.save()
    return objs

def _foreign_key(objects, row, name, nullable=False):
    id_ = row[name]
    if id_ is None and nullable:
        return None
    return objects[id_]

def migrate_courses():
    print("  Migrating courses...")

    mapping = {
        "department": "department",
        "course_number": "course_number",
        "created_at": "created",
        "title": "title",
        "credits": "credits",
        "description": "description",
    }

    courses = _create_table("courses", Course, mapping)
    return courses

def migrate_professors():
    print("  Migrating professors...")

    def _type(row):
        return Professor.Type.PROFESSOR if row["type"] == 0 else Professor.Type.TA
    def _status(row):
        mapping = {
            -1: Professor.Status.REJECTED,
            0: Professor.Status.PENDING,
            1: Professor.Status.VERIFIED,
        }
        return mapping[row["verified"]]

    def _name(row):
        split_name = str(row["name"]).split(" ")
        return " ".join([n for n in split_name if not n.isspace() and n != '']).strip()

    mapping = {
        "name": _name,
        "slug": "slug",
        "created_at": "created",
        "type": _type,
        "status": _status
    }
    return _create_table("professors", Professor, mapping)

def link_courses_and_professors(courses, professors):
    print("  Linking courses and professors...")

    for row in db.select("professor_courses"):
        professor = professors[row["professor_id"]]
        course = courses[row["course_id"]]
        recent_semester = row["recent_semester"]
        through = {
            "recent_semester": recent_semester
        }
        course.professors.add(professor, through_defaults=through)

def migrate_users():
    print("  Migrating users...")

    def _send_review_email(row):
        val = row["send_review_email"]
        return False if val is None or str(row["email"]).isspace() else bool(val)

    def _email(row):
        return None if str(row["email"]).isspace() else row['email']

    mapping = {
        "send_review_email": _send_review_email,
        "username": "username",
        "password": "password",
        "email": _email,
        "is_staff": "is_admin",
        "created_at": "created"
    }
    return _create_table("users", User, mapping)

def migrate_reviews(users, courses, professors):
    print("  Migrating reviews...")

    ourumd_users = {}
    for row in db.select("reviews", where="reviewer_id = -1 AND from_ourumd = 1"):
        # from ourumd, create new user
        username = row["reviewer_name"]

        # ...unless a user by that name already exists
        if username in ourumd_users:
            continue

        user = User.objects.create_ourumd_user(username)
        ourumd_users[username] = user

    def _user(row):
        if row["reviewer_id"] == 0:
            return None
        if row["reviewer_name"] in ourumd_users:
            return ourumd_users[row["reviewer_name"]]
        return _foreign_key(users, row, "reviewer_id")

    def _status(row):
        mapping = {
            -1: Review.Status.REJECTED,
            0: Review.Status.PENDING,
            1: Review.Status.VERIFIED,
        }
        return mapping[row["verified"]]

    def _anonymous(row):
        return row['reviewer_name'].lower() == "anonymous"

    mapping = {
        "professor": lambda row: _foreign_key(professors, row, "professor_id"),
        "course": lambda row: _foreign_key(courses, row, "course_id", True),
        "user": _user,
        "updater": lambda row: _foreign_key(users, row, "updated_by", True),
        "content": "review",
        "rating": "rating",
        "grade": "expected_grade",
        "status": _status,
        "anonymous": _anonymous,
        "from_ourumd": "from_ourumd",
        "created_at": "created"
    }
    return _create_table("reviews", Review, mapping)

def migrate_grades(courses, professors):
    print("  Migrating grades...")

    mapping = {
        "course": lambda row: _foreign_key(courses, row, "course_id"),
        "professor": lambda row: _foreign_key(professors, row, "professor_id", True),
        "semester": "semester",
        "section": "section",
        "num_students": "num_students",
        "a_plus": "APLUS",
        "a": "A",
        "a_minus": "AMINUS",
        "b_plus": "BPLUS",
        "b": "B",
        "b_minus": "BMINUS",
        "c_plus": "CPLUS",
        "c": "C",
        "c_minus": "CMINUS",
        "d_plus": "DPLUS",
        "d": "D",
        "d_minus": "DMINUS",
        "f": "F",
        "w": "W",
        "other": "OTHER"
    }
    return _create_table("grades", Grade, mapping)

def migrate_geneds(courses):
    print("  Migrating geneds...")

    mapping = {
        "name": "gened",
        "course": lambda row: _foreign_key(courses, row, "course_id"),
        "created_at": "created"
    }

    return _create_table("geneds", Gened, mapping)

def migrate_sections(courses):
    print("  Migrating sections...")

    def _active(row):
        val = row['active']
        return bool(val)

    mapping = {
        "id": "id",
        "semester": "semester",
        "section_number": "section_number",
        "seats": "seats",
        "available_seats": "available_seats",
        "waitlist": "waitlist",
        "active": _active,
        "created_at": "created",
        "course": lambda row: _foreign_key(courses, row, "course_id")
    }
    return _create_table("sections", Section, mapping)

def link_sections_and_professors(professors, sections):
    print("  Linking sections and professors...")

    for row in db.select("sections"):
        section = sections[row["id"]]
        professor_ids = str(row["professor_ids"]).split(",")
        for id_ in professor_ids:
            # sections.professor_ids use 0 to represent no professor so try to
            # get a professor by the id or use None instead
            try:
                professor = professors[int(id_)]
            except KeyError:
                professor = None

            section.professors.add(professor)

def migrate_section_meetings(sections):
    print("  Migrating section meetings...")

    def _building(row):
        val = row['building']
        return None if not val or val == '' else val

    mapping = {
        "section": lambda row: _foreign_key(sections, row, "section_id"),
        "days": "days",
        "start_time": "start_time",
        "end_time": "end_time",
        "building": _building,
        "room": "room",
        "type": "type",
        "created_at": "created"
    }

    return _create_table("section_meetings", SectionMeeting, mapping)

def migrate_organizations():
    print("  Migrating organizations...")

    mapping = {
        "name": "name",
        "url": "url",
        "alt_text": "alt",
        "width": "width",
        "height": "height",
        "image_file_name": "image"
    }

    return _create_table("organizations", Organization, mapping)


# disable all auto_now_add fields, if we don't they won't respect our values,
# even if we pass it as a param
# https://stackoverflow.com/q/7499767/12164878
for model in [User, Course, Professor, Section, Gened, ProfessorCourse, SectionMeeting]:
    for field in model._meta.local_fields:
        if field.name == "created_at":
            field.auto_now_add = False

courses = migrate_courses()
professors = migrate_professors()
link_courses_and_professors(courses, professors)

users = migrate_users()
reviews = migrate_reviews(users, courses, professors)
grades = migrate_grades(courses, professors)
geneds = migrate_geneds(courses)
sections = migrate_sections(courses)
link_sections_and_professors(professors, sections)
migrate_section_meetings(sections)
migrate_organizations()
