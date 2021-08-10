# This script essentially sets user.email = None for every user with an email
#   that appears in the db more than once, effectively making a user's email
#   unique.
#
# Use the "django" command-line arg if you've already converted your db to django
#   via the webpy_to_django.py script. Otherwise, run without any command-line args

import os
import sys
from django.core.wsgi import get_wsgi_application
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

if "django" in sys.argv:
    from django.db.models import Count
    from home.models import User
    print("Using django...")
    User.objects.filter(email="").update(email=None)
    # https://stackoverflow.com/a/36064192
    dups = User.objects.values('email').annotate(email_count=Count('email')).filter(email_count__gt=1)
    for dup in dups:
        obj = User.objects.filter(email=dup['email']).order_by('pk').update(email=None)
    print("Done")
else:
    import web
    from planetterp.config import USER, PASSWORD
    print("Using web.py...")
    db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
    db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')
    db.query('UPDATE planetterp.user SET email = NULL WHERE email = ""')
    # https://stackoverflow.com/a/14302701
    db.query('''
        UPDATE planetterp.user
        SET email = NULL
        WHERE email IN (
            SELECT email FROM (SELECT email FROM planetterp.user) AS x
            GROUP BY email
            HAVING COUNT((email)) > 1
        );
    ''')
    print("Done")
