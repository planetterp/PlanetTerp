from django.core.management import BaseCommand
from django.db.models import Max, Q

from home.models import Course
from home.utils import Semester

class Command(BaseCommand):
    def handle(self, *args, **options):
        # a course is "recent" if we have a grade record for it since
        # `Semester(201201)`, or if it was taught at all since
        # `Semester(201201)`.
        #
        # A course could be matched by the second, but not the first, condition
        # if the course will be taught next semester but we don't have grade
        # data for it yet.
        #
        # A course could be matched by the first, but not the second, condition
        # if the course has grade data more recent than 201201, but hasn't been
        # taught in the past ~1 year, which would cause it to appear in
        # professorcourse_recent_semester, which tracks which professors to
        # display on course pages as "previously taught this course".
        #
        # The reason these two are not identical conditions is because the time
        # frame for a course to be considered recently taught (~10 years) and
        # the time frame for a professor to be considered having recently taught
        # a course may not be the same.

        # recent recency
        Course.unfiltered.update(is_recent=False)

        # actually update recency
        (
            Course.unfiltered
            .annotate(max_semester=Max("grade__semester"))
            .annotate(most_recent_semester=Max(
                "professorcourse__recent_semester")
            )
            .filter(
                Q(max_semester__gte=Semester(201201)) |
                Q(most_recent_semester__gte=Semester(201201))
            )
            .update(is_recent=True)
        )
