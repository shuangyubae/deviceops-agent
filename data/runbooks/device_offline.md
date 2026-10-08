---
alert_type: DEVICE_OFFLINE
severity: critical
tags: heartbeat, network, power, monitoring-agent
---

# DEVICE_OFFLINE Runbook

Symptoms:

- Heartbeat is missing.
- CPU and memory readings may be zero or stale.

Common causes:

- Network interruption.
- Device powered off.
- Monitoring agent stopped.

Recommended actions:

1. Check last heartbeat timestamp.
2. Verify network connectivity.
3. Confirm power state or monitoring agent status.
