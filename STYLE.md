## Django

### Model Queries

When constructing model queries, if you can fit it on one line without going over python's character limit (80 characters), then do so:

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
