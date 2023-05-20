import sys
import requests
from requests import adapters
from datetime import datetime
from time import sleep
import threading
import concurrent.futures
from urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError
from requests.exceptions import SSLError

from django.core.management import BaseCommand
from argparse import RawTextHelpFormatter

from home.models import Course, Gened
from home.utils import Semester

class Command(BaseCommand):
    help = '''Updates the database with new courses and professors during the provided semester.
    The semester argument must be in the numerical form YEAR+SEASON (see ** for exception).
    The season codes are as follows:
        Spring -> 01
        Summer -> 05
         Fall  -> 08
        Winter -> 12
    EXAMPLE: Spring 2023 = 202301

    ** NOTE: Starting from Winter 2021, the values for winter semesters are off by one year. Winter 2021 is actually 202012, not 202112
   '''

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.num_geneds_updated = 0
        self.num_courses_processed = 0
        self._lock = threading.Lock()

    def create_parser(self, *args, **kwargs):
        # to format the help text that gets displayed with the -h option
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        start = datetime.now()
        # I don't know which approach will actually be used so for now
        # they live in separate functions and one will move here once we decide
        #self.comparator_approach()
        self.threaded_approach()


        runtime = datetime.now() - start
        print(f"number of geneds updated: {self.num_geneds_updated}")
        print(f"total runtime: {round(runtime.seconds / 60, 2)} minutes")

    def comparator_approach(self):
        # TODO: I want to use the comparators for the semester field (e.g. |leq) so that we can
        # query all courses less than or equal to the current semester. Unfortunetely,
        # the comparators for the semester field is broken so this will need to be revisited
        # when that is fixed.
        kwargs = {"semester": f"{Semester.current()}|leq", "per_page": 100, "page": 1}
        umdio_courses  = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()
        pt_courses = Course.recent.all()

        while umdio_courses:
            for umdio_course in umdio_courses:
                # if umdio does not have this course continue to the next course
                if isinstance(umdio_course, dict) and 'error_code' in umdio_course.keys():
                    continue

                umdio_course_id = umdio_course["course_id"].strip("\n\t\r ")
                print(umdio_course_id)
                pt_course = pt_courses.filter(name=umdio_course_id)
                self.update_course_table(pt_course, umdio_course)
                self.update_geneds_table(pt_course, umdio_course)

            kwargs["page"] += 1
            umdio_courses  = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

    def threaded_approach(self):
        failed_courses = []
        pt_courses = Course.recent.all().order_by('name')
        num_total_courses = pt_courses.count()

        # necessary to overcome errors related to exceeding maximum retires for a url
        retry = Retry(total=1)
        adapter = adapters.HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)

        # Each thread will be reponsible for querying umdio for a particular course.
        # If something happens and the course cannot be retrieved, return None
        def thread_task(pt_course):
            # query umdio for this course.
            res = session.get(f"https://api.umd.io/v1/courses/{pt_course.name}")

            # TODO: figure out why some courses cause a code 500 error
            # In the mean time, return None
            if res.status_code == 500:
                failed_courses.append(pt_course.name)
                return None

            umdio_course = res.json()

            # if umdio does not have this course, return None
            if isinstance(umdio_course, dict) and 'error_code' in umdio_course.keys():
                return None

            with self._lock:
                self.num_courses_processed += 1
                sys.stdout.write("\r" + f"Collecting courses from umdio ({self.num_courses_processed}/{num_total_courses})")

            # otherwise, this thread completed its job, so return the result
            return (pt_course, umdio_course[0])

        print("Setting up thread pool...")

        # The expensive part of this script is querying umdio for each of our courses so we create
        # a thread pool that will break the task up into min(32, os.cpu_count() + 4) threads.
        # Wait for all the courses to be collected before moving on to updating the database.
        # We use submit() instead of map() because wait() expects a list of futures.
        # This part takes a long while (make sure your computer's auto-sleep feature is disabled).
        with concurrent.futures.ThreadPoolExecutor() as executor_:
            futures = [executor_.submit(thread_task, course) for course in pt_courses]
            concurrent.futures.wait(futures, return_when="ALL_COMPLETED")

        print("Updating planetterp courses...")

        # go through the courses collected by the thread pool and update our database
        for future in futures:
            res = future.result()

            if not res:
                continue

            pt_course, umdio_course = res

            print(pt_course.name)
            self.update_course_table(pt_course, umdio_course)
            self.update_geneds_table(pt_course, umdio_course)

        # sort the list of courses that caused an error, if there are any, by
        # their planetterp name so that the courses print in alphabetical order (A->Z)
        def keyfn(e):
            return e[0]

        failed_courses.sort(key=keyfn)

        if len(failed_courses):
            print(f"{len(failed_courses)}/{Course.recent.count()} courses failed to retrieve from umdio")
            print(failed_courses)


    # Go through all of umdio's courses by delegating smaller chunks of our
    # courses to threads that will each search umdio and combine their results
    # into a single list for us to process later.
    def get_umdio_courses(self):
        # list of (pt_course, umdio_course) tuples that threads will add to
        courses = []

        def thread_task(pt_courses):
            thread_courses = []

            # for each pt_course in the given chunk of pt_courses...
            for pt_course in pt_courses:
                # query umdio for this course.
                req = requests.get(f"https://api.umd.io/v1/courses/{pt_course.name}")

                # TODO: figure out why some courses cause a code 500 error
                if req.status_code == 500:
                    print(f"code 500 for {pt_course.name}")
                    continue

                umdio_course = req.json()

                # if umdio does not have this course continue to the next course
                if isinstance(umdio_course, dict) and 'error_code' in umdio_course.keys():
                    continue

                # otherwise, add the tuple to this thread's personal list of courses
                thread_courses.append((pt_course, umdio_course[0]))
                sleep(1)

            # once this thread has finished its task, add its personal list to
            # the main list in a thread-safe manner
            self._lock.acquire()
            courses += thread_courses
            self._lock.release()

        # chunk_size is an arbitrary number with almost no significance.
        # It's a minimal effort guess at trying to find a balance between
        # #threads and runtime.
        # Python does technically have a maximum allowed thread count,
        # but its somewhere in the 18,000s which currently isn't a problem with a chunk_size >= 100.
        # The only factor that will affect this concern is the number of courses we have.
        chunk_size = 200
        imin = 0
        imax = chunk_size
        threads = []
        pt_courses = Course.recent.all().order_by('name')
        num_pt_courses = pt_courses.count()

        # while the upper bound of a chunk is still a valid index...
        while imax < num_pt_courses:
            # create and start threads
            t = threading.Thread(target=thread_task, args=(pt_courses[imin:imax],), name=len(threads))
            threads.append(t)
            t.start()
            imax += chunk_size
            imin += chunk_size
            sleep(0.5)

        # if the last chunk range exceeded the valid range but there are courses left,
        # create one more thread to handle the remaining courses.
        if imin < num_pt_courses:
            t = threading.Thread(target=thread_task, args=(pt_courses[imin:],))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
            print(f"thread {t.name()} is done")

        return courses

    def update_course_table(self, pt_course, umdio_course):
        # umdio uses an empty list if a course has no geneds but
        # we want to use null because that's what our schema is expecting.
        if not umdio_course['gen_ed']:
            pt_course.geneds = None
        else:
            pt_course.geneds = umdio_course['gen_ed']

        pt_course.save()

    def update_geneds_table(self, pt_course, umdio_course):
        # create a list of all the umdio geneds for this course.
        # This list is considered the "correct" geneds for this course.
        umdio_geneds = []
        for gened_lst in umdio_course['gen_ed']:
            for gened in gened_lst:
                # To account for cases that have a pipe |, split the gened
                # on the pipe and take the first part. If there is no
                # pipe, the gened will be unmodified.
                gened_name= gened.split("|")[0]
                umdio_geneds.append(gened_name)

        # if we have a gened linked to a course but umdio doesn't agree,
        # assume our records are outdated and delete this link.
        for gened in pt_course.gened_set.all():
            if gened.name not in umdio_geneds:
                self.num_geneds_updated += 1
                gened.delete()

        # if we don't have a gened for this course that umdio does have,
        # add it to our records.
        for gened in umdio_geneds:
            if not pt_course.gened_set.filter(name=gened).exists():
                self.num_geneds_updated += 1
                Gened(name=gened, course=pt_course).save()
