import os
from django.db import models
import web
from django.core.wsgi import get_wsgi_application
from planetterp.config import USER, PASSWORD

# https://stackoverflow.com/a/43391786
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

from home.models import *

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
        if table == "users" and id_ == 0:
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
    mapping = {
        "department": "department",
        "course_number": "course_number",
        "created_at": "created",
        "title": "title",
        "credits": "credits",
        "description": "description",
    }

    mapping["historical"] = False
    courses = _create_table("courses", Course, mapping)
    return courses
    # TODO migrate historical courses too that aren't already in the courses
    # table
    # mapping["historical"] = True
    # courses_historical = _create_table("courses_historical", Course, mapping)

def migrate_professors():
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
    for row in db.select("professor_courses"):
        professor = professors[row["professor_id"]]
        course = courses[row["course_id"]]
        recent_semester = row["recent_semester"]
        through = {
            "recent_semester": recent_semester
        }
        course.professors.add(professor, through_defaults=through)

def migrate_users():
    def _send_review_email(row):
        val = row["send_review_email"]
        return True if val is None else bool(val)

    mapping = {
        "send_review_email": _send_review_email,
        "username": "username",
        "password": "password",
        "email": "email",
        "is_staff": "is_admin"
    }
    return _create_table("users", User, mapping)

def migrate_reviews(users, courses, professors):
    def _user(row):
        if row["reviewer_id"] == 0:
            return None
        return _foreign_key(users, row, "reviewer_id")

    def _status(row):
        mapping = {
            -1: Review.Status.REJECTED,
            0: Review.Status.PENDING,
            1: Review.Status.VERIFIED,
        }
        return mapping[row["verified"]]

    mapping = {
        "professor": lambda row: _foreign_key(professors, row, "professor_id"),
        "course": lambda row: _foreign_key(courses, row, "course_id", True),
        "user": _user,
        "updater": lambda row: _foreign_key(users, row, "updated_by", True),
        "content": "review",
        "rating": "rating",
        "grade": "expected_grade",
        "status": _status,
        "anonymous": "anonymous",
        "from_ourumd": "from_ourumd",
    }
    return _create_table("reviews", Review, mapping)

def migrate_grades(courses, professors):
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
        "other": "OTHER",
        "historical": False
    }
    return _create_table("grades", Grade, mapping)

def migrate_geneds(courses):
    mapping = {
        "name": "gened",
        "course": lambda row: _foreign_key(courses, row, "course_id")
    }

    return _create_table("geneds", Gened, mapping)


courses = migrate_courses()
professors = migrate_professors()
link_courses_and_professors(courses, professors)

users = migrate_users()
reviews = migrate_reviews(users, courses, professors)
grades = migrate_grades(courses, professors)
geneds = migrate_geneds(courses)

# before running, do the following:
# * delete any users with stupidly long emails
# * delete any professor with a negative id

# not necessary but will need to be addressed in the future:
# * set any professors with duplicate slugs to a null slug (or some other
#   resolution). My db has a bunch of professors with the slug "test", not put
#   there by me.
