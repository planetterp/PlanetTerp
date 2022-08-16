# This is the django migration script. Don't run any of the files other files

import os

SUCCESS = 0
print("Migrating DB to django:\nResetting django tables...")

ret = os.system("sudo python3.9 reset_django.py")
if ret != SUCCESS:
    print("\nDjango reset failed!")
    exit()

print("DB successfully reset\nPreparing DB for migration...")

ret = os.system("sudo python3.9 db_setup.py")
if ret != SUCCESS:
    print("\nDB setup failed!")
    exit()

print("DB prepared successfully\nMigrating to django. This might take a few minutes...")

ret = os.system("sudo python3.9 webpy_to_django.py")
if ret != SUCCESS:
    print("\nwebpy_to_django to failed!")
    exit()

print("\nSuccess!")
