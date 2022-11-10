from enum import Enum

from django.contrib.auth.models import (AbstractUser,
    UserManager as DjangoUserManager)
from django.utils.safestring import mark_safe
from django.utils.functional import cached_property
from django.urls import reverse
from django.core import validators
from django.db.models import (Model, CharField, DateTimeField, TextField,
    IntegerField, BooleanField, ForeignKey, PositiveIntegerField, EmailField,
    CASCADE, ManyToManyField, SlugField, TextChoices, FloatField, Manager,
    QuerySet, Sum, UniqueConstraint, Index, Count)

class GradeQuerySet(QuerySet):

    def exclude_pf(self):
        from home.utils import PF_SEMESTERS
        ret = self
        for semester in PF_SEMESTERS:
            ret = ret.exclude(semester=semester)
        return ret

    def average_gpa(self):
        return self._apply_average_gpa(self.aggregate)["average_gpa"]

    def average_gpa_annotate(self):
        """
        Exposed primarily for queries which require performance and need the
        average_gpa annotated, not returned directly.
        """
        return self._apply_average_gpa(self.annotate)

    def _apply_average_gpa(self, func):
        """
        A generic way to calculate average_gpa, either as an aggregate or as an
        annotation. Not intended for external use.
        """
        return func(
            average_gpa=(
                (Sum("a_plus") * 4  + Sum("a") * 4 + Sum("a_minus") * 3.7 +
                Sum("b_plus") * 3.3 + Sum("b") * 3 + Sum("b_minus") * 2.7 +
                Sum("c_plus") * 2.3 + Sum("c") * 2 + Sum("c_minus") * 1.7 +
                Sum("d_plus") * 1.3 + Sum("d") * 1 + Sum("d_minus") * 0.7)
                /
                # TODO switch back to using `num_students - other` once
                # discrepancies in `num_students` are fixed
                (Sum("a_plus") + Sum("a") + Sum("a_minus") + Sum("b_plus") +
                 Sum("b") + Sum("b_minus") +Sum("c_plus")  + Sum("c") +
                 Sum("c_minus") + Sum("d_plus")  + Sum("d") + Sum("d_minus") +
                 Sum("f") + Sum("w"))
            )
        )

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

class RecentGradeManager(Manager):
    def get_queryset(self):
        from home.utils import Semester
        # TODO dont hardcode recent semester
        return super().get_queryset().filter(semester__gte=Semester(201201))

class RecentCourseManager(Manager):
    def get_queryset(self):
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
        return super().get_queryset().filter(is_recent=True)

class UserManager(DjangoUserManager):
    def create_ourumd_user(self, username, email=None, **kwargs):
        # password=None is equivalent to calling user#set_unusable_password()
        return self.create_user(username, email=email, password=None,
            from_ourumd=True, **kwargs)


class ReviewVerifiedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Review.Status.VERIFIED)
class ReviewPendingManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Review.Status.PENDING)
class ReviewRejectedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Review.Status.REJECTED)

class ProfessorVerifiedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Professor.Status.VERIFIED)
class ProfessorPendingManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Professor.Status.PENDING)
class ProfessorRejectedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Professor.Status.REJECTED)

class SemesterField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    # called when reading from the database
    def from_db_value(self, value, _expression, _connection):
        # avoid circular import
        from home.utils import Semester

        if value is None:
            return None
        return Semester(value)

    # called when writing back to the database
    def get_prep_value(self, value):
        from home.utils import Semester
        if value is None:
            return None
        if not isinstance(value, Semester):
            raise ValueError(f"Expected a Semester object; found {type(value)} "
                "instead.")
        return str(value.number())

    # called when deserializing, and by a form's `clean` method
    def to_python(self, value):
        from home.utils import Semester

        if isinstance(value, Semester):
            return value
        if value is None:
            return None
        return Semester(value)

    # called when serialization
    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

class Course(Model):
    department = CharField(max_length=4)
    course_number = CharField(max_length=6)
    # I fought against adding this as a column for a long time, but django wins;
    # it's simply easier if the course name is a first-class citizen, instead of
    # having to be explicitly promoted with
    # `.annotate(name=Concat("department", "course_number"))`. This also allows
    # us to apply an index to this field, something which is not possible with
    # the concatenated version.
    name = CharField(max_length=10)
    title = TextField(null=True)
    credits = IntegerField(null=True)
    description = TextField(null=True)
    created_at = DateTimeField(auto_now_add=True)
    # determining whether a course is recent or not can actually be extremely
    # expensive (for reasons I don't quite understand - lacking proper
    # indices?). Since recency changes so infrequently, we'll cache it and
    # update it manually with a custom management command (`updaterecency`).
    is_recent = BooleanField(default=False)

    professors = ManyToManyField("Professor", blank=True,
        through="ProfessorCourse")

    recent = RecentCourseManager()
    unfiltered = Manager()

    def save(self, *args, **kwargs):
        # `name` is essentially a computed field, and will never have a value
        # other than CONCAT("department", "course_number"). Ensure that this
        # invariant holds here.
        self.name = f"{self.department}{self.course_number}"
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name"], name="unique_name")
        ]
        indexes = [
            Index(fields=["name"])
        ]
        default_manager_name = "unfiltered"

    def average_gpa(self):
        return self.grade_set(manager="recent").all().average_gpa()

    def get_absolute_url(self):
        return reverse("course", kwargs={"name": self.name})

    def __str__(self):
        return self.name


class Professor(Model):
    class Type(TextChoices):
        PROFESSOR = ("professor", "Professor")
        TA = ("TA", "TA")

    class Status(TextChoices):
        VERIFIED = "verified"
        PENDING = "pending"
        REJECTED = "rejected"

    # as a safety precuation, do away with the default "objects" manager on
    # models which have a verification status (Professor and Review). This way,
    # a consumer must access `Professor.unfiltered` explicitly
    # (`Professor.objects` will error), which makes them reconsider whether they
    # really want an "unfiltered" queryset (all objects in the database), or
    # only the verified/pending/rejected reviews.
    verified = ProfessorVerifiedManager()
    pending = ProfessorPendingManager()
    rejected = ProfessorRejectedManager()
    unfiltered = Manager()

    name = CharField(max_length=100)
    slug = SlugField(max_length=100, null=True, unique=True)
    type = CharField(choices=Type.choices, max_length=50)
    status = CharField(choices=Status.choices, default=Status.PENDING,
        max_length=50)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        default_manager_name = "unfiltered"

    @cached_property
    def average_rating(self):
        return (
            self.review_set(manager="verified")
            .aggregate(
                average_rating=Sum("rating", output_field=FloatField()) / Count("*")
            )
        )["average_rating"]

    def get_absolute_url(self):
        return reverse("professor", kwargs={"slug": self.slug})

    def __str__(self):
        return f"{self.name} ({self.id})"


class ProfessorAlias(Model):
    class Meta:
        db_table = "home_professor_alias"

    alias = CharField(max_length=100)
    professor = ForeignKey(Professor, CASCADE)


class ProfessorSection(Model):
    class Meta:
        db_table = "home_professor_section"

    professor = ForeignKey(Professor, CASCADE, null=True)
    section = ForeignKey("Section", CASCADE)


class Section(Model):
    course = ForeignKey(Course, CASCADE)
    professors = ManyToManyField(Professor, through=ProfessorSection)
    semester = SemesterField()
    section_number = CharField(max_length=8)
    seats = PositiveIntegerField()
    available_seats = PositiveIntegerField()
    waitlist = PositiveIntegerField()
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course} ({self.section_number}) taught by {self.professors.name}"


class User(AbstractUser):
    objects = UserManager()

    send_review_email = BooleanField(default=True)

    # accounts which are from ourumd are given an unusable password so nobody
    # can log in to the accounts
    from_ourumd = BooleanField(default=False)

    username = CharField(
        max_length=22,
        unique=True,
        help_text="Once a username is set, it cannot be changed.",
        validators=[
            validators.RegexValidator("^[\w\d]+$", "Username can only contain "
                "alphanumeric characters and underscores"),
            validators.MaxLengthValidator(22, "Username must be less than 20 characters"),
            validators.MinLengthValidator(2, "Username must be at least 2 characters")
        ],
        error_messages={
            "required": "You must enter a username",
            "unique": "A user with that username already exists."
        }
    )

    email = EmailField(
        unique=True,
        null=True,
        blank=True,
        validators=[validators.validate_email],
        error_messages={
            "unique": mark_safe(
                'A user with that email already exists. If you forgot your <br /> '
                'password, please <a href="" data-toggle="modal" '
                'data-target="#password-reset-modal" style="color: red;"> '
                '<strong>reset your password</strong></a> or login on the left.'
                )
        }
    )

    password = CharField(
        max_length=128,
        validators=[
            validators.MinLengthValidator(8, "Password must be at least 8 characters")
        ],
        error_messages={
            "required": "You must enter a password"
        }
    )

    # Workaround to force CharField to store empty values as NULL instead of ''
    # https://stackoverflow.com/a/38621160
    def save(self, *args, **kwargs):
        if not self.email or self.email.strip() == '':
            self.email = None

        super().save(*args, **kwargs)


class AuditLog(Model):
    class Meta:
        db_table = "home_audit_log"

    username = TextField()
    summary = TextField()
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.summary} (action by {self.username})"


class Gened(Model):
    GENEDS = [
        "FSAW", "FSAR", "FSMA", "FSOC", "FSPW", "DSHS", "DSHU", "DSNS", "DSNL",
        "DSSP", "DVCC", "DVUP", "SCIS"
    ]

    course = ForeignKey(Course, CASCADE)
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
        A_PLUS = ("A+", "A+")
        A = ("A", "A")
        A_MINUS = ("A-", "A-")

        B_PLUS = ("B+", "B+")
        B = ("B", "B")
        B_MINUS = ("B-", "B-")

        C_PLUS = ("C+", "C+")
        C = ("C", "C")
        C_MINUS = ("C-", "C-")

        D_PLUS = ("D+", "D+")
        D = ("D", "D")
        D_MINUS = ("D-", "D-")

        F = ("F", "F")
        P = ("P", "P")
        W = ("W", "W")
        XF = ("XF", "XF")

    verified = ReviewVerifiedManager()
    pending = ReviewPendingManager()
    rejected = ReviewRejectedManager()
    unfiltered = Manager()

    professor = ForeignKey(Professor, CASCADE)
    course = ForeignKey(Course, CASCADE, null=True, blank=True)
    user = ForeignKey(User, CASCADE, null=True, blank=True)
    updater = ForeignKey(User, CASCADE, null=True, blank=True, related_name="updater")
    content = TextField()
    rating = IntegerField()
    grade = CharField(max_length=2, null=True, blank=True,
        choices=Grades.choices)
    status = CharField(choices=Status.choices, default=Status.PENDING,
        max_length=50)
    anonymous = BooleanField()
    from_ourumd = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        default_manager_name = "unfiltered"
        indexes = [
            Index(fields=["status"])
        ]

class Grade(Model):
    POSSIBLE_GRADES = [choice[0] for choice in Review.Grades.choices]
    VOWEL_GRADES = ["A", "A-", "A+", "F"]

    course = ForeignKey(Course, CASCADE)
    professor = ForeignKey(Professor, CASCADE, null=True)
    semester = SemesterField()
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

    recent = RecentGradeManager.from_queryset(GradeQuerySet)()
    unfiltered = Manager.from_queryset(GradeQuerySet)()

    class Meta:
        # TODO enforce a constraint asserting that
        # `num_students = a_plus a + ... + other` once discrepancies in the
        # database are fixed
        constraints = [
            UniqueConstraint(
                fields=["course", "semester", "section"],
                name="unique_course_semester_section"
            )
        ]
        indexes = [
            Index(fields=["semester"]),
            Index(fields=["section"]),
        ]
        default_manager_name = "unfiltered"

    def __str__(self):
        return (
            f"{self.a_plus} {self.a} {self.a_minus}, "
            f"{self.b_plus} {self.b} {self.b_minus}, "
            f"{self.c_plus} {self.c} {self.c_minus}, "
            f"{self.d_plus} {self.d} {self.d_minus}, "
            f"{self.f} {self.w} {self.other}"
        )

class Organization(Model):
    name = TextField()
    url = TextField()
    alt_text = TextField()
    image_file_name = TextField(null=True)
    width = IntegerField(null=True)
    height = IntegerField(null=True)

    def __str__(self):
        return f"{self.name} ({self.website_url})"


class ProfessorCourse(Model):
    class Meta:
        db_table = "home_professor_course"
        # we need fast lookups on recent_semester, eg for our
        # `RecentCourseManager`
        indexes = [
            Index(fields=["recent_semester"])
        ]

    professor = ForeignKey(Professor, CASCADE)
    course = ForeignKey(Course, CASCADE)
    recent_semester = SemesterField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.professor} teaching {self.course}"


class ResetCode(Model):
    class Meta:
        db_table = "home_reset_code"

    user = ForeignKey(User, CASCADE)
    reset_code = CharField(max_length=100)
    expires_at = DateTimeField()
    invalid = BooleanField(default=False)


class SectionMeeting(Model):
    class Meta:
        db_table = "home_section_meeting"

    section = ForeignKey(Section, CASCADE)
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
    class Meta:
        db_table = "home_user_schedule"

    user = ForeignKey(User, CASCADE)
    section = ForeignKey(Section, CASCADE, null=True)
    active = BooleanField(default=True)
    semester = SemesterField()
    loadtime = FloatField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"schedule by {self.user} for {self.semester}"
