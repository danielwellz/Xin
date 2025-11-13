# Status Page Draft — Xin ChatBot Launch

**Incident Title:** Scheduled Maintenance — Xin ChatBot GA Launch  
**Status:** Monitoring (once complete)  
**Start Time:**  
**Expected Duration:** 30 minutes

## Summary
We are deploying the GA build of Xin ChatBot to production. During this window
we may briefly place the API and gateway into maintenance mode while we run
database migrations and smoke tests.

## Impact
- Operator console: read-only mode
- Channel webhooks: queue messages, deliver once rollout completes
- Automation jobs: paused until verification finishes

## Timeline (UTC)
- 00:00 — Maintenance mode enabled
- 00:05 — Deploy orchestrator/gateway containers
- 00:10 — Run migrations + data integrity checks
- 00:20 — Perform synthetic conversations and alert validation
- 00:30 — Exit maintenance mode, monitor dashboards hourly for first 24h

## Next Steps
1. Post-launch monitoring cadence: hourly first day via war room Slack channel,
   then daily stand-ups for the remainder of the week.
2. Contact support@xinbot.ir if you experience issues outside the window.
