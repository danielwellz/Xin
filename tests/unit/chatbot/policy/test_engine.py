"""Policy engine evaluation tests."""

from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from chatbot.core.db import models
from chatbot.policy.engine import PolicyEngine


def _setup_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_policy_engine_quiet_hours_denies() -> None:
    session = _setup_session()
    tenant_id = uuid4()
    config = models.RetrievalConfig(tenant_id=tenant_id)
    session.add(config)
    policy = models.PolicyVersion(
        tenant_id=tenant_id,
        version=1,
        status=models.PolicyStatus.PUBLISHED,
        created_by="tester",
        policy_json={
            "guardrails": {
                "quiet_hours": [
                    {"start": "00:00", "end": "23:59", "timezone": "UTC"},
                ]
            }
        },
    )
    session.add(policy)
    session.commit()

    engine_service = PolicyEngine(session)
    decision = engine_service.evaluate(
        tenant_id=tenant_id,
        brand_id=uuid4(),
        channel_id=uuid4(),
        message="hello",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    assert decision.allow_response is False
    assert decision.reason == "quiet_hours"


def test_policy_engine_allows_when_no_guardrail() -> None:
    session = _setup_session()
    tenant_id = uuid4()
    session.add(models.RetrievalConfig(tenant_id=tenant_id))
    policy = models.PolicyVersion(
        tenant_id=tenant_id,
        version=1,
        status=models.PolicyStatus.PUBLISHED,
        created_by="tester",
        policy_json={},
    )
    session.add(policy)
    session.commit()

    engine_service = PolicyEngine(session)
    decision = engine_service.evaluate(
        tenant_id=tenant_id,
        brand_id=uuid4(),
        channel_id=uuid4(),
        message="hello",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    assert decision.allow_response is True
    assert decision.top_k == 5
