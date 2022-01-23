from enum import Enum, auto
from functools import lru_cache, wraps, total_ordering
import time
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from datetime import datetime

from django.urls import reverse

from discord_webhook import DiscordWebhook
from discord_webhook.webhook import DiscordEmbed
from google.oauth2 import service_account
from googleapiclient.discovery import build

from home.models import Professor, Review
from planetterp.config import (WEBHOOK_URL_UPDATE, EMAIL_HOST_USER,
    EMAIL_SERVICE_ACCOUNT_CREDENTIALS)

@total_ordering
class Semester:
    SPRING = 1
    SUMMER = 5
    FALL = 8
    WINTER = 12

    SEASONS = {
        "spring": SPRING,
        "summer": SUMMER,
        "fall": FALL,
        "winter": WINTER
    }

    SEASONS_REVERSE = {v: k for k, v in SEASONS.items()}

    def __init__(self, semester):
        semester = str(semester)
        self.year = int(semester[0:4])
        self.season_number = int(semester[4:6])
        self.season = self.SEASONS_REVERSE[self.season_number]

        # TODO more accurate measure
        self.recent = datetime.now().year - self.year <= 1

    def __hash__(self):
        return hash((self.year, self.season_number))

    def __eq__(self, other):
        return (self.year == other.year and
            self.season_number == other.season_number)

    def __le__(self, other):
        if self.year < other.year:
            return True
        if self.year > other.year:
            return False
        return self.season_number < other.season_number

    @classmethod
    def from_name(cls, name):
        season = name.split(" ")[0]
        year = name.split(" ")[1]
        number = cls.SEASONS[season.lower()]
        return Semester(f"{year}{number:02}")

    @staticmethod
    def current():
        now = datetime.now()
        # fall
        if 3 >= now.month >= 9:
            semester = "08"
        # spring
        else:
            semester = "01"

        return Semester(f"{now.year}{semester}")

    def name(self, *, year_first=False, short=False):
        year = self.year
        # The winter semester starting in january 2021 is actually called 202012
        # internally, not 202112, so return the next year for winter to adjust.
        if self.season_number == Semester.WINTER:
            year += 1

        season = self.season.capitalize()
        if short:
            # use first letter as acronym
            season = season[0]

        if year_first:
            return f"{year} {season}"
        return f"{season} {year}"

    def number(self):
        return int(f"{self.year}{self.season_number:02}")

# If you add additional semesters here, you will also need to add additional
# semesters to grades.html in the submitCourseSearch method.
PF_SEMESTERS = [Semester(202001), Semester(202101)]

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

def send_updates_webhook(request, *, include_professors=True, include_reviews=True):
    if not WEBHOOK_URL_UPDATE:
        return

    title = ""
    if include_professors:
        num_professors = Professor.pending.count()
        title += f"{num_professors} unverified professor(s)"
    if include_professors and include_reviews:
        title += " and "
    if include_reviews:
        num_reviews = Review.pending.count()
        title += f"{num_reviews} unverified review(s)"

    webhook = DiscordWebhook(url=WEBHOOK_URL_UPDATE)
    embed = DiscordEmbed(title=title, description="\n",
        url=request.build_absolute_uri(reverse("admin")))

    webhook.add_embed(embed)
    webhook.execute()



EMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

gmail_service_account = None
if EMAIL_SERVICE_ACCOUNT_CREDENTIALS:
    credentials = service_account.Credentials.from_service_account_info(
        EMAIL_SERVICE_ACCOUNT_CREDENTIALS, scopes=EMAIL_SCOPES,
        subject=EMAIL_HOST_USER)

    gmail_service_account = build("gmail", "v1", credentials=credentials)

def send_email(user, subject, message_text):
    # sending email can be a highly expensive operation, so we do it in a
    # separate thread by default. If you require a blocking operation, see
    # `send_mail_sync.`
    thread = Thread(target=lambda: send_mail_sync(user, subject, message_text))
    thread.start()

def send_mail_sync(user, subject, message_text):
    if not user.email:
        return
    # prefer sending using the service account if it's set up
    if gmail_service_account:
        # alternative means we're sending both html and plaintext
        # https://stackoverflow.com/q/3902455
        message = MIMEMultipart("alternative")
        message["to"] = user.email
        message["from"] = "admin@planetterp.com"
        message["subject"] = subject

        # plaintext is provided as a fallback if the client doesn't support html.
        # important: we have to add the html part last so it is the first one the
        # client attempts to display.
        # # https://realpython.com/python-send-email/#including-html-content
        text_part = MIMEText(message_text, "plain")
        html_part = MIMEText(message_text, "html")
        message.attach(text_part)
        message.attach(html_part)

        # https://stackoverflow.com/a/46668827
        message_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message = {'raw': message_b64}

        # pylint: disable=no-member
        gmail_service_account.users().messages().send(userId="me", body=message).execute()
    # otherwise, fall back to django's email setup
    elif EMAIL_HOST_USER:
        user.email_user(
            subject,
            message_text,
            html_message=message_text
        )
