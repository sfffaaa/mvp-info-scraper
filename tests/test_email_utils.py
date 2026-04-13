from unittest.mock import MagicMock, patch
from email_utils import build_message, send_email, send_failure_email


def test_build_message_sets_headers():
    msg = build_message(
        subject="Test Subject",
        html_body="<p>Hello</p>",
        from_addr="tool@gmail.com",
        to_addr="user@gmail.com",
    )
    assert msg["Subject"] == "Test Subject"
    assert msg["From"] == "tool@gmail.com"
    assert msg["To"] == "user@gmail.com"


def test_send_email_uses_smtp(monkeypatch):
    mock_server = MagicMock()
    mock_smtp_cls = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr("email_utils.smtplib.SMTP", mock_smtp_cls)

    settings_mock = MagicMock()
    settings_mock.gmail_address = "tool@gmail.com"
    settings_mock.gmail_app_password = "apppass"
    settings_mock.config = {
        "email": {
            "to": "user@gmail.com",
            "from": "tool@gmail.com",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
        }
    }

    send_email("Subject", "<p>Body</p>", settings_mock)
    mock_server.send_message.assert_called_once()


def test_send_failure_email_subject_contains_source(monkeypatch):
    sent_subjects = []

    def fake_send(subject, html_body, settings):
        sent_subjects.append(subject)

    monkeypatch.setattr("email_utils.send_email", fake_send)

    settings_mock = MagicMock()
    send_failure_email("scraper", "Connection refused", settings_mock)
    assert "scraper" in sent_subjects[0]
    assert "FAILURE" in sent_subjects[0]
