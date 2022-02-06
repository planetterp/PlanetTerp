from django.views import View
from django.shortcuts import render

from django.db.models import Count, Sum, Q, FloatField

from home.models import Review, Professor
from home.utils import ttl_cache

class Statistics(View):
    def get(self, request):
        (review_ratings, review_dates, professor_ratings) = self.graph_data()
        context = {
            "review_ratings": review_ratings,
            "review_dates": review_dates,
            "professor_ratings": professor_ratings
        }
        return render(request, "statistics.html", context)

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def graph_data():
        reviews = Review.verified.all()
        professors = (
            Professor.verified
            .annotate(
                # TODO consolidate this with the Professor#average_rating
                # method, will likely require a new Professors queryset
                average_rating_= (
                    Sum(
                        "review__rating",
                        output_field=FloatField(),
                        filter=Q(review__status=Review.Status.VERIFIED)
                    )
                    /
                    Count(
                        "review",
                        filter=Q(review__status=Review.Status.VERIFIED)
                    )
                )
            )
        )

        review_ratings = [0] * 5
        # not a typo - there are actually 53 weeks in an isocalendar year.
        review_dates = [0] * 53
        # we'll divide each of the 4 intervals (1-2, 2-3, 3-4, 4-5) into 10
        # segments each. So bucket 1.0 - 1.1 together, 1.1 - 1.2 together, etc.
        professor_ratings = [0] * 10 * 4

        for review in reviews:
            review_ratings[review.rating - 1] += 1
            week = review.created_at.isocalendar()[1]
            review_dates[week - 1] += 1

        professors = professors.annotate()
        for professor in professors:
            rating = professor.average_rating_
            if rating is None:
                continue
            bucket = int((rating - 1) // 0.1)
            professor_ratings[bucket] += 1

        return (review_ratings, review_dates, professor_ratings)
