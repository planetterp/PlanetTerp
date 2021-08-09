from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import BasePasswordHasher
import bcrypt

from home.models import User

# TODO need to check for old 15 round salt passwords and convert to 13 round
# salts. Will probably need to make a new base bcrypt backend and then two
# backends which inherit and change the number of salt rounds, then let django
# handle the password upgrading for us automaticallys.

class BcryptBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        user = User.objects.filter(username=username).first()
        if not user:
            return None

        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            return None

        return user

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()
