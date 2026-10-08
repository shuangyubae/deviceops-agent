---
alert_type: DEPLOYMENT_REGRESSION
severity: warning
tags: deployment, rollback, regression, change-correlation
---

# DEPLOYMENT_REGRESSION Runbook

Symptoms:

- Alert starts shortly after a service deployment, configuration change, or scheduled job update.
- Multiple devices of the same type show similar symptoms.
- Metric changes align closely with the deployment time window.

Common causes:

- New service version introduced a resource leak or busy loop.
- Configuration change increased retry frequency or logging volume.
- Rollout changed batch size, cache size, or retention settings.

Recommended actions:

1. Compare alert start time with deployment and configuration change records.
2. Check whether the same version or change exists on other affected devices.
3. Roll back only after confirming the change is correlated with the symptom.
4. Preserve logs and metric snapshots before restart or rollback.
5. Add a post-deployment guardrail for the metric that regressed.
