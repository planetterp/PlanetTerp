# This is the django migration script. Don't run any of the files other files

import os

print("Migrating DB to django\nWiping django tables...")
os.system("python3 reset_django.py")

print("DB wiped successfully\nPreparing DB for migration...")
os.system("python3 db_setup.py")
print("DB prepared successfully\nMigrating to django. This might take a few minutes...")

os.system("python3 webpy_to_django.py")

print("Sucess!")
