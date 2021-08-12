from enum import Enum

from django.contrib.auth.models import AbstractUser
from django.utils.safestring import mark_safe
from django.db.models.functions import Concat
from django.urls import reverse
from django.core import validators
from django.db.models import (Model, CharField, DateTimeField, TextField,
    IntegerField, BooleanField, ForeignKey, PositiveIntegerField, RESTRICT,
    CASCADE, ManyToManyField, SlugField, TextChoices, FloatField, Manager,
    QuerySet, EmailField, Sum)

class GradeQuerySet(QuerySet):
    def average_gpa(self):
        return self.aggregate(
            average_gpa=(
                (Sum("a_plus") * 4  + Sum("a") * 4 + Sum("a_minus") * 3.7 +
                Sum("b_plus") * 3.3 + Sum("b") * 3 + Sum("b_minus") * 2.7 +
                Sum("c_plus") * 2.3 + Sum("c") * 2 + Sum("c_minus") * 1.7 +
                Sum("d_plus") * 1.3 + Sum("d") * 1 + Sum("d_minus") * 0.7)
                /
                Sum("num_students")
            )
        )["average_gpa"]

    def num_students(self):
        return self.aggregate(
            num_students=Sum("num_students")
        )["num_students"]

    def grade_totals_aggregate(self):
        return (
            self.aggregate(
                a_plus_total=Sum("a_plus"), a_total=Sum("a"), a_minus_total=Sum("a_minus"),
                b_plus_total=Sum("b_plus"), b_total=Sum("b"), b_minus_total=Sum("b_minus"),
                c_plus_total=Sum("c_plus"), c_total=Sum("c"), c_minus_total=Sum("c_minus"),
                d_plus_total=Sum("d_plus"), d_total=Sum("d"), d_minus_total=Sum("d_minus"),
                f_total=Sum("f"), w_total=Sum("w"), other_total=Sum("other")
            )
        )

    average_gpa.queryset_only = True
    num_students.queryset_only = True


class CourseManager(Manager):
    def get_queryset(self):
        # annotate all queries with a name field so we can filter on it
        return (
            super().get_queryset().annotate(
                name=Concat("department", "course_number")
            )
        )


class ReviewManager(Manager):
    @property
    def verified(self):
        return self.filter(status=Review.Status.VERIFIED)

    @property
    def pending(self):
        return self.filter(status=Review.Status.PENDING)

    @property
    def rejected(self):
        return self.filter(status=Review.Status.REJECTED)


class ProfessorManager(Manager):
    @property
    def verified(self):
        return self.filter(status=Professor.Status.VERIFIED)

    @property
    def pending(self):
        return self.filter(status=Professor.Status.PENDING)

    @property
    def rejected(self):
        return self.filter(status=Professor.Status.REJECTED)


class Course(Model):
    department = CharField(max_length=4)
    course_number = CharField(max_length=6)
    title = TextField(null=True)
    credits = IntegerField(null=True)
    description = TextField(null=True)
    historical = BooleanField()
    created_at = DateTimeField(auto_now_add=True)

    professors = ManyToManyField("Professor", blank=True,
        through="ProfessorCourse")

    objects = CourseManager()

    def average_gpa(self):
        return self.grade_set.all().average_gpa()

    @property
    def name(self):
        return f"{self.department}{self.course_number}"

    # necessary for django admin interface to be able to create courses
    # https://stackoverflow.com/a/51189035
    @name.setter
    def name(self, _value):
        pass

    def get_absolute_url(self):
        return reverse("course", kwargs={"name": self.name})

    def __str__(self):
        return self.name

class Professor(Model):
    class Type(TextChoices):
        PROFESSOR = "professor"
        TA = "TA"

    class Status(TextChoices):
        VERIFIED = "verified"
        PENDING = "pending"
        REJECTED = "rejected"

    objects = ProfessorManager()

    name = CharField(max_length=100)
    # TODO: make this field unique when the db migration is finished so we can
    # deal with the fallout more cleanly
    slug = SlugField(max_length=100, null=True)
    type = CharField(choices=Type.choices, max_length=50)
    status = CharField(choices=Status.choices, default=Status.PENDING,
        max_length=50)
    created_at = DateTimeField(auto_now_add=True)

    def average_rating(self):
        num_reviews = self.review_set.count()
        if num_reviews == 0:
            return None
        return (
            self.review_set
            .aggregate(
                average_rating=Sum("rating") / num_reviews
            )
        )["average_rating"]

    def get_absolute_url(self):
        return reverse("professor", kwargs={"slug": self.slug})

    def __str__(self):
        return f"{self.name} ({self.slug})"


class Section(Model):
    course = ForeignKey(Course, RESTRICT)
    professors = ManyToManyField(Professor)
    semester = CharField(max_length=6)
    section_number = CharField(max_length=8)
    seats = PositiveIntegerField()
    available_seats = PositiveIntegerField()
    waitlist = PositiveIntegerField()
    active = BooleanField()
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course} ({self.section_number}) taught by {self.professors}"

class User(AbstractUser):
    email_changed = BooleanField(default=False)
    send_review_email = BooleanField(default=True)
    email = EmailField(
        null=True,
        blank=True,
        validators=[validators.validate_email],
        help_text=mark_safe(
            'Once an email is set, it cannot be changed. '
            '<span id="email_hint_text" style="display: none;">'
            '<br /><br /> Planetterp will only send you emails when a review of '
            'yours is approved, rejected, or unverified. You can opt out of this '
            'in your account settings at any time. <br /><br /> Your email and '
            'any other personal data on our site is kept confidential and isn\'t '
            'shared with anyone else. If you have any questions about how '
            'Planetterp handles your data, please email '
            '<a href="mailto:admin@planetterp.com">admin@planetterp.com</a>'
            '</span>'
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username = self._meta.get_field('username')
        password = self._meta.get_field('password')

        username.help_text = "Once a username is set, it cannot be changed."
        username.error_messages['required'] = "You must enter a username"
        username.validators += [
            validators.MaxLengthValidator(20, "Username must be less than 20 characters"),
            validators.MinLengthValidator(2, "Username must be at least 2 characters")
        ]

        password.error_messages['required'] = "You must enter a password"
        password.validators += [
            validators.MinLengthValidator(8, "Password must be at least 8 characters")
        ]


class AuditLog(Model):
    username = TextField()
    summary = TextField()
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.summary} (action by {self.username})"


class Discussion(Model):
    author = ForeignKey(User, CASCADE)
    title = CharField(max_length=200)
    num_views = PositiveIntegerField(default=0)
    content = TextField()
    removed = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)


class Fall2020Search(Model):
    query = TextField()
    created_at = DateTimeField(auto_now_add=True)


class Gened(Model):
    GENEDS = [
        "FSAW", "FSAR", "FSMA", "FSOC", "FSPW", "DSHS", "DSHU", "DSNS", "DSNL",
        "DSSP", "DVCC", "DVUP", "SCIS"
    ]

    course = ForeignKey(Course, RESTRICT)
    name = CharField(max_length=4)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course} ({self.name})"

class Review(Model):
    class Status(TextChoices):
        VERIFIED = "verified"
        PENDING = "pending"
        REJECTED = "rejected"

    class ReviewType(Enum):
        ADD = "add"
        REVIEW = "review"

    class Grades(TextChoices):
        A_PLUS = "A+"
        A = "A"
        A_MINUS = "A-"

        B_PLUS = "B+"
        B = "B"
        B_MINUS = "B-"

        C_PLUS = "C+"
        C = "C"
        C_MINUS = "C-"

        D_PLUS = "D+"
        D = "D"
        D_MINUS = "D-"

        F = "F"
        P = "P"
        W = "W"
        XF = "XF"

    objects = ReviewManager()

    professor = ForeignKey(Professor, CASCADE)
    course = ForeignKey(Course, RESTRICT, null=True, blank=True)
    user = ForeignKey(User, CASCADE, null=True, blank=True)
    updater = ForeignKey(User, CASCADE, null=True, blank=True, related_name="updater")
    content = TextField()
    rating = IntegerField()
    grade = CharField(max_length=2, null=True, blank=True)
    status = CharField(choices=Status.choices, default=Status.PENDING,
        max_length=50)
    anonymous = BooleanField()
    from_ourumd = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class Grade(Model):
    POSSIBLE_GRADES = [choice[0] for choice in Review.Grades.choices]
    VOWEL_GRADES = ["A", "A-", "A+", "F"]

    course = ForeignKey(Course, RESTRICT)
    professor = ForeignKey(Professor, CASCADE, null=True)
    semester = CharField(max_length=6)
    section = CharField(max_length=10)
    num_students = PositiveIntegerField()
    a_plus  = PositiveIntegerField(db_column="APLUS")
    a       = PositiveIntegerField(db_column="A")
    a_minus = PositiveIntegerField(db_column="AMINUS")
    b_plus  = PositiveIntegerField(db_column="BPLUS")
    b       = PositiveIntegerField(db_column="B")
    b_minus = PositiveIntegerField(db_column="BMINUS")
    c_plus  = PositiveIntegerField(db_column="CPLUS")
    c       = PositiveIntegerField(db_column="C")
    c_minus = PositiveIntegerField(db_column="CMINUS")
    d_plus  = PositiveIntegerField(db_column="DPLUS")
    d       = PositiveIntegerField(db_column="D")
    d_minus = PositiveIntegerField(db_column="DMINUS")
    f       = PositiveIntegerField(db_column="F")
    w       = PositiveIntegerField(db_column="W")
    other   = PositiveIntegerField(db_column="OTHER")
    historical = BooleanField()

    objects = GradeQuerySet.as_manager()

    def __str__(self):
        return (
            f"{self.a_plus} {self.a} {self.a_minus}, "
            f"{self.b_plus} {self.b} {self.b_minus}, "
            f"{self.c_plus} {self.c} {self.c_minus}, "
            f"{self.d_plus} {self.d} {self.d_minus}, "
            f"{self.f} {self.w} {self.other}"
        )

class GroupmeUser(Model):
    user = ForeignKey(User, CASCADE)
    groups = ManyToManyField("GroupmeGroup")
    access_token = CharField(max_length=100)
    groupme_username = CharField(max_length=100)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"groupme user {self.groupme_username} (planetterp user {self.user})"


class GroupmeGroup(Model):
    name = CharField(max_length=191)
    group_id = IntegerField()
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"groupme group {self.name}"


class Organization(Model):
    name = TextField()
    website_url = TextField()
    alt_text = TextField()

    def __str__(self):
        return f"{self.name} ({self.website_url})"


class ProfessorCourse(Model):
    professor = ForeignKey(Professor, CASCADE)
    course = ForeignKey(Course, RESTRICT)
    recent_semester = CharField(max_length=6, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.professor} teaching {self.course}"


class DiscussionReply(Model):
    user = ForeignKey(User, CASCADE)
    discussion = ForeignKey(Discussion, RESTRICT)
    content = TextField()
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply on {self.discussion} by {self.user}"


class ResetCode(Model):
    user = ForeignKey(User, CASCADE)
    reset_code = CharField(max_length=100)
    expires_at = DateTimeField()
    invalid = BooleanField(default=False)


class SectionMeeting(Model):
    section = ForeignKey(Section, RESTRICT)
    days = TextField()
    start_time = TextField()
    end_time = TextField()
    building = TextField(null=True)
    room = TextField(null=True)
    type = TextField(null=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"meeting {self.days} {self.start_time}-{self.end_time} at {self.building}"


class UserSchedule(Model):
    user = ForeignKey(User, CASCADE)
    section = ForeignKey(Section, RESTRICT)
    active = BooleanField(default=True)
    semester = CharField(max_length=6)
    loadtime = FloatField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"schedule by {self.user} for {self.semester}"


class View(Model):
    page = TextField()
    status = TextField()
    ip = TextField()
    user_agent = TextField()
    method = CharField(max_length=10)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"viewed {self.page} on {self.created_at}"
