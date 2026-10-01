"""Owner settings and bounded recovery; callers never receive saved SMTP secrets."""
from __future__ import annotations

import logging
import re
import time
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field

from security.mail import email_address, mail_settings, send_code
from security.store import AccessError
from security.connections import capabilities as describe_capabilities, principal_info

log = logging.getLogger("bifrost.security")


class MailConfig(BaseModel):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    mode: Literal["starttls", "ssl"]
    username: str = Field(min_length=1, max_length=254)
    sender: str = Field(min_length=1, max_length=254)
    password: str = Field(default="", max_length=1024)


class EmailInput(BaseModel):
    email: str = Field(max_length=254)


class CodeInput(BaseModel):
    code: str = Field(min_length=20, max_length=256)


class KeyInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[Literal["read", "ingest"]] = ["read"]
    days: int = Field(default=30, ge=1, le=365)
    rpm: int | None = Field(default=None, ge=1)
    writes: int | None = Field(default=None, ge=1)
    documents: int | None = Field(default=None, ge=1)
    bytes: int | None = Field(default=None, ge=1)


def deliver(store, address, purpose):
    code = store.challenge(purpose, {"email": address})
    try:
        send_code(store, address, code, purpose)
    except Exception as exc:
        store.cancel_challenge(code)
        log.warning("Recovery mail delivery failed kind=%s smtp_status=%s (credentials and code omitted)",
                    type(exc).__name__, getattr(exc, "smtp_code", None))
        raise AccessError("Mail delivery failed; current access and recovery email remain valid", 503) from None


def read_routes(get_store, require_token, safely):
    api = APIRouter()

    @api.get("/api/auth/me")
    @safely("auth_me")
    def me(request: Request, _=Depends(require_token)):
        return principal_info(request.state.principal)

    @api.get("/api/capabilities")
    @safely("capabilities")
    def capabilities(request: Request, _=Depends(require_token)):
        return describe_capabilities(get_store(), request)

    @api.get("/api/admin/settings")
    @safely("security_settings")
    def settings(_=Depends(require_token)):
        store = get_store()
        mail = mail_settings(store)
        return {"email": store.setting("email", ""), "verified": store.setting("email_verified", False),
                "mail": {k: v for k, v in mail.items() if k != "password"},
                "mail_configured": bool(mail.get("password")), "limits": store.limits}

    return api


def email_routes(get_store, require_token, safely):
    api = APIRouter()

    @api.post("/api/admin/mail")
    @safely("mail_settings")
    def configure_mail(body: MailConfig, _=Depends(require_token)):
        if not re.fullmatch(r"[A-Za-z0-9.-]+", body.host) or any(c in body.username for c in "\r\n"):
            raise AccessError("Invalid SMTP host or username", 400)
        store, cfg = get_store(), body.model_dump()
        cfg["sender"] = email_address(cfg["sender"])
        old = mail_settings(store)
        unchanged = all(cfg[field] == old.get(field) for field in ("host", "port", "mode", "username"))
        cfg["password"] = body.password or (old.get("password", "") if unchanged else "")
        if cfg["host"].casefold() == "smtp.gmail.com":
            cfg["password"] = cfg["password"].replace(" ", "")
        store.set_setting("mail", cfg)
        return {"ok": True, "configured": bool(cfg["password"])}

    @api.post("/api/admin/email/request")
    @safely("email_request")
    def email_request(body: EmailInput, _=Depends(require_token)):
        store, address = get_store(), email_address(body.email)
        store.spend("owner-email", str(int(time.time() // 3600)) + ":email", store.limits["challenge_requests_per_hour"])
        deliver(store, address, "email")
        return {"ok": True, "message": "Verification code sent; confirm before the address becomes active"}

    @api.post("/api/admin/email/confirm")
    @safely("email_confirm")
    def email_confirm(body: CodeInput, _=Depends(require_token)):
        return get_store().confirm(body.code, "email")

    return api


def recovery_routes(get_store, require_token, safely):
    api = APIRouter()

    @api.post("/api/auth/recovery/request", status_code=202)
    @safely("recovery_request")
    def recovery_request(body: EmailInput, background: BackgroundTasks):
        store = get_store()
        store.spend("recovery-mail", str(int(time.time() // 3600)) + ":recovery", store.limits["challenge_requests_per_hour"])
        if store.setting("email_verified", False) and body.email.casefold() == store.setting("email", "").casefold():
            def send():
                try:
                    deliver(store, store.setting("email"), "recovery")
                except AccessError:
                    pass  # generic response avoids disclosing mailbox registration
            background.add_task(send)
        return {"message": "If this is the verified recovery email and mail is configured, a single-use code will arrive"}

    @api.post("/api/auth/recovery/confirm")
    @safely("recovery_confirm")
    def recovery_confirm(body: CodeInput):
        return get_store().confirm(body.code, "recovery")

    return api


def key_routes(get_store, require_token, safely):
    api = APIRouter()

    @api.get("/api/admin/keys")
    @safely("keys_list")
    def list_keys(_=Depends(require_token)):
        return get_store().list_keys()

    @api.post("/api/admin/keys")
    @safely("key_create")
    def create_key(body: KeyInput, _=Depends(require_token)):
        return get_store().create_key(**body.model_dump(exclude_none=True))

    @api.post("/api/admin/keys/{id}/revoke")
    @safely("key_revoke")
    def revoke(id: str, _=Depends(require_token)):
        get_store().revoke(id)
        return {"ok": True}

    return api


def router(get_store, require_token, safely):
    api = APIRouter()
    for factory in [read_routes, email_routes, recovery_routes, key_routes]:
        api.include_router(factory(get_store, require_token, safely))
    return api
