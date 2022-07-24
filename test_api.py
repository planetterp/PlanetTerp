import requests
import os
from django.core.wsgi import get_wsgi_application
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()
from home.models import Course
BASE_MASTER = "https://api.planetterp.com/v1/"
BASE_DJANGO = "http://127.0.0.1:8000/api/v1/"

def get(url, params={}):
    master = requests.get(f"{BASE_MASTER}{url}", params)
    django = requests.get(f"{BASE_DJANGO}{url}", params)
    return (master.json(), django.json())

for course in Course.recent.order_by("?")[0:1000]:
    print(course)
    params = {"name": course.name}
    (master, django) = get("course", params=params)
    for attr in master.keys():
        if attr == "average_gpa":
            if master[attr] is None and django[attr] is None:
                continue
            if master[attr] is None and django[attr] == 0:
                continue
            assert abs(master[attr] - django[attr]) < 0.0001
            continue
        assert master[attr] == django[attr], f"{attr}: {master[attr]} vs {django[attr]}"
