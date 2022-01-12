from enum import Enum, auto
from functools import lru_cache, wraps
import time

from discord_webhook import DiscordWebhook
from discord_webhook.webhook import DiscordEmbed

from home.models import Course, Professor, Review, Grade
from planetterp.config import discord_webhook_updates_url

def semester_name(semester_number):
    seasons = {"01": "Spring", "05": "Summer", "08": "Fall", "12": "Winter"}
    season = seasons[semester_number[4:6]]

    year = int(semester_number[:4])

    # The winter semester starting in january 2021 is actually called 202012
    # internally, not 202112, so return the next year for winter to adjust.
    if season == "Winter":
        year += 1

    return f"{season} {year}"

def semester_number(semester_name: str):
    seasons = {"Spring": "01", "Summer": "05", "Fall": "08", "Winter": "12"}
    season, year = semester_name.strip().split(' ')

    if season == "Winter":
        year = int(year) + 1

    return f"{year}{seasons[season]}"

# This list must be kept in ascending order, as other parts of the codebase rely
# on the ordering.
RECENT_SEMESTERS = ["202008", "202012", "202101", "202105", "202108"]

class AdminAction(Enum):
    # Review actions
    REVIEW_VERIFY = "review_verify"
    REVIEW_HELP = "review_help"

    # Professor actions
    PROFESSOR_VERIFY = "professor_verify"
    PROFESSOR_EDIT = "professor_edit"
    PROFESSOR_MERGE = "professor_merge"
    PROFESSOR_DELETE = "professor_delete"
    PROFESSOR_SLUG = "professor_slug"

class ReviewsTableColumn(Enum):
    INFORMATION = auto()
    REVIEW = auto()
    STATUS = auto()
    ACTION = auto()

def slug_in_use_err(slug: str, name: str):
    return f"Slug '{slug}' is already in use by '{name}'. Please merge these professors together if they are the same person."

# adapted from https://stackoverflow.com/a/63674816
def ttl_cache(max_age, maxsize=128, typed=False):
    """
    An @lru_cache, but instead of caching indefinitely (or until purged from
    the cache, which in practice rarely happens), only caches for `max_age`
    seconds.

    That is, at the first function call with certain arguments, the result is
    cached. Then, when the funcion is called again with those arguments, if it
    has been more than `max_age` seconds since the first call, the result is
    recalculated and that value is cached. Otherwise, the cached value is
    returned.

    Warnings
    --------
    This function does not actually guarantee that the result will be cached for
    exactly `max_age` seconds. Rather it only guarantees that the result will be
    cached for at *most* `max_age` seconds. This is to simplify implementation.
    """
    def decorator(function):
        @lru_cache(maxsize=maxsize, typed=typed)
        def with_time_salt(*args, __time_salt, **kwargs):
            return function(*args, **kwargs)

        @wraps(function)
        def wrapper(*args, **kwargs):
            time_salt = time.time() // max_age
            return with_time_salt(*args, **kwargs, __time_salt=time_salt)

        return wrapper
    return decorator

def send_updates_webhook(*, include_professors=True, include_reviews=True):
    if not discord_webhook_updates_url:
        return

    title = ""
    if include_professors:
        num_professors = Professor.objects.filter(status=Professor.Status.PENDING).count()
        title += f"{num_professors} unverified professor(s)"
    if include_professors and include_reviews:
        title += " and "
    if include_reviews:
        num_reviews = Review.objects.filter(status=Review.Status.PENDING).count()
        title += f"{num_reviews} unverified review(s)"

    webhook = DiscordWebhook(url=discord_webhook_updates_url)
    embed = DiscordEmbed(title=title, description="\n", url="https://planetterp.com/admin")

    webhook.add_embed(embed)
    webhook.execute()

class GradeData:
    def _get_data(self, average_gpa, num_students, grades):
        def _statistic(name):
            if not num_students:
                return 0
            return round((grades[name] / num_students) * 100, 2)

        return {
            "average_gpa": average_gpa,
            "num_students": num_students,
            "data_plus": [
                _statistic("a_plus_total"),
                _statistic("b_plus_total"),
                _statistic("c_plus_total"),
                _statistic("d_plus_total")
            ],
            "data_flat": [
                _statistic("a_total"),
                _statistic("b_total"),
                _statistic("c_total"),
                _statistic("d_total"),
                _statistic("f_total"),
                _statistic("w_total"),
                _statistic("other_total")
            ],
            "data_minus": [
                _statistic("a_minus_total"),
                _statistic("b_minus_total"),
                _statistic("c_minus_total"),
                _statistic("d_minus_total")
            ]
        }

    def _course_grade_data(self, professor, PF_semesters):
        professor = Professor.objects.verified.filter(name=professor).first()
        courses = Course.objects.filter(professors=professor)
        grades = Grade.objects.filter(professor=professor)
        if not PF_semesters:
            grades = grades.exclude(semester=202001)

        grade_data = {
            "professor_slug": professor.slug,
            "average_gpa": grades.average_gpa(),
            "num_students": grades.num_students()
        }
        for course in courses:
            course_grades = grades
            course_grades = course_grades.filter(course=course)

            average_course_gpa = course_grades.average_gpa()
            num_course_students = course_grades.num_students()
            course_grades = course_grades.grade_totals_aggregate()

            grade_data[course.name] = (average_course_gpa, num_course_students, course_grades)

        return grade_data

    @ttl_cache(24 * 60 * 60)
    def _grade_data(self, professor, course, semester, section, PF_semesters):
        grades = Grade.objects.all()

        if professor:
            professor = Professor.objects.verified.filter(slug=professor).first()
            grades = grades.filter(professor=professor)
        if course:
            course = Course.objects.filter(name=course).first()
            grades = grades.filter(course=course)
        if semester:
            grades = grades.filter(semester=semester_number(semester))
        if section:
            grades = grades.filter(section=section)
        if not PF_semesters:
            grades = grades.exclude(semester=202001)

        average_gpa = grades.average_gpa()
        num_students = grades.num_students()
        grades = grades.grade_totals_aggregate()

        return (average_gpa, num_students, grades)

    @staticmethod
    def compose_grade_data(professor, course, semester, section, PF_semesters):
        (average_gpa, num_students, grades) = GradeData()._grade_data(professor,
        course, semester, section, PF_semesters)

        return GradeData()._get_data(average_gpa, num_students, grades)

    @staticmethod
    def compose_course_grade_data(professor, PF_semesters):
        grade_data = GradeData()._course_grade_data(professor, PF_semesters)
        data = {
            "professor_slug": grade_data.pop("professor_slug"),
            "average_gpa": grade_data.pop("average_gpa"),
            "num_students": grade_data.pop("num_students"),
            "data": {}
        }

        for course_name, course_data in grade_data.items():
            (course_average_gpa, course_num_students, course_grades) = course_data

            if course_num_students and course_average_gpa:
                data['data'][course_name] = GradeData()._get_data(
                    course_average_gpa, course_num_students, course_grades)
        return data
