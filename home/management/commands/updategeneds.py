import requests

from django.core.management import BaseCommand

from home.models import Course, Gened

class Command(BaseCommand):
    def __init__(self):
        super().__init__()

    def handle(self, *args, **options):
        pass
