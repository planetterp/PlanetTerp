import os
import web

from home.models import Professor
from home.models import Gened
from planetterp.config import USER, PASSWORD

db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')


# queries to be rewritten

def verify_professor(id_, verified_status: Professor.Status, slug):
    if verified_status is not Professor.Status.VERIFIED:
        db.update('reviews', where='professor_id=$id', verified=verified_status.value, vars={'id': id_})

    db.update('professors', where='id=$id', verified=verified_status.value, slug=slug, vars={'id': id_})

def merge_professors(subject_id, target_id):
    db.update("professor_courses", where="professor_id=$id", professor_id=target_id, vars={"id": subject_id})
    db.update("reviews", where="professor_id=$id", professor_id=target_id, vars={"id": subject_id})
    db.update("grades", where="professor_id=$id", professor_id=target_id, vars={"id": subject_id})
    db.query("DELETE FROM professors WHERE id=$id", vars={"id": subject_id})

def delete_professor(id_):
    db.query("DELETE FROM professor_courses WHERE professor_id=$id", vars={"id": id_})
    db.query("DELETE FROM reviews WHERE professor_id=$id", vars={"id": id_})
    db.query("DELETE FROM professors WHERE id=$id", vars={"id": id_})

def update_professor_name(professor_id, new_name):
    db.update("professors", where="id=$prof_id", name=new_name, vars={"prof_id": professor_id})

def update_professor_slug(professor_id, new_slug):
    db.update("professors", where="id=$prof_id", slug=new_slug, vars={"prof_id": professor_id})

def update_professor_type(professor_id, new_type):
    db.update("professors", where="id=$prof_id", type=new_type, vars={"prof_id": professor_id})

def count_professors_slugs(slug):
    return int(db.query('SELECT COUNT(name) FROM professors WHERE slug=$slug', vars={"slug": slug})[0]['COUNT(name)'])

def get_all_sections():
    return db.query('SELECT id FROM sections WHERE active=1;')

def get_sections(course_id, maxwaitlist):
    if maxwaitlist == -1:
        return db.query('SELECT * FROM sections WHERE course_id = $course_id AND active=1;', vars={'course_id': course_id})
    return db.query('SELECT * FROM sections WHERE course_id = $course_id AND active=1 AND (waitlist < $maxwaitlist OR available_seats > 0);', vars={'course_id': course_id, 'maxwaitlist': maxwaitlist})

def get_data_from_section(section_id):
    return db.query('SELECT CONCAT(department, course_number) AS course, title, section_number, GROUP_CONCAT(DISTINCT gened ORDER BY gened) AS geneds, credits, available_seats, seats, waitlist, name, slug, SUM(rating)/COUNT(rating) as average_rating, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS)*2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0 + SUM(OTHER)*0.0) / (SUM(num_students) - SUM(OTHER)) AS average_gpa FROM courses LEFT JOIN sections ON courses.id = sections.course_id LEFT JOIN professors ON FIND_IN_SET(professors.id, sections.professor_ids) LEFT JOIN reviews ON professors.id = Review.professor_id LEFT JOIN grades ON courses.id = grades.course_id AND professors.id = grades.professor_id LEFT JOIN geneds ON courses.id = geneds.course_id WHERE sections.id = $section_id GROUP BY professors.id;', vars={'section_id': section_id})

def get_meetings(section_id):
    return db.query('SELECT * FROM section_meetings WHERE section_id = $section_id;', vars={'section_id': section_id})

def get_all_meetings():
    return db.query('SELECT * FROM section_meetings;')

def insert_user_sections(user_id, sections, active, semester):
    db.query('UPDATE user_schedules SET active=false WHERE user_id = $user_id', vars={'user_id': user_id})

    for section_id in sections:
        db.insert('user_schedules', user_id=user_id, section_id=section_id, active=active, semester=semester)

def get_user_schedule(user_id):
    user_sections = db.query('SELECT section_id FROM user_schedules WHERE user_id=$user_id AND active=true AND semester=202101;', vars={'user_id': user_id})
    return user_sections if user_sections else None

def get_random_gened_course(gened):
    return db.query('SELECT course_id FROM geneds WHERE gened=$gened ORDER BY RAND() LIMIT 1;', vars={'gened': gened})[0]['course_id']

def insert_groupme_auth(user_id, groupme_username, access_token):
    return db.insert('groupme_auth', user_id=user_id, groupme_username=groupme_username, access_token=access_token)

def insert_groupme_group(group_id, group_name):
    return db.insert('groups', group_id=group_id, group_name=group_name)

def insert_groupme_user_group(user_id, group_id):
    return db.insert('groupme_user_groups', user_id=user_id, group_id=group_id)

def get_access_token(user_id):
    result = db.query('SELECT access_token FROM groupme_auth WHERE user_id = $user_id;', vars={'user_id': user_id})
    return result[0].access_token if result else False

def user_already_authenticated(user_id):
    result = db.query('SELECT * FROM groupme_auth WHERE user_id = $user_id;', vars={'user_id': user_id})
    return len(result) == 1

def access_token_exists(access_token, user_id):
    result = db.query('SELECT * FROM groupme_auth WHERE access_token = $access_token AND user_id != $user_id;', vars={'access_token': access_token, 'user_id': user_id})
    return len(result) == 1

def groupme_exists(group_id):
    result = db.query('SELECT id FROM groups WHERE group_id = $group_id;', vars={'group_id': group_id})
    return result[0].id if result else False

def user_is_in_group(user_id, group_id):
    result = db.query('SELECT id FROM groupme_user_groups WHERE user_id = $user_id AND group_id = $group_id;', vars={'user_id': user_id, 'group_id': group_id})

    return len(result) == 1

def get_user_groups(user_id):
    return db.query('SELECT * FROM groupme_user_groups INNER JOIN groups ON groupme_user_groups.group_id = groups.id WHERE user_id = $user_id', vars={'user_id': user_id})

def get_group_users(group_id, current_user_id):
    users = db.query('SELECT * FROM groupme_user_groups INNER JOIN groupme_auth ON groupme_user_groups.user_id = groupme_auth.user_id WHERE group_id = $group_id AND groupme_user_groups.user_id != $current_user_id;', vars={'group_id': group_id, 'current_user_id': current_user_id})

    user_data = []

    for user in users:
        course_data = db.query('SELECT GROUP_CONCAT(department, course_number, " (", section_number, ")" SEPARATOR ", ") AS courses, GROUP_CONCAT(sections.id) AS sections, SUM(credits) AS credits FROM user_schedules INNER JOIN sections ON user_schedules.section_id = sections.id INNER JOIN courses ON sections.course_id = courses.id WHERE user_id=$user_id AND user_schedules.active=true AND user_schedules.semester="202101";', vars={'user_id': user['user_id']})

        if not course_data:
            continue
        course_data = course_data[0]
        if not course_data.courses:
            continue
        user_data.append({'groupme_username': user['groupme_username'], 'courses': course_data['courses'], 'sections': course_data['sections'], 'credits': course_data['credits']})

    return user_data

def insert_created_schedule(loadtime, course_ids, status):
    schedule_id = db.insert('created_schedules', loadtime=loadtime, status=status)

    for course_id in course_ids:
        if course_id in Gened.GENEDS:
            db.insert('created_schedule_sections', created_schedule_id=schedule_id, gened=course_id)
        else:
            db.insert('created_schedule_sections', created_schedule_id=schedule_id, course_id=course_id)


def get_distribution(search):
    if search == "":
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id GROUP BY semester', vars={'search': search})

    if len(search) == 4:
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id WHERE department = $search GROUP BY semester', vars={'search': search})

    if len(search) in [7, 8]:
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id WHERE CONCAT (department, course_number) = $search GROUP BY semester', vars={'search': search})
