from django.urls import path, register_converter

from home.views.add_professor import AddProfessor
from home.views.admin import Admin
from home.views.authentication import Login, Logout, ForgotPassword, Register
from home.views.basic import (About, Contact, PrivacyPolicy, TermsOfUse, Courses,
    Professors, Fall2020, Documents, SetColorScheme, Robots, Sitemap, Grades,
    CourseReviews, Index, SortReviewsTable)
from home.views.course import Course
from home.views.data_sources import GradeData, CourseDifficultyData, GenedData
from home.views.endpoints import Autocomplete
from home.views.professor import Professor
from home.views.profile import Profile, ResetPassword
from home.views.search import Search
from home.views.tools import (Tools, ToolDemographics, ToolPopularCourses,
    ToolGradeInflation, ToolGeneds, ToolCourseDifficulty)
from home.views.schedule import groupmeauth, groups, newschedule, schedule


class CourseConverter:
    regex = "[A-Za-z]{4}[\dA-Za-z]{3,6}"

    def to_python(self, value):
        return value
    def to_url(self, value):
        return value

class ResetCodeConverter:
    regex = "[\da-f]+"

    def to_python(self, value):
        return value
    def to_url(self, value):
        return value

register_converter(CourseConverter, "course")
register_converter(ResetCodeConverter, "reset_code")


urlpatterns = [
    # authentication
    path('login', Login.as_view(), name='login'),
    path('logout', Logout.as_view(), name='logout'),
    path('forgot_password', ForgotPassword.as_view(), name='password-reset'),
    path('register', Register.as_view(), name='register'),

    # basic
    path('', Index.as_view(), name='index'),
    path('grades', Grades.as_view(), name='grades'),
    path('about', About.as_view(), name='about'),
    path('privacypolicy', PrivacyPolicy.as_view(), name='privacy-policy'),
    path('termsofuse', TermsOfUse.as_view(), name='terms-of-use'),
    path("documents", Documents.as_view(), name="documents"),
    path("fall2020", Fall2020.as_view(), name="fall2020"),
    path("contact", Contact.as_view(), name="contact"),
    path('set_colors_cheme', SetColorScheme.as_view(), name='set-color-scheme'),
    path('courses', Courses.as_view(), name='courses'),
    path('professors', Professors.as_view(), name='professors'),
    path('robots.txt', Robots.as_view(), name="robots"),
    path('sitemap.xml', Sitemap.as_view(), name="sitemap"),
    path('table_sort', SortReviewsTable.as_view(), name="table_sort"),

    # data sources
    path('data_sources/grade_data', GradeData.as_view(), name='grade-data'),
    path("data_sources/course_difficulty_data/<str:type_>", CourseDifficultyData.as_view(), name="course-difficulty-data"),
    path("data_sources/gened_data", GenedData.as_view(), name="gened-data"),

    # endpoints
    path('autocomplete', Autocomplete.as_view(), name='autocomplete'),

    # standalone
    path('professor/<slug:slug>', Professor.as_view(), name='professor'),
    path('search', Search.as_view(), name='search'),
    path('course/<course:name>', Course.as_view(), name='course'),
    path('course/<course:name>/reviews', CourseReviews.as_view(), name='course-reviews'),
    path('admin', Admin.as_view(), name='admin'),
    path('add_professor', AddProfessor.as_view(), name='add-professor'),

    # profile
    path('profile', Profile.as_view(), name='profile'),
    path('profile/resetpassword/<reset_code:reset_code>', ResetPassword.as_view(), name='reset-password'),

    # schedule
    path('schedule', schedule.Schedule.as_view(), name='schedule'),
    path('schedule/new', newschedule.NewSchedule.as_view(), name='schedule-new'),
    path('schedule/groups/auth', groupmeauth.GroupMeAuth.as_view(), name='schedule-groupme-auth'),
    path('schedule/groups', groups.Groups.as_view(), name='schedule-groups'),

    # tools
    path('tools', Tools.as_view(), name='tools'),
    path('tools/demographics', ToolDemographics.as_view(), name='tools-demographics'),
    path('tools/coursedifficulty', ToolCourseDifficulty.as_view(), name='tools-course-difficulty'),
    path('tools/geneds', ToolGeneds.as_view(), name='tools-geneds'),
    path('tools/gradeinflation', ToolGradeInflation.as_view(), name='tools-grade-inflation'),
    path('tools/popularcourses', ToolPopularCourses.as_view(), name='tools-popular-courses'),
]
