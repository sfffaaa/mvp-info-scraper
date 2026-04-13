import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings


def build_message(subject: str, html_body: str, from_addr: str, to_addr: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_email(subject: str, html_body: str, settings: "Settings") -> None:
    cfg = settings.config["email"]
    msg = build_message(subject, html_body, cfg["from"], cfg["to"])
    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls()
        server.login(settings.gmail_address, settings.gmail_app_password)
        server.send_message(msg)


def send_failure_email(source: str, error: str, settings: "Settings") -> None:
    subject = f"[info-scraper] FAILURE: {source}"
    html_body = f"<h2>Failure in {source}</h2><pre>{error}</pre>"
    try:
        send_email(subject, html_body, settings)
    except Exception as e:
        print(f"[email_utils] Could not send failure email: {e}")
