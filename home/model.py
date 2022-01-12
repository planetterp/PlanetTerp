import os
import web

from planetterp.config import USER, PASSWORD

db_name = os.environ.get("PLANETTERP_MYSQL_DB_NAME", "planetterp")
db = web.database(dbn='mysql', db=db_name, user=USER, pw=PASSWORD, charset='utf8mb4')


def get_distribution(search):
    if search == "":
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id GROUP BY semester', vars={'search': search})

    if len(search) == 4:
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id WHERE department = $search GROUP BY semester', vars={'search': search})

    if len(search) in [7, 8]:
        return db.query('SELECT semester, (SUM(APLUS)*4.0 + SUM(A)*4.0 + SUM(AMINUS)*3.7 + SUM(BPLUS)*3.3 + SUM(B)*3.0 + SUM(BMINUS)*2.7 + SUM(CPLUS) * 2.3 + SUM(C)*2.0 + SUM(CMINUS)*1.7 + SUM(DPLUS)*1.3 + SUM(D)*1.0 + SUM(DMINUS)*0.7 + SUM(F)*0.0 + SUM(W)*0.0)/(SUM(APLUS) + SUM(A) + SUM(AMINUS) + SUM(BPLUS) + SUM(B) + SUM(BMINUS) + SUM(CPLUS) + SUM(C) + SUM(CMINUS) + SUM(DPLUS) + SUM(D) + SUM(DMINUS) + SUM(F) + SUM(W)) AS avg_gpa FROM grades_historical INNER JOIN courses_historical ON courses_historical.id = grades_historical.course_id WHERE CONCAT (department, course_number) = $search GROUP BY semester', vars={'search': search})
