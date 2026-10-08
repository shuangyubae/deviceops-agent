---
alert_type: CPU_HIGH
severity: warning
tags: cpu, scheduler, workload, deployment
---

# CPU_HIGH Runbook

Symptoms:

- CPU usage remains above 90% for more than five minutes.
- The device is still online and heartbeat remains healthy.

Common causes:

- Duplicated scheduled batch job.
- Abnormal image processing or inference workload.
- Recent deployment introduced a busy loop.

Recommended actions:

1. Check top CPU processes.
2. Compare with recent deployments or scheduler changes.
3. Limit or restart the abnormal worker after human approval.
