# You can exectue `db_setup.py full` to completely migrate your db to django

import os
import web
from planetterp.config import USER, PASSWORD

db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')

db.query("DROP TABLE `planetterp`.`auth_group`, `planetterp`.`auth_group_permissions`, `planetterp`.`auth_permission`, `planetterp`.`django_admin_log`, `planetterp`.`django_content_type`, `planetterp`.`django_migrations`, `planetterp`.`django_session`, `planetterp`.`home_auditlog`, `planetterp`.`home_course`, `planetterp`.`home_discussion`, `planetterp`.`home_discussionreply`, `planetterp`.`home_fall2020search`, `planetterp`.`home_gened`, `planetterp`.`home_grade`, `planetterp`.`home_groupmegroup`, `planetterp`.`home_groupmeuser`, `planetterp`.`home_groupmeuser_groups`, `planetterp`.`home_organization`, `planetterp`.`home_professor`, `planetterp`.`home_professorcourse`, `planetterp`.`home_resetcode`, `planetterp`.`home_review`, `planetterp`.`home_section`, `planetterp`.`home_sectionmeeting`, `planetterp`.`home_section_professors`, `planetterp`.`home_user`, `planetterp`.`home_user_groups`, `planetterp`.`home_userschedule`, `planetterp`.`home_user_user_permissions`, `planetterp`.`home_view`;")
os.system("python3 manage.py makemigrations")
os.system("python3 manage.py migrate home zero --fake")
os.system("python3 manage.py migrate")
