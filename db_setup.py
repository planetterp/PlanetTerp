# This is an all-in-one script to get your db up and running. It assumes you
#   already have data in your webpy tables to be migrated to the django tables.
# * Export your db to have a backup before running.
#
# Use the command-line arg "full" to perform a complete migration from
#   web.py to django.
# Use without any command-line args to update your django db (do this if you've
#   already migrated your db from web.py and only need to update the user model)

import os
import sys
import web
from django.core.wsgi import get_wsgi_application
from planetterp.config import USER, PASSWORD

# https://stackoverflow.com/a/43391786
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

from home.models import User

if "full" in sys.argv:
    print("Starting full setup...\nWiping django tables...")
    os.system("python3 wipe_django.py")


    print("Updating web.py tables...")
    db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
    db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')

    # Make the changes mentioned in webpy_to_django.py
    db.query('DELETE FROM planetterp.professor_courses WHERE professor_id < 0')
    db.query('DELETE FROM planetterp.reviews WHERE professor_id < 0')
    db.query('DELETE FROM planetterp.grades WHERE professor_id < 0')
    db.query('DELETE FROM planetterp.grades_historical WHERE professor_id < 0')
    db.query('DELETE FROM planetterp.professors WHERE id < 0')

    db.query('UPDATE planetterp.professors SET verified = 1 WHERE verified IS NULL')
    db.query('UPDATE planetterp.reviews SET verified = 1 WHERE verified IS NULL')
    db.query("UPDATE planetterp.users SET email = NULL WHERE CHARACTER_LENGTH(email) > 254 OR email = ''")


    print("Migrating to django. This might take a few minutes...")
    os.system("python3 webpy_to_django.py")
else:
    print("Starting django setup...\nUpdating user emails...")
    User.objects.filter(email='').update(email=None)
    os.system("python3 manage.py makemigrations")
    os.system("python3 manage.py migrate")


print("Done")
