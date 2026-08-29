import os
import smtplib
import ssl
from email.message import EmailMessage

from database import (
    create_database,
    create_missing_photo_reminders,
    get_due_email_reminders,
    mark_email_reminder_failed,
    mark_email_reminder_sent,
)


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)
APP_URL = os.getenv("APP_URL", "http://localhost:8501")


def validate_email_configuration():
    """Stop early when email credentials are missing."""
    missing_values = []

    if not SMTP_HOST:
        missing_values.append("SMTP_HOST")
    if not SMTP_USERNAME:
        missing_values.append("SMTP_USERNAME")
    if not SMTP_PASSWORD:
        missing_values.append("SMTP_PASSWORD")
    if not EMAIL_FROM:
        missing_values.append("EMAIL_FROM")

    if missing_values:
        raise RuntimeError(
            "Missing email configuration: "
            + ", ".join(missing_values)
        )


def build_photo_reminder_message(
    recipient_email,
    patient_name,
    family_member_name,
):
    """Create a plain-text photo-refresh reminder email."""
    message = EmailMessage()
    message["Subject"] = (
        f"Photo refresh reminder for {patient_name}"
    )
    message["From"] = EMAIL_FROM
    message["To"] = recipient_email

    message.set_content(
        f"""Hello {family_member_name or 'Family Member'},

The family photo connected to {patient_name}'s cognitive-training profile is now at least 30 days old.

Please open the Family Setup section and upload a recent photo or confirm the current photo is still suitable.

Application: {APP_URL}

This is an automatic reminder from the dementia cognitive-training prototype.
"""
    )

    return message


def send_message(message):
    """Send one email through an SSL-protected SMTP connection."""
    ssl_context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        SMTP_HOST,
        SMTP_PORT,
        context=ssl_context,
        timeout=30,
    ) as smtp:
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def process_due_photo_reminders():
    """Create missing reminder rows and send all reminders due now."""
    create_database()
    created_count = create_missing_photo_reminders()
    due_reminders = get_due_email_reminders()

    sent_count = 0
    failed_count = 0

    print(
        f"Created {created_count} missing reminder record(s)."
    )
    print(
        f"Found {len(due_reminders)} due reminder(s)."
    )

    if not due_reminders:
        return {
            "created": created_count,
            "due": 0,
            "sent": 0,
            "failed": 0,
        }

    validate_email_configuration()

    for reminder in due_reminders:
        (
            reminder_id,
            recipient_email,
            reminder_type,
            due_at,
            patient_name,
            family_member_name,
        ) = reminder

        if reminder_type != "photo_refresh":
            continue

        try:
            message = build_photo_reminder_message(
                recipient_email=recipient_email,
                patient_name=patient_name,
                family_member_name=family_member_name,
            )

            send_message(message)
            mark_email_reminder_sent(reminder_id)
            sent_count += 1

            print(
                f"Sent reminder {reminder_id} to "
                f"{recipient_email}. Due date: {due_at}"
            )

        except Exception as error:
            mark_email_reminder_failed(
                reminder_id,
                str(error),
            )
            failed_count += 1

            print(
                f"Reminder {reminder_id} failed for "
                f"{recipient_email}: {error}"
            )

    return {
        "created": created_count,
        "due": len(due_reminders),
        "sent": sent_count,
        "failed": failed_count,
    }


if __name__ == "__main__":
    summary = process_due_photo_reminders()
    print(f"Reminder run completed: {summary}")