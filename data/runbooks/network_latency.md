---
alert_type: NETWORK_LATENCY
severity: warning
tags: network, latency, packet-loss, connectivity
---

# NETWORK_LATENCY Runbook

Symptoms:

- Device heartbeat still exists, but response time is higher than normal.
- Metric uploads arrive late or in bursts.
- API calls to the device may timeout intermittently.

Common causes:

- Network congestion between gateway and device.
- Packet loss on wireless or factory network links.
- DNS or routing change after infrastructure update.
- Monitoring agent retry interval is too aggressive.

Recommended actions:

1. Check latency and packet loss between the collector and device.
2. Compare the issue with recent network or routing changes.
3. Verify whether only one device, one location, or one device type is affected.
4. Reduce aggressive retries if they amplify traffic during degraded network periods.
5. Escalate to network operations when packet loss or routing changes are confirmed.
