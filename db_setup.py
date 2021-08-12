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


# Add a new column will be used to keep track of users who get their email set
#   to '' in case we decide that we want to notify those users
#   (via a notification on their profile page) that their email was reset.

# See first comment: https://dba.stackexchange.com/a/169478
query = db.query("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='planetterp' AND TABLE_NAME='users' AND COLUMN_NAME='email_changed'")
if len(query) == 0:
    db.query('ALTER TABLE planetterp.users ADD email_changed TINYINT(1) DEFAULT 0')

# Set user.email = '' for every user with an email that appears in the db more
#   than once. This is necessary to account for making a user's email unique.
# https://stackoverflow.com/a/14302701
db.query('''
    UPDATE planetterp.users
    SET email = '', email_changed = 1, send_review_email = 0
    WHERE email IN (
        SELECT email FROM (SELECT email FROM planetterp.users WHERE email != '') AS x
        GROUP BY email
        HAVING COUNT((email)) > 1
    )
''')


print("Migrating to django. This might take a few minutes...")
os.system("python3 webpy_to_django.py")

print("Done")
