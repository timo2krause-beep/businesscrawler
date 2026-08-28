"""Einfacher E-Mail-Versand via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import settings

log = logging.getLogger(__name__)


def send_report_email(to: str, subject: str, html_body: str) -> bool:
    """Sendet einen HTML-Report per E-Mail. Gibt True bei Erfolg zurück."""
    if not settings.smtp_host:
        log.warning("SMTP nicht konfiguriert – E-Mail wird übersprungen.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, [to], msg.as_string())
        log.info("E-Mail gesendet an %s", to)
        return True
    except Exception:
        log.exception("Fehler beim E-Mail-Versand an %s", to)
        return False
