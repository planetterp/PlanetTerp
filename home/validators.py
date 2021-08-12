from django.core.exceptions import ValidationError
from home.models import User

def validate_unique_email(email):
    email = User.objects.filter(email=email).first()
    if email:
        raise ValidationError(
            "A user with that email already exists.",
            code="email_exists"
        )
