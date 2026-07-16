from email.message import EmailMessage
import smtplib
import ssl


def _smtp_config():
    try:
        import streamlit as st
        if "smtp" in st.secrets:
            return dict(st.secrets["smtp"])
    except Exception:
        pass
    return {}


def send_booking_email(to_email, subject, body):
    config = _smtp_config()
    required = {"host", "port", "username", "password", "from_email"}
    if not required.issubset(config.keys()):
        return False, "SMTP secrets not configured"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"]
    message["To"] = to_email
    message.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            config["host"], int(config["port"]), context=context
        ) as server:
            server.login(config["username"], config["password"])
            server.send_message(message)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)
