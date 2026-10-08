---
alert_type: DISK_HIGH
severity: warning
tags: disk, logs, cache, retention, storage
---

# DISK_HIGH Runbook

Symptoms:

- Disk usage remains above 85% for more than five minutes.
- New log files, cache files, or temporary files grow faster than expected.
- The device may stay online while write latency increases or data collection becomes delayed.

Common causes:

- Application logs are not rotated or compressed.
- Temporary files are not cleaned after batch jobs or failed uploads.
- Local cache grows without an upper limit.
- Historical metrics, images, or diagnostic dumps are retained for too long.
- A process is repeatedly writing error logs after a failure loop.

Recommended actions:

1. Check disk usage by directory and identify the fastest-growing path.
2. Inspect recent log growth and verify whether log rotation is enabled.
3. Clean safe temporary files only after confirming they are not needed for diagnosis.
4. Review recent deployments, batch jobs, or retry loops that may produce large files.
5. Add retention limits for logs, caches, metrics, and diagnostic dumps.
6. Escalate to human review before deleting unknown files or user data.
