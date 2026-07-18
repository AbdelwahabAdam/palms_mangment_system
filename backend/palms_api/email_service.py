"""Jinja2-backed email delivery with an injectable transport."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
import smtplib
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from palms_api.config import Settings
from palms_api.models import EmailLog


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SMTPTransport:
    """SMTP transport compatible with a local MailHog listener."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as client:
            if self.settings.smtp_use_tls:
                client.starttls()
            if self.settings.smtp_username:
                client.login(self.settings.smtp_username, self.settings.smtp_password or "")
            client.send_message(message)


@dataclass
class MemoryEmailTransport:
    """Injected test transport retaining complete MIME messages in memory."""

    messages: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class EmailService:
    """Render templates, deliver mail, and retain a non-secret delivery audit."""

    def __init__(self, settings: Settings, transport: EmailTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport or SMTPTransport(settings)
        self.templates = Environment(
            loader=FileSystemLoader(Path(__file__).with_name("templates") / "emails"),
            autoescape=select_autoescape(["html", "jinja2"]),
        )

    def send(
        self,
        db: Session,
        *,
        recipient: str,
        template_name: str,
        subject: str,
        context: dict[str, Any],
        attachment: tuple[str, bytes, str] | None = None,
    ) -> EmailLog:
        """Try delivery and persist sent/failed state without exposing template secrets."""
        log = EmailLog(
            recipient=recipient.lower(),
            template_name=template_name,
            subject=subject[:255],
            status="queued",
            metadata_json={"has_attachment": attachment is not None},
        )
        db.add(log)
        html = self.templates.get_template(f"{template_name}.html.jinja2").render(**context)
        message = EmailMessage()
        message["To"] = log.recipient
        message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
        message["Subject"] = log.subject
        message.set_content(_text_content(context))
        message.add_alternative(html, subtype="html")
        if attachment:
            filename, content, content_type = attachment
            maintype, _, subtype = content_type.partition("/")
            message.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)
        try:
            if self.settings.email_enabled:
                self.transport.send(message)
            log.status = "sent" if self.settings.email_enabled else "suppressed"
        except Exception as error:
            log.status = "failed"
            log.error_message = str(error)[:2_000]
        return log

    def send_password_reset(self, db: Session, *, email: str, full_name: str, token: str) -> EmailLog:
        reset_url = f"{self.settings.admin_app_url.rstrip('/')}/reset-password?token={token}"
        return self.send(
            db,
            recipient=email,
            template_name="password_reset",
            subject="Reset your password",
            context={"full_name": full_name, "reset_url": reset_url},
        )

    def send_invitation(
        self, db: Session, *, email: str, full_name: str, role_name: str, token: str
    ) -> EmailLog:
        invitation_url = f"{self.settings.admin_app_url.rstrip('/')}/accept-invitation?token={token}"
        return self.send(
            db,
            recipient=email,
            template_name="user_invitation",
            subject="You have been invited to Palms Management",
            context={"full_name": full_name, "role_name": role_name, "invitation_url": invitation_url},
        )

    def send_report_result(
        self,
        db: Session,
        *,
        recipient: str,
        subject: str,
        succeeded: bool,
        report_name: str,
        download_url: str | None = None,
        attachment: tuple[str, bytes, str] | None = None,
        error_message: str | None = None,
    ) -> EmailLog:
        return self.send(
            db,
            recipient=recipient,
            template_name="scheduled_report",
            subject=subject,
            context={
                "succeeded": succeeded,
                "report_name": report_name,
                "download_url": download_url,
                "error_message": error_message,
            },
            attachment=attachment if succeeded else None,
        )

    def send_notification(self, db: Session, *, recipient: str, subject: str, message: str) -> EmailLog:
        return self.send(
            db,
            recipient=recipient,
            template_name="notification",
            subject=subject,
            context={"message": message},
        )


def _text_content(context: dict[str, Any]) -> str:
    """Provide a safe plain-text alternative without serializing raw objects."""
    values = [str(value) for key, value in context.items() if key not in {"token"} and value]
    return "\n".join(values) or "Palms Management notification."
