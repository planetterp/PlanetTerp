from typing import List

from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.core.handlers.wsgi import WSGIRequest

import django_tables2 as tables

from home.utils import ReviewsTableColumn
from home.models import Review
from home.tables.columns import InformationColumn, ReviewColumn, StatusColumn, VerifiedReviewsActionColumn, UnverifiedReviewsActionColumn, ProfileReviewsActionColumn

class BaseReviewsTable(tables.Table):
    '''
    WARNING: This class is not designed to be instantiated directly!
             Use one of the predefined table classes below instead.
    '''
    information = InformationColumn()
    review = ReviewColumn()
    status = StatusColumn()

    def __init__(
        self,
        columns: List[ReviewsTableColumn],
        reviews: QuerySet[Review],
        request: WSGIRequest,
        *args,
        **kwargs
    ):

        self.row_attrs = None
        self.columns = columns
        # performance tanks on large tables without this, since we're accessing
        # these attributes for almost every review.
        self.reviews = reviews.select_related("professor", "course", "user")
        self.request = request
        self.data = self.get_data(self.reviews)

        kwargs = {
            "exclude": [column.name.lower() for column in ReviewsTableColumn if column not in self.columns],
            "attrs": {"class": "table table-striped reviews-table"},
            "sequence": [column.name.lower() for column in self.columns],
            **kwargs
        }

        if ReviewsTableColumn.INFORMATION in self.columns:
            self.row_attrs = {
                "class": lambda record: record['information']['review'].course.name if record['information']['review'].course else "no-course",
                "id": lambda record: f"review-{record['information']['review'].pk}"
            }

        super().__init__(self.data, row_attrs=self.row_attrs, *args, **kwargs)

    def get_data(self, reviews: QuerySet[Review]):
        data = []
        for review in reviews:
            formatted_data = {}

            if ReviewsTableColumn.INFORMATION in self.columns:
                formatted_data['information'] = {
                    "review": review,
                    "is_planetterp_admin": self.request.user.has_perm("home.mod")
                }
            if ReviewsTableColumn.REVIEW in self.columns:
                formatted_data['review'] = {"review": review}
            if ReviewsTableColumn.STATUS in self.columns:
                formatted_data['status'] = {"review": review}
            if ReviewsTableColumn.ACTION in self.columns:
                formatted_data['action'] = {
                    "request": self.request,
                    "model_obj": review
                }

            data.append(formatted_data)
        return data

class VerifiedReviewsTable(BaseReviewsTable):
    action = VerifiedReviewsActionColumn()

    def __init__(self, reviews, request, *args, **kwargs):
        noun = "instructor" if "professor" in request.path else "course"
        empty_text = mark_safe(
            (
            f'<h4 class="text-center">This {noun} has not been reviewed yet. '
            'Why not be the first to do so?</h4>'
            )
        )

        self.columns = [ReviewsTableColumn.INFORMATION, ReviewsTableColumn.REVIEW]
        if request.user.has_perm("home.mod"):
            self.columns.append(ReviewsTableColumn.ACTION)

        kwargs = {"empty_text": empty_text}
        super().__init__(self.columns, reviews, request, *args, **kwargs)

class UnverifiedReviewsTable(BaseReviewsTable):
    action = UnverifiedReviewsActionColumn()

    def __init__(self, reviews, request, *args, **kwargs):
        empty_text = mark_safe('<h4 class="text-center">There are no reviews to verify!</h4>')
        self.columns = [ReviewsTableColumn.INFORMATION, ReviewsTableColumn.REVIEW, ReviewsTableColumn.ACTION]

        kwargs = {"empty_text": empty_text}
        super().__init__(self.columns, reviews, request, *args, **kwargs)

class ProfileReviewsTable(BaseReviewsTable):
    action = ProfileReviewsActionColumn()

    def __init__(self, reviews, request, editable=True, *args, **kwargs):
        empty_text = mark_safe('<h4 class="text-center">You haven\'t written any reviews! Why not start now?</h4>')
        self.columns = [ReviewsTableColumn.INFORMATION, ReviewsTableColumn.REVIEW, ReviewsTableColumn.STATUS]
        if editable:
            self.columns.append(ReviewsTableColumn.ACTION)

        kwargs = {"empty_text": empty_text}
        super().__init__(self.columns, reviews, request, *args, **kwargs)
