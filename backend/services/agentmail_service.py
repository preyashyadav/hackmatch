import logging
import re
import secrets
import time
from typing import Optional

from agentmail import AgentMail
from agentmail.core.api_error import ApiError
from agentmail.inboxes.types import CreateInboxRequest
import httpx

import config


logger = logging.getLogger(__name__)


def _get_client() -> AgentMail:
    if not config.AGENTMAIL_API_KEY:
        raise RuntimeError("AGENTMAIL_API_KEY is not configured.")
    return AgentMail(api_key=config.AGENTMAIL_API_KEY)


def _sanitize_username_hint(username_hint: str) -> str:
    username = re.sub(r"[^a-z0-9]", "", username_hint.lower())[:12]
    return username or "agent"


def _run_with_retry(operation_name: str, func):
    last_error = None
    for attempt in range(1, 4):
        try:
            return func()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            logger.warning(
                "AgentMail %s failed on attempt %s/3: %s",
                operation_name,
                attempt,
                exc,
            )
            if attempt < 3:
                time.sleep(0.5 * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"AgentMail {operation_name} failed unexpectedly.")


def create_inbox(username_hint: str) -> dict[str, str]:
    client = _get_client()
    username = f"{_sanitize_username_hint(username_hint)}{secrets.token_hex(2)}"
    configured_domain = config.AGENT_DOMAIN.strip()
    request_kwargs = {"username": username}
    if configured_domain and configured_domain != "agentmail.to":
        request_kwargs["domain"] = configured_domain

    try:
        inbox = _run_with_retry(
            "create inbox",
            lambda: client.inboxes.create(request=CreateInboxRequest(**request_kwargs)),
        )
    except ApiError as exc:
        error_message = str(getattr(exc, "body", {}).get("message", "")).strip().lower()
        if request_kwargs.get("domain") and error_message == "domain not found":
            inbox = _run_with_retry(
                "create inbox with default domain",
                lambda: client.inboxes.create(request=CreateInboxRequest(username=username)),
            )
        else:
            raise

    return {
        "agent_email": getattr(inbox, "email", None) or f"{username}@{configured_domain or 'agentmail.to'}",
        "inbox_id": inbox.inbox_id,
    }


def send_email(
    from_inbox_id: str,
    to_email: str | list[str],
    subject: str,
    body: str,
    in_reply_to: Optional[str] = None,
) -> str:
    client = _get_client()
    headers = None
    if in_reply_to:
        headers = {
            "In-Reply-To": in_reply_to,
            "References": in_reply_to,
        }

    send_kwargs = {
        "inbox_id": from_inbox_id,
        "to": to_email,
        "subject": subject,
        "text": body,
    }
    if headers:
        send_kwargs["headers"] = headers

    sent_message = _run_with_retry(
        "send email",
        lambda: client.inboxes.messages.send(**send_kwargs),
    )
    return sent_message.message_id


def get_message(inbox_id: str, message_id: str):
    client = _get_client()
    return _run_with_retry(
        "get message",
        lambda: client.inboxes.messages.get(inbox_id=inbox_id, message_id=message_id),
    )


def list_webhooks():
    client = _get_client()
    response = _run_with_retry("list webhooks", lambda: client.webhooks.list())
    return getattr(response, "webhooks", [])


def register_webhook(inbox_id: str, webhook_url: str) -> str:
    client = _get_client()
    webhook = _run_with_retry(
        "register webhook",
        lambda: client.webhooks.create(
            url=webhook_url,
            event_types=["message.received"],
            inbox_ids=[inbox_id],
        ),
    )
    return webhook.webhook_id


def ensure_webhook_registration(inbox_id: str, webhook_url: str) -> str:
    for webhook in list_webhooks():
        webhook_url_value = getattr(webhook, "url", "")
        inbox_ids = list(getattr(webhook, "inbox_ids", []) or [])
        event_types = list(getattr(webhook, "event_types", []) or [])
        if webhook_url_value == webhook_url and inbox_id in inbox_ids and "message.received" in event_types:
            return getattr(webhook, "webhook_id")

    return register_webhook(inbox_id=inbox_id, webhook_url=webhook_url)
