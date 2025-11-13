"""Automation service tests."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from chatbot.admin import schemas
from chatbot.automation.service import AutomationService
from chatbot.core.db import models


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _seed_tenant(session: Session) -> tuple[models.Tenant, models.Brand]:
    tenant = models.Tenant(name="Acme", timezone="UTC")
    session.add(tenant)
    session.flush()
    brand = models.Brand(
        tenant_id=tenant.id,
        name="Acme Brand",
        slug="acme",
        language="en",
    )
    session.add(brand)
    session.commit()
    return tenant, brand


def test_create_and_pause_rule() -> None:
    session = _session()
    _, brand = _seed_tenant(session)
    service = AutomationService(session, redis_client=None)
    request = schemas.AutomationRuleCreateRequest(
        tenant_id=brand.tenant_id,
        brand_id=brand.id,
        name="Follow Up",
        trigger_type="schedule",
        trigger_event="cron",
        schedule_expression="*/5 * * * *",
        action_type="webhook",
        action_payload={"url": "https://example.com/webhook"},
        throttle_seconds=0,
        max_retries=2,
        is_active=True,
    )
    rule = service.create_rule(request, actor="tester")
    assert rule.is_active
    paused = service.set_rule_active(rule.id, active=False, actor="tester")
    assert paused.is_active is False


def test_test_rule_returns_dry_run() -> None:
    session = _session()
    tenant, brand = _seed_tenant(session)
    service = AutomationService(session, redis_client=None)
    payload = schemas.AutomationTestRequest(
        rule=schemas.AutomationRuleCreateRequest(
            tenant_id=tenant.id,
            brand_id=brand.id,
            name="Sim",
            trigger_type="event",
            trigger_event="lead_created",
            action_type="email",
            action_payload={"to": "ops@xin.com"},
            throttle_seconds=0,
            max_retries=1,
            is_active=True,
        )
    )
    result = service.test_rule(payload)
    assert result["status"] == "dry_run"
