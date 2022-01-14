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
    db.query("UPDATE planetterp.reviews SET reviewer_name = $new_name WHERE reviewer_name = $old_name",
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

# Select all historical courses that are NOT in planetterp.courses.
# Inverse join: https://www.sitepoint.com/community/t/how-to-do-an-inverse-join/3224/2
print("  Adding neccessary historical courses to courses (will take a while)...")
distinct_historical_courses = db.query(
    "SELECT planetterp.courses_historical.id, planetterp.courses_historical.department, planetterp.courses_historical.course_number, planetterp.courses_historical.created FROM planetterp.courses_historical LEFT JOIN planetterp.courses ON planetterp.courses.department = planetterp.courses_historical.department AND planetterp.courses.course_number = planetterp.courses_historical.course_number WHERE planetterp.courses.department IS NULL AND planetterp.courses.course_number IS NULL"
)

max_id = int(db.query('SELECT MAX(id) FROM planetterp.courses')[0]['MAX(id)']) + 1
for idx, course in enumerate(distinct_historical_courses):
    # update the course_id for relevant historical grades so they refer to
    # the right course
    db.query('UPDATE planetterp.grades_historical SET course_id = $new_id WHERE course_id = $curr_id',
        vars={
            "new_id": str(max_id + idx),
            "curr_id": course['id']
        }
    )

    # insert historical courses into planetterp.courses
    db.query(
        'INSERT INTO planetterp.courses (department, course_number, created) VALUES ($department, $course_number, $created)',
        vars={
            "department": course["department"],
            "course_number": course["course_number"],
            "created": course["created"]
        }
    )

# Repeat the above process of updating historic_grades.course_id for the courses
# that already exist in planetterp.courses
historical_courses = db.query(
    'SELECT planetterp.courses_historical.id FROM planetterp.courses_historical LEFT JOIN planetterp.courses ON planetterp.courses.department = planetterp.courses_historical.department AND planetterp.courses.course_number = planetterp.courses_historical.course_number'
)

max_id = int(db.query('SELECT MAX(id) FROM planetterp.courses')[0]['MAX(id)']) + 1
for idx, course in enumerate(historical_courses):
    db.query('UPDATE planetterp.grades_historical SET course_id = $new_id WHERE course_id = $curr_id',
        vars={
            "new_id": str(max_id + idx),
            "curr_id": course['id']
        }
    )

# Move all historical grades to planetterp.grades
print("  Moving all historical grades to grades (will take a while)...")
grades = db.query('SELECT * FROM planetterp.grades_historical')
for grade in grades:
    db.query(
        'INSERT INTO planetterp.grades (semester, course_id, section, professor_id, num_students, APLUS, A, AMINUS, BPLUS, B, BMINUS, CPLUS, C, CMINUS, DPLUS, D, DMINUS, F, W, OTHER) VALUES ($semester, $course, $section, $professor, $students, $AP, $A, $AM, $BP, $B, $BM, $CP, $C, $CM, $DP, $D, $DM, $F, $W, $OTHER)',
        vars={
            "semester": grade["semester"],
            "course": grade["course_id"],
            "section": grade["section"],
            "professor": grade["professor_id"],
            "students": grade["num_students"],
            "AP": grade["APLUS"],
            "A": grade["A"],
            "AM": grade["AMINUS"],
            "BP": grade["BPLUS"],
            "B": grade["B"],
            "BM": grade["BMINUS"],
            "CP": grade["CPLUS"],
            "C": grade["C"],
            "CM": grade["CMINUS"],
            "DP": grade["DPLUS"],
            "D": grade["D"],
            "DM": grade["DMINUS"],
            "F": grade["F"],
            "W": grade["W"],
            "OTHER": grade["OTHER"]
        }
    )
