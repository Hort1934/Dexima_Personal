from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from dotenv import load_dotenv

from main_service.tasks import send_html_email

BASE_URL = "http://195.201.70.92"
# BASE_URL = " http://127.0.0.1"


def forgot_password_sender(email):
    print("forgot_password_sender")
    load_dotenv()
    user = get_user_model().objects.get(email=email)
    django_endpoint = BASE_URL + ":80"
    import base64
    # Assuming user_id is the user's ID
    uidb64 = base64.urlsafe_b64encode(str(user.id).encode()).decode()
    token = default_token_generator.make_token(user)
    subject = "ats.trading Password Reset Request"
    message = f"""
    <html>
    <body>
        <p>Dear User,</p>
        <p>You recently requested a password reset for your account. To reset your password, please click on the following link:</p>
        <p><a href='{django_endpoint}/password-reset/confirm/{uidb64}/{token}/'>link</a></p>
        <p>If you did not request this password reset, you can safely ignore this email. Your password will not be changed until you confirm the reset.</p>
        <p>Thank you,<br>ats.trading Team</p>
    </body>
    </html>
    """

    try:
        send_html_email.delay(subject, message, email)
    except Exception:
        return 0
