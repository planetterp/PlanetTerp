import os
import web
from django.core.wsgi import get_wsgi_application
from planetterp.config import USER, PASSWORD

# https://stackoverflow.com/a/43391786
os.environ['DJANGO_SETTINGS_MODULE'] = 'planetterp.settings'
application = get_wsgi_application()

web.config.debug = False
db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')

print("  Dropping useless tables...")
db.query('''
    DROP TABLE IF EXISTS
        planetterp.views,
        planetterp.discussions,
        planetterp.fall_2020_searches,
        planetterp.replies,
        planetterp.groupme_auth,
        planetterp.groupme_user_groups,
        planetterp.courses_copy,
        planetterp.grades2,
        planetterp.professor_courses_copy,
        planetterp.professors_copy,
        planetterp.reviews_copy,
        planetterp.organizations_review
    ''')

print("  Handling werid edge cases...")
db.query("UPDATE planetterp.users SET email = NULL WHERE CHARACTER_LENGTH(email) > 254 OR email = ''")
db.query('DELETE FROM planetterp.reviews WHERE professor_id < 0')
db.query('DELETE FROM planetterp.grades WHERE professor_id < 0')
db.query('DELETE FROM planetterp.grades_historical WHERE professor_id < 0')
db.query('DELETE FROM planetterp.professor_courses WHERE professor_id < 0')
db.query('DELETE FROM planetterp.professors WHERE id < 0')

print("  Making ourumd reviewer_names unique...")
to_rename = db.query("""SELECT DISTINCT reviewer_name FROM planetterp.reviews
            INNER JOIN planetterp.users ON reviews.reviewer_name = users.username
            WHERE from_ourumd = 1 and reviewer_name != "Anonymous"
""")
for row in to_rename:
    old_name = row["reviewer_name"]
    new_name = f"{old_name}_ourumd"
    db.query("UPDATE planetterp.reviews SET reviewer_name = $new_name WHERE reviewer_name = $old_name AND from_ourumd = 1",
        vars={"new_name": new_name, "old_name": old_name})


# Merge professors with duplicate slugs and delete all duplicate professors.
# Only keep the professor that was created first
print("  Removing duplicate professors...")
professors = db.query('SELECT * FROM planetterp.professors WHERE slug IS NOT NULL ORDER BY created DESC')
for professor in professors:
    query = db.query('SELECT id FROM planetterp.professors WHERE slug = $slug ORDER BY created DESC', vars={"slug": professor["slug"]})
    p_ids = [record["id"] for record in query]

    if len(p_ids) > 1:
        kwargs = {
            "new_id": p_ids[-1],
            "curr_id": professor["id"]
        }

        db.query('UPDATE planetterp.reviews SET professor_id = $new_id WHERE professor_id = $curr_id', vars=kwargs)
        db.query('UPDATE planetterp.grades SET professor_id = $new_id WHERE professor_id = $curr_id', vars=kwargs)
        db.query('UPDATE planetterp.grades_historical SET professor_id = $new_id WHERE professor_id = $curr_id', vars=kwargs)
        db.query('UPDATE planetterp.professor_courses SET professor_id = $new_id WHERE professor_id = $curr_id', vars=kwargs)
        db.query('DELETE FROM planetterp.professors WHERE id = $id', vars={"id": professor["id"]})
