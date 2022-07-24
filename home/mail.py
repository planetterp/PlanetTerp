# this file is named `mail` instead of `email` to avoid name clashes with the
# builtin `email` library.
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from planetterp import config
from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

service = None
if config.email_config:
    credentials = service_account.Credentials.from_service_account_info(
        config.email_config, scopes=SCOPES, subject=config.email)

    service = build("gmail", "v1", credentials=credentials)



def send_email(to, subject, message_text):
    # alternative means we're sending both html and plaintext
    # https://stackoverflow.com/q/3902455
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["from"] = "admin@planetterp.com"
    message["subject"] = subject

    # plaintext is provided as a fallback if the client doesn't support html.
    # important: we have to add the html part last so it is the first one the
    # client attempts to display.
    # # https://realpython.com/python-send-email/#including-html-content
    text_part = MIMEText(message_text, "plain")
    html_part = MIMEText(message_text, "html")
    message.attach(text_part)
    message.attach(html_part)

    # https://stackoverflow.com/a/46668827
    message_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message = {'raw': message_b64}


    # dev environments may not have email auth set up. In this case, just don't
    # send the email.
    if service:
        # google is doing some hacky setattr stuff that pylint can't detect
        # pylint: disable=no-member
        service.users().messages().send(userId="me", body=message).execute()
