from __future__ import annotations

import smtplib
from email.message import EmailMessage


class EmailDeliveryError(RuntimeError):
    """Raised when SMTP delivery fails."""


def send_email(
    subject: str,
    body: str,
    from_email: str,
    to_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str = "",
    smtp_password: str = "",
    use_tls: bool = True,
) -> None:
    if not from_email or not to_email:
        raise ValueError("from_email and to_email are required to send mail")
    if not smtp_host:
        raise ValueError("smtp_host is required to send mail")

    recipients = [address.strip() for address in to_email.split(",") if address.strip()]
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as client:
        try:
            if use_tls:
                client.starttls()
            if smtp_user:
                client.login(smtp_user, smtp_password)
            client.send_message(message)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError(f"SMTP delivery failed: {exc}") from exc
        except OSError as exc:
            raise EmailDeliveryError(f"Network error while sending e-mail: {exc}") from exc
