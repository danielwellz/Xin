"""Automation action connectors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConnectorContext:
    tenant_id: UUID
    brand_id: UUID
    rule_id: UUID | None = None


class AutomationConnector:
    """Base connector."""

    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        raise NotImplementedError


class WebhookConnector(AutomationConnector):
    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        url = payload.get("url")
        method = payload.get("method", "POST").upper()
        headers = payload.get("headers") or {}
        body = payload.get("body") or {}
        if dry_run:
            logger.info(
                "automation.webhook.dry_run",
                extra={
                    "tenant_id": str(context.tenant_id),
                    "url": url,
                    "method": method,
                },
            )
            return {"status": "dry_run", "url": url, "method": method}

        if not url:
            raise ValueError("webhook url missing")
        with httpx.Client(timeout=payload.get("timeout", 10.0)) as client:
            response = client.request(method, url, headers=headers, json=body)
        logger.info(
            "automation.webhook.sent",
            extra={
                "tenant_id": str(context.tenant_id),
                "status_code": response.status_code,
            },
        )
        return {"status_code": response.status_code, "body": response.text}


class CRMConnector(AutomationConnector):
    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        endpoint = payload.get("endpoint")
        event = payload.get("event")
        if dry_run:
            logger.info(
                "automation.crm.dry_run",
                extra={
                    "tenant_id": str(context.tenant_id),
                    "endpoint": endpoint,
                    "event": event,
                },
            )
            return {"status": "dry_run"}
        logger.info(
            "automation.crm.sent",
            extra={
                "tenant_id": str(context.tenant_id),
                "endpoint": endpoint,
                "event": event,
            },
        )
        return {"status": "recorded"}


class EmailConnector(AutomationConnector):
    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        to_address = payload.get("to")
        subject = payload.get("subject", "Xin Automation")
        if dry_run:
            logger.info(
                "automation.email.dry_run",
                extra={"tenant_id": str(context.tenant_id), "to": to_address},
            )
            return {"status": "dry_run"}
        logger.info(
            "automation.email.sent",
            extra={
                "tenant_id": str(context.tenant_id),
                "to": to_address,
                "subject": subject,
            },
        )
        return {"status": "queued"}


class SMSConnector(AutomationConnector):
    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        phone = payload.get("phone")
        if dry_run:
            logger.info(
                "automation.sms.dry_run",
                extra={"tenant_id": str(context.tenant_id), "phone": phone},
            )
            return {"status": "dry_run"}
        logger.info(
            "automation.sms.sent",
            extra={"tenant_id": str(context.tenant_id), "phone": phone},
        )
        return {"status": "queued"}


class InternalNotificationConnector(AutomationConnector):
    def execute(
        self, payload: dict[str, Any], *, dry_run: bool, context: ConnectorContext
    ) -> dict[str, Any]:
        message = payload.get("message", "")
        channel = payload.get("channel", "ops")
        logger.info(
            "automation.internal.notification",
            extra={
                "tenant_id": str(context.tenant_id),
                "channel": channel,
                "dry_run": dry_run,
            },
        )
        return {"status": "dry_run" if dry_run else "notified"}


def build_connector(action_type: str) -> AutomationConnector:
    action_type = (action_type or "webhook").lower()
    if action_type == "webhook":
        return WebhookConnector()
    if action_type == "crm":
        return CRMConnector()
    if action_type == "email":
        return EmailConnector()
    if action_type == "sms":
        return SMSConnector()
    return InternalNotificationConnector()
