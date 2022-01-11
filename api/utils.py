from rest_framework.exceptions import ValidationError as ValidationError_


class ValidationError(ValidationError_):
    def __init__(self, message, code=None):
        detail = {"error": message}
        super().__init__(detail, code)

# distinguish between `default=None`` and default not being passed
sentry = object()
def param(request, name, *, default=sentry, options=None):
    params = request.query_params

    if name not in params:
        if default is sentry:
            raise ValidationError(f"{name} parameter is required")
        return default

    val = params[name]

    if options and val not in options:
        raise ValidationError(f"{name} parameter must be one of {options}")

    return val

def param_int(request, name, *, default=sentry, min_=None, max_=None):
    val = param(request, name, default=default)
    if val == default:
        return val
    try:
        val = int(val)
    except:
        raise ValidationError(f"{name} parameter must be a valid integer")

    if min_ is not None and val < min_:
        raise ValidationError(f"{name} parameter must be at least {min_}")

    if max_ is not None and val > max_:
        raise ValidationError(f"{name} parameter must be no more than {max_}")

    return val

def param_bool(request, name, *, default=sentry):
    val = param(request, name, default=default, options=["true", "false"])

    if val == default:
        return val

    return val == "true"
