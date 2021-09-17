## Python

### Package Imports

Imports should be organized in blocks, according to its type, with a space
separating each block. The order of blocks should be listed in the following order:
* Stanard Python Packages
* Standard Django Packages
* Crispy Forms
* Django Tables
* Discord
* Other Non-local imports
* Local imports

If an import line is longer than 80 characters, surround it with parenthesis and
break up the import across as many lines as neccessary to keep it under 80 characters:

```python
                                                                         # 80 chars
# BAD:                                                                         |
from home.forms.admin_forms import ReviewUnverifyForm, ReviewVerifyForm, ProfessorVerifyForm, ReviewRejectForm, ReviewHelpForm, ProfessorRejectForm, ProfessorDeleteForm

# GOOD:
from home.forms.admin_forms import (ReviewUnverifyForm, ReviewVerifyForm,
ProfessorVerifyForm, ReviewRejectForm, ReviewHelpForm, ProfessorRejectForm,
ProfessorDeleteForm)
```

## Django

### Model Queries

When constructing model queries, if you can fit it on one line without going
over python's character limit (80 characters), then do so:

```python
courses = Course.objects.filter(name__icontains=search)
```

However, if your query is longer than 80 characters, style it in the following way.

* wrap the entire expression in paranetheses
* put `<model>.objects` first, on its own line
* put any method call (`filter`, `exclude`, `annotate`, etc) on its own line

For example:

```python
average_gpa = (
    Grade.objects
    .filter(course__department=department_name)
    .average_gpa()
)
```

If any of the subexpressions get too long, the arguments should be put on their own line to save a few characters:

```python
# before
grades = (
    Grade.objects
    .annotate(course_name=Concat("course__department", "course__course_number"))
    .filter(course_name__icontains=query)
)

# after
grades = (
    Grade.objects
    .annotate(
        course_name=Concat("course__department", "course__course_number")
    )
    .filter(course_name__icontains=query)
)
```

## Crispy Forms

### Layout Objects

When instantiating layout objects, unless you are only passing a single parameter, always put each parameter on its own line:

```python
Field(
    "anonymous",
    id=f"id_anonymous_{self.form_type.value}"
)
```

## Django Tables

### Column HTML Attributes in Python
HTML attributes are defined via nested dictionaries in the column definition. No matter how many ```key, value``` pairs a dictionary has, always expand a nested dictionary onto it own line.

```python
# Bad
        attrs = {
            "th": {"class": "information"},
            "td": {
                "class": "information",
                "style": "white-space: nowrap; width: 11%;"
            }
        }


# Good
        attrs = {
            "th": {
                "class": "information"
            },
            "td": {
                "class": "information",
                "style": "white-space: nowrap; width: 11%;"
            }
        }
```
