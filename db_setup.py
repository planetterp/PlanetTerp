# This is an all-in-one script to get your db up and running. It assumes you
#   already have data in your webpy tables to be migrated to the django tables.
# * Export your db to have a backup before running.

import os
import web
from planetterp.config import USER, PASSWORD

print("Wiping django tables...")
os.system("python3 wipe_django.py")

print("Updating web.py tables...")
db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')

# Make the changes mentioned in webpy_to_django.py
db.query('DELETE FROM planetterp.professors WHERE id < 0')
db.query('UPDATE planetterp.professors SET verified = 1 WHERE verified IS NULL')
db.query('UPDATE planetterp.reviews SET verified = 1 WHERE verified IS NULL')
db.query("UPDATE planetterp.users SET email = '' WHERE CHARACTER_LENGTH(email) > 254")




print("Migrating to django. This might take a few minutes...")
os.system("python3 webpy_to_django.py")

print("Done")
