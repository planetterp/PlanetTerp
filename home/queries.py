from itertools import chain, islice

from django.db.models import Q

from home.models import Professor, Course

def search(search, num_results, *, offset=0, professors=False, courses=False):
    # TODO: allow option to search all professors
    professors_q = (
        Professor.verified
        .filter(name__icontains=search)
        .order_by("name")
    )
    courses_q = (
        Course.objects
        .filter(Q(name__icontains=search) | Q(title__icontains=search))
        .order_by("name")
    )
    iterables = []
    # professors before courses if both are passed
    if professors:
        iterables.append(professors_q)
    if courses:
        iterables.append(courses_q)

    results = chain(*iterables)
    return list(islice(results, offset, num_results))
