"""Automation worker processing scheduled jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from prometheus_client import Histogram, Counter, Gauge, start_http_server
from sqlmodel import select
from uuid import UUID

from chatbot.automation.connectors import ConnectorContext, build_connector
from chatbot.automation.service import AUTOMATION_FAILURES, AUTOMATION_QUEUE_GAUGE
from chatbot.core.config import AppSettings
from chatbot.core.db import models
from chatbot.core.db.session import session_scope
from chatbot.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)

AUTOMATION_LATENCY = Histogram(
    "automation_latency_seconds",
    "Execution latency for automation jobs.",
)

AUTOMATION_FAILURE_COUNTER = Counter(
    "automation_failures_worker_total",
    "Automation job failures recorded by the worker.",
    ["tenant_id"],
)

AUTOMATION_ACTIVE_RULES = Gauge(
    "automation_active_rules",
    "Number of active automation rules loaded by the worker.",
)


class AutomationWorker:
    """Schedules and executes automation jobs."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._scheduled_rules: dict[str, Any] = {}
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        logger.info("automation worker starting")
        self._scheduler.start()
        await self._refresh_rules()
        self._scheduler.add_job(self._refresh_rules, "interval", seconds=60)
        if self._settings.telemetry.metrics_port:
            start_http_server(
                self._settings.telemetry.metrics_port,
                addr=self._settings.telemetry.metrics_host,
            )
        try:
            while not self._shutdown.is_set():
                await self._process_jobs()
                await asyncio.sleep(5)
        finally:
            self._scheduler.shutdown(wait=False)

    async def stop(self) -> None:
        self._shutdown.set()

    async def _refresh_rules(self) -> None:
        logger.info("automation worker refreshing rules")
        for job in self._scheduled_rules.values():
            try:
                self._scheduler.remove_job(job.id)
            except Exception:
                logger.debug("failed to remove job", exc_info=True)
        self._scheduled_rules.clear()

        with session_scope(self._settings) as session:
            rules = list(
                session.exec(
                    select(models.AutomationRule).where(
                        models.AutomationRule.is_active.is_(True),
                        models.AutomationRule.schedule_expression.is_not(None),
                    )
                )
            )
        AUTOMATION_ACTIVE_RULES.set(len(rules))
        for rule in rules:
            try:
                trigger = CronTrigger.from_crontab(
                    rule.schedule_expression, timezone=UTC
                )
            except Exception:
                logger.warning(
                    "invalid schedule expression",
                    extra={
                        "rule_id": str(rule.id),
                        "expression": rule.schedule_expression,
                    },
                )
                continue
            job = self._scheduler.add_job(
                self._enqueue_rule, trigger, args=[str(rule.id)]
            )
            self._scheduled_rules[str(rule.id)] = job

    async def _enqueue_rule(self, rule_id: str) -> None:
        logger.info("enqueuing automation rule", extra={"rule_id": rule_id})
        with session_scope(self._settings) as session:
            rule = session.get(models.AutomationRule, rule_id)
            if rule is None or not rule.is_active:
                return
            job = models.AutomationJob(
                rule_id=rule.id,
                tenant_id=rule.tenant_id,
                brand_id=rule.brand_id,
                status=models.AutomationJobStatus.PENDING,
                scheduled_for=datetime.now(tz=UTC),
                payload={"trigger": "schedule"},
            )
            session.add(job)
            session.commit()
            AUTOMATION_QUEUE_GAUGE.labels(str(rule.tenant_id)).inc()

    async def _process_jobs(self) -> None:
        with session_scope(self._settings) as session:
            jobs = list(
                session.exec(
                    select(models.AutomationJob)
                    .where(
                        models.AutomationJob.status
                        == models.AutomationJobStatus.PENDING
                    )
                    .order_by(models.AutomationJob.created_at)
                    .limit(10)
                )
            )
            if not jobs:
                return
            for job in jobs:
                await self._execute_job(session, job)

    async def _execute_job(self, session, job: models.AutomationJob) -> None:
        rule = session.get(models.AutomationRule, job.rule_id)
        if rule is None:
            job.status = models.AutomationJobStatus.CANCELLED
            session.add(job)
            session.commit()
            return

        job.status = models.AutomationJobStatus.RUNNING
        job.started_at = datetime.now(tz=UTC)
        job.attempts += 1
        session.add(job)
        session.commit()

        start_time = datetime.now(tz=UTC)
        try:
            policy_engine = PolicyEngine(session)
            decision = policy_engine.evaluate(
                tenant_id=job.tenant_id,
                brand_id=job.brand_id,
                channel_id=UUID(int=0),
                message=job.payload.get("sample", ""),
            )
            if not decision.allow_response:
                raise RuntimeError(f"policy_denied:{decision.reason}")

            connector = build_connector(rule.action_type)
            context = ConnectorContext(
                tenant_id=job.tenant_id,
                brand_id=job.brand_id,
                rule_id=rule.id,
            )
            connector.execute(rule.action_payload, dry_run=False, context=context)
            job.status = models.AutomationJobStatus.COMPLETED
            job.completed_at = datetime.now(tz=UTC)
            session.add(job)
            session.commit()
            AUTOMATION_QUEUE_GAUGE.labels(str(job.tenant_id)).dec()
        except Exception as exc:
            logger.exception("automation job failed", extra={"job_id": str(job.id)})
            job.status = models.AutomationJobStatus.FAILED
            job.failure_reason = str(exc)
            session.add(job)
            session.commit()
            AUTOMATION_FAILURE_COUNTER.labels(str(job.tenant_id)).inc()
            AUTOMATION_FAILURES.labels(str(job.tenant_id)).inc()
            if job.attempts < rule.max_retries:
                job.status = models.AutomationJobStatus.PENDING
                job.scheduled_for = datetime.now(tz=UTC) + timedelta(
                    seconds=2**job.attempts
                )
                session.add(job)
                session.commit()
        finally:
            elapsed = (datetime.now(tz=UTC) - start_time).total_seconds()
            AUTOMATION_LATENCY.observe(elapsed)


async def _main() -> None:
    settings = AppSettings.load()
    worker = AutomationWorker(settings)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(_main())
