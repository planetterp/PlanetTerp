from enum import Enum, auto
from functools import lru_cache, wraps
from home.models import Professor, Review
import time

from discord_webhook import DiscordWebhook
from discord_webhook.webhook import DiscordEmbed

from planetterp.config import discord_webhook_updates_url

def semester_name(semester_number):
    seasons = {"01": "Spring", "05": "Summer", "08": "Fall", "12": "Winter"}
    season = seasons[semester_number[4:6]]

    year = int(semester_number[:4])

    # The winter semester starting in january 2021 is actually called 202012
    # internally, not 202112, so return the next year for winter to adjust.
    if season == "Winter":
        year += 1

    return f"{season} {year}"

def semester_number(semester_name: str):
    seasons = {"Spring": "01", "Summer": "05", "Fall": "08", "Winter": "12"}
    season, year = semester_name.strip().split(' ')

    if season == "Winter":
        year = int(year) + 1

    return f"{year}{seasons[season]}"

# This list must be kept in ascending order, as other parts of the codebase rely
# on the ordering.
RECENT_SEMESTERS = ["202008", "202012", "202101", "202105", "202108"]

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

def send_updates_webhook(*, include_professors=True, include_reviews=True):
    if not discord_webhook_updates_url:
        return

    title = ""
    if include_professors:
        num_professors = Professor.objects.filter(status=Professor.Status.PENDING).count()
        title += f"{num_professors} unverified professor(s)"
    if include_professors and include_reviews:
        title += " and "
    if include_reviews:
        num_reviews = Review.objects.filter(status=Review.Status.PENDING).count()
        title += f"{num_reviews} unverified review(s)"

    webhook = DiscordWebhook(url=discord_webhook_updates_url)
    embed = DiscordEmbed(title=title, description="\n", url="https://planetterp.com/admin")

    webhook.add_embed(embed)
    webhook.execute()
