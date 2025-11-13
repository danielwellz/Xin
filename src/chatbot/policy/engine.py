"""Tenant policy evaluation and retrieval tuning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID

from prometheus_client import Counter
from sqlmodel import Session, select

from chatbot.core.db import models

POLICY_DENIALS = Counter(
    "policy_denials_total",
    "Total number of responses denied by policy evaluation.",
    ["reason"],
)

RETRIEVAL_HITS = Counter(
    "retrieval_hits_total",
    "Total number of retrieval hits returned to the LLM.",
    ["tenant_id"],
)


@dataclass(slots=True)
class PolicyDecision:
    allow_response: bool
    reason: str | None
    top_k: int
    min_score: float
    filters: dict[str, Any] | None
    hybrid_weight: float
    fallback_llm: str | None
    context_budget_tokens: int
    policy_version: int | None = None


class PolicyEngine:
    """Evaluates policy versions and retrieval configs for a tenant."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(
        self,
        *,
        tenant_id: UUID,
        brand_id: UUID,
        channel_id: UUID,
        message: str,
        timestamp: datetime | None = None,
    ) -> PolicyDecision:
        published_policy = self._load_policy(tenant_id)
        retrieval_config = self._load_retrieval_config(tenant_id)
        allow_response = True
        reason = None
        ts = timestamp or datetime.now(tz=UTC)

        if published_policy:
            guardrails = published_policy.policy_json.get("guardrails", {})
            if self._is_within_quiet_hours(
                guardrails.get("quiet_hours"), ts, tenant_id
            ):
                allow_response = False
                reason = "quiet_hours"
            keywords = guardrails.get("block_keywords") or []
            for keyword in keywords:
                if keyword.lower() in message.lower():
                    allow_response = False
                    reason = "keyword_block"
                    break

        decision = PolicyDecision(
            allow_response=allow_response,
            reason=reason,
            top_k=retrieval_config.max_documents,
            min_score=retrieval_config.min_score,
            filters=retrieval_config.filters,
            hybrid_weight=retrieval_config.hybrid_weight,
            fallback_llm=retrieval_config.fallback_llm,
            context_budget_tokens=retrieval_config.context_budget_tokens,
            policy_version=published_policy.version if published_policy else None,
        )

        if not allow_response:
            POLICY_DENIALS.labels(reason or "unspecified").inc()
        return decision

    def _load_policy(self, tenant_id: UUID) -> models.PolicyVersion | None:
        return self._session.exec(
            select(models.PolicyVersion)
            .where(
                models.PolicyVersion.tenant_id == tenant_id,
                models.PolicyVersion.status == models.PolicyStatus.PUBLISHED,
            )
            .order_by(models.PolicyVersion.version.desc())
        ).first()

    def _load_retrieval_config(self, tenant_id: UUID) -> models.RetrievalConfig:
        config = self._session.exec(
            select(models.RetrievalConfig).where(
                models.RetrievalConfig.tenant_id == tenant_id
            )
        ).first()
        if config:
            return config
        config = models.RetrievalConfig(tenant_id=tenant_id)
        self._session.add(config)
        self._session.flush()
        return config

    @staticmethod
    def _is_within_quiet_hours(
        quiet_hours: list[dict[str, Any]] | None,
        timestamp: datetime,
        tenant_id: UUID,
    ) -> bool:
        if not quiet_hours:
            return False
        for window in quiet_hours:
            start_str = window.get("start")
            end_str = window.get("end")
            tz_name = window.get("timezone") or "UTC"
            if not start_str or not end_str:
                continue
            try:
                start = _parse_time(start_str)
                end = _parse_time(end_str)
            except ValueError:
                continue
            localized = timestamp
            if tz_name.upper() != "UTC":
                # Placeholder for timezone adjustments; keep UTC for now.
                localized = timestamp
            current_time = localized.time()
            normalized_start = start if start.tzinfo else start.replace(tzinfo=UTC)
            normalized_end = end if end.tzinfo else end.replace(tzinfo=UTC)
            normalized_current = localized.timetz()
            if normalized_current.tzinfo is None:
                normalized_current = normalized_current.replace(tzinfo=UTC)

            if normalized_start <= normalized_end:
                if normalized_start <= normalized_current <= normalized_end:
                    return True
            else:
                if (
                    normalized_current >= normalized_start
                    or normalized_current <= normalized_end
                ):
                    return True
        return False


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute), tzinfo=UTC)
