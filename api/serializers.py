from rest_framework.serializers import (ModelSerializer, Serializer,
    SerializerMethodField, RelatedField as _RelatedField, CharField,
    DateTimeField, IntegerField)

from home.models import Course, Professor, Review, Grade


# our entire api is read only
class RelatedField(_RelatedField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, read_only=True)

class CourseField(RelatedField):
    def to_representation(self, course):
        return course.name

class ProfessorField(RelatedField):
    def to_representation(self, professor):
        return professor.name


class ReviewsSerializer(ModelSerializer):
    course = CourseField()
    professor = ProfessorField()
    review = CharField(source="content")
    expected_grade = CharField(source="grade")
    created = DateTimeField(source="created_at")

    class Meta:
        model = Review
        fields = ["professor", "course", "review", "rating", "expected_grade",
            "created"]

    # necessary for compatability with the pre-django api, which returned ""
    # for reviews with a null expected grade.
    def to_representation(self, instance):
        response = super().to_representation(instance)
        if response["expected_grade"] is None:
            response["expected_grade"] = ""
        return response

class CourseSerializer(ModelSerializer):
    average_gpa = SerializerMethodField()
    professors = ProfessorField(many=True)

    class Meta:
        model = Course
        exclude = ["created_at", "id"]

    def get_average_gpa(self, course):
        return course.average_gpa()


class ProfessorSerializer(ModelSerializer):
    courses = CourseField(many=True, source="course_set")
    average_rating = SerializerMethodField()

    class Meta:
        model = Professor
        exclude = ["id", "status", "created_at"]

    def get_average_rating(self, professor):
        return professor.average_rating()


class ProfessorWithReviewsSerializer(ProfessorSerializer):
    # TODO unapproved reviews will be returned here, filter them out
    reviews = ReviewsSerializer(many=True, source="review_set")

class CourseWithReviewsSerializer(CourseSerializer):
    reviews = ReviewsSerializer(many=True, source="review_set")


class SearchResultSerializer(Serializer):
    type = SerializerMethodField()
    name = CharField()
    slug = SerializerMethodField()

    def get_type(self, result):
        if isinstance(result, Course):
            return "course"
        return "professor"

    def get_slug(self, result):
        if isinstance(result, Course):
            return result.name
        return result.slug


class GradeSerializer(ModelSerializer):
    class Meta:
        model = Grade
        exclude = ["id", "num_students"]

    # maintain backwards compatability
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["A+"] = data.pop("a_plus")
        data["A"] = data.pop("a")
        data["A-"] = data.pop("a_minus")
        data["B+"] = data.pop("b_plus")
        data["B"] = data.pop("b")
        data["B-"] = data.pop("b_minus")
        data["C+"] = data.pop("c_plus")
        data["C"] = data.pop("c")
        data["C-"] = data.pop("c_minus")
        data["D+"] = data.pop("d_plus")
        data["D"] = data.pop("d")
        data["D-"] = data.pop("d_minus")
        data["F"] = data.pop("f")
        data["W"] = data.pop("w")
        data["Other"] = data.pop("other")
        return data
