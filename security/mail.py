"""TLS-only mail delivery; SMTP secrets stay in the private security store."""
from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage

from security.store import AccessError


def email_address(value: str) -> str:
    if len(value) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise AccessError("Enter a valid email address", 400)
    return value


def mail_settings(store) -> dict:
    return store.setting("mail", {})


def send_code(store, address: str, code: str, purpose: str) -> None:
    cfg = mail_settings(store)
    if not cfg.get("host") or not cfg.get("password"):
        raise AccessError("Configure a TLS SMTP account in Security settings first", 503)
    message = EmailMessage()
    message["From"], message["To"] = email_address(cfg["sender"]), email_address(address)
    message["Subject"] = "Bifröst: verify your recovery email" if purpose == "email" else "Bifröst: owner access recovery"
    message.set_content(
        f"Your single-use Bifröst {purpose} code is:\n\n{code}\n\n"
        f"It expires after {store.limits['recovery_seconds'] // 60} minutes. "
        "Enter it in the Security page. Your current owner token remains valid until recovery is confirmed.\n"
        "If you did not request this, ignore this email.\n"
    )
    context = ssl.create_default_context()
    if cfg["mode"] == "ssl":
        client = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10, context=context)
    else:
        client = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
    with client:
        if cfg["mode"] == "starttls":
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
        client.login(cfg["username"], cfg["password"])
        client.send_message(message)
