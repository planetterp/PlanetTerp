from enum import Enum, auto
from functools import wraps, total_ordering
import time
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from datetime import datetime

from django.urls import reverse
from django.template.defaultfilters import pluralize

from discord_webhook import DiscordWebhook
from discord_webhook.webhook import DiscordEmbed
from google.oauth2 import service_account
from googleapiclient.discovery import build

from planetterp.config import (WEBHOOK_URL_UPDATE, EMAIL_HOST_USER,
    EMAIL_SERVICE_ACCOUNT_CREDENTIALS, WEBHOOK_FREQUENCY)

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

    def __str__(self):
        return str(self.number())

    @classmethod
    def from_name(cls, name):
        season = name.split(" ")[0]
        year = name.split(" ")[1]
        number = cls.SEASONS[season.lower()]
        return Semester(f"{year}{number:02}")

    @staticmethod
    def current():
        now = datetime.now()
        # spring (current year)
        if now.month < 3:
            semester = "01"
            year = now.year
        # fall
        if 3 <= now.month <= 9:
            semester = "08"
            year = now.year
        # spring (of next year)
        if 9 < now.month:
            semester = "01"
            year = now.year + 1

        return Semester(f"{year}{semester}")

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

# We're going to handroll our own ttl cache instead of using python's
# `lru_cache` with a time salt (which was the original implementation), for two
# reasons:
# * if the ttl has expired, we want to still return the cached result
#   immediately, and then silently update the cached value so the updated result
#   is returned for future calls. This means that the first unlucky soul to
#   trigger a ttl cache after the ttl expires won't be hit with a delay, but
#   will cause a recomputation.
# * we want to be able to force update values, even if the ttl hasn't expired
#   yet. This is useful for scenarios where we eg add new grades and want to
#   update all grade graphs immediately.
# XXX: as we've handrolled our own (unbounded) cache implementation, this has
# the potential to cause memory leaks. Investigate this first if memory leaks
# arise in the future.
_ttl_cache = {}
def ttl_cache(max_age):
    """
    An @cache, but instead of caching indefinitely, only caches for `max_age`
    seconds.

    That is, at the first function call with certain arguments, the result is
    computed and cached. Then, when the funcion is called again with those
    arguments, if it has not been more than `max_age` seconds since the first
    call, the cached value is returned. Otherwise, the cached value is still
    returned, but the value is recomputed on a separate thread. This ensures
    that the user which triggers the recomputation will not experience a delay,
    but *will* update the value for the next users.

    Warnings
    --------
    This function does not actually guarantee that the result will be cached for
    exactly `max_age` seconds. Rather it only guarantees that the result will be
    cached for at *most* `max_age` seconds. This is to simplify implementation.
    """
    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):
            time_salt = time.time() // max_age
            # make kwargs hashable
            frozen_kwargs = tuple(sorted(kwargs.items()))
            key = (function, args, frozen_kwargs)
            if key in _ttl_cache:
                (time_salt_cached, value) = _ttl_cache[key]

                if time_salt_cached < time_salt:

                    # recompute the new value in a separate thread, but return
                    # the cached value immediately so we don't delay the
                    # response.
                    def recompute():
                        value = function(*args, **kwargs)
                        _ttl_cache[key] = (time_salt, value)
                    thread = Thread(target=recompute)
                    thread.start()
                    return value

                return value

            value = function(*args, **kwargs)
            _ttl_cache[key] = (time_salt, value)
            return value

        return wrapper
    return decorator

def recompute_ttl_cache():
    # TODO this is an imperfect implementation because although this will
    # recompute all values in the ttl cache, it will take two calls per cached
    # key for any difference to be perceived. The first call we see that we set
    # time_salt to 0 here and so will recompute the value, but it will return
    # the previously cached value before it does so. Only on the second call
    # will we return the truly updated value.
    for key, value in _ttl_cache.copy().items():
        (_time_salt, *values) = value
        # set time_salt to 0 to force recomputation on next call
        value = (0, *values)
        _ttl_cache[key] = value

def send_updates_webhook(request):
    # avoid circular imports
    from home.models import Professor, Review
    if not WEBHOOK_URL_UPDATE:
        return

    num_professors = Professor.pending.count()
    num_reviews = Review.pending.count()

    title = f"{num_reviews} unverified review{pluralize(num_reviews)}"

    if num_professors:
        title += f" and {num_professors} unverified professor{pluralize(num_professors)}"

    webhook = DiscordWebhook(url=WEBHOOK_URL_UPDATE)
    embed = DiscordEmbed(title=title, description="\n",
        url=request.build_absolute_uri(reverse("admin")))

    webhook.add_embed(embed)

    if num_reviews % WEBHOOK_FREQUENCY != 0:
        return

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
