import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

log = logging.getLogger("newsfold.email")


def configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.from_email)


def send_email(to: str, subject: str, html: str) -> bool:
    """Send one HTML email over SMTP+STARTTLS. Returns False (and logs) on any
    failure or when SMTP isn't configured — never raises into the caller."""
    if not configured():
        log.warning("SMTP not configured — skipping email to %s", to)
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.from_name} <{settings.from_email}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(settings.from_email, [to], msg.as_string())
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("email send to %s failed: %s", to, exc)
        return False
