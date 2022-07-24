from django.urls import path, register_converter, reverse, include
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap

from home.views.add_professor import AddProfessor
from home.views.admin import Admin
from home.views.authentication import Login, Logout, ForgotPassword, Register
from home.views.basic import (About, Contact, PrivacyPolicy, TermsOfUse,
    Courses, Professors, Documents, SetColorScheme, Robots, CourseReviews,
    Index, SortReviewsTable, RecomputeTTLCache, UserProfile, Ads)
from home.views.grades import Grades
from home.views.statistics import Statistics
from home.views.course import Course
from home.views.data_sources import GradeData, CourseDifficultyData, GenedData
from home.views.endpoints import Autocomplete
from home.views.professor import Professor
from home.views.profile import Profile, ResetPassword
from home.views.search import Search
from home.views.tools import (Tools, ToolDemographics, ToolPopularCourses,
    ToolGradeInflation, ToolGeneds, ToolCourseDifficulty)
from home.models import Course as CourseModel, Professor as ProfessorModel

import debug_toolbar


class CourseConverter:
    # yes, unfortunately there are courses with a trailing plus, eg `BIOL105+`
    regex = "[A-Za-z]{4}[\dA-Za-z]{3,6}\+?"

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

class CourseSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return CourseModel.unfiltered.all().order_by("pk")

class ProfessorSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5

    def items(self):
        return ProfessorModel.verified.all().order_by("pk")

class StaticSitemap(Sitemap):
    def location(self, item):
        return reverse(item)

# short for "high priority"
class HighStaticSitemap(StaticSitemap):
    changefreq = "daily"
    priority = 1

    def items(self):
        return ["index"]

class MediumStaticSitemap(StaticSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ["login", "grades", "tools", "tools-demographics",
            "tools-popular-courses", "tools-course-difficulty",
            "tools-geneds", "tools-grade-inflation", "api-docs"]

class LowStaticSitemap(StaticSitemap):
    changefreq = "weekly"
    priority = 0.2

    def items(self):
        return ["about"]

sitemaps = {
    "courses": CourseSitemap,
    "professors": ProfessorSitemap,
    "high_static": HighStaticSitemap,
    "medium_static": MediumStaticSitemap,
    "low_static": LowStaticSitemap,
}

urlpatterns = [
    # authentication
    path('login', Login.as_view(), name='login'),
    path('logout', Logout.as_view(), name='logout'),
    path('forgot_password', ForgotPassword.as_view(), name='password-reset'),
    path('register', Register.as_view(), name='register'),

    # basic
    path('', Index.as_view(), name='index'),
    path('about', About.as_view(), name='about'),
    path('privacypolicy', PrivacyPolicy.as_view(), name='privacy-policy'),
    path('termsofuse', TermsOfUse.as_view(), name='terms-of-use'),
    path("documents", Documents.as_view(), name="documents"),
    path("contact", Contact.as_view(), name="contact"),
    path('set_colors_cheme', SetColorScheme.as_view(), name='set-color-scheme'),
    path('courses', Courses.as_view(), name='courses'),
    path('professors', Professors.as_view(), name='professors'),
    path('robots.txt', Robots.as_view(), name="robots"),
    path('sitemap.xml', sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path('table_sort', SortReviewsTable.as_view(), name="table_sort"),
    path('recompute_ttl_cache', RecomputeTTLCache.as_view(), name="recompute-ttl-cache"),
    path("ads.txt", Ads.as_view(), name="ads"),

    # data sources
    path('data_sources/grade_data', GradeData.as_view(), name='grade-data'),
    path("data_sources/course_difficulty_data/<str:type_>", CourseDifficultyData.as_view(), name="course-difficulty-data"),
    path("data_sources/gened_data", GenedData.as_view(), name="gened-data"),

    # endpoints
    path('autocomplete', Autocomplete.as_view(), name='autocomplete'),

    # standalone
    # this can't be <slug:slug> because django slugs don't allow quotes, and
    # some professors have quotes in their name (o'brien)
    path('professor/<str:slug>', Professor.as_view(), name='professor'),
    path('search', Search.as_view(), name='search'),
    path('course/<course:name>', Course.as_view(), name='course'),
    path('course/<course:name>/reviews', CourseReviews.as_view(), name='course-reviews'),
    path('admin', Admin.as_view(), name='admin'),
    path('add_professor', AddProfessor.as_view(), name='add-professor'),
    path("statistics", Statistics.as_view(), name="statistics"),
    path('grades', Grades.as_view(), name='grades'),

    # profile
    path('profile', Profile.as_view(), name='profile'),
    path('profile/resetpassword/<reset_code:reset_code>', ResetPassword.as_view(), name='reset-password'),
    path('users/<int:user_id>', UserProfile.as_view(), name='user-profile'),

    # tools
    path('tools', Tools.as_view(), name='tools'),
    path('tools/demographics', ToolDemographics.as_view(), name='tools-demographics'),
    path('tools/coursedifficulty', ToolCourseDifficulty.as_view(), name='tools-course-difficulty'),
    path('tools/geneds', ToolGeneds.as_view(), name='tools-geneds'),
    path('tools/gradeinflation', ToolGradeInflation.as_view(), name='tools-grade-inflation'),
    path('tools/popularcourses', ToolPopularCourses.as_view(), name='tools-popular-courses'),

    path('__debug__/', include(debug_toolbar.urls)),
]
