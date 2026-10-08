---
alert_type: MEMORY_HIGH
severity: warning
tags: memory, buffer, cache, inference
---

# MEMORY_HIGH Runbook

Symptoms:

- Memory usage keeps increasing and remains above 90%.
- CPU may stay normal while memory pressure grows.

Common causes:

- Buffer not released after image inference timeout.
- Cache size is not bounded.
- Long-running process keeps stale session data.

Recommended actions:

1. Check process memory growth.
2. Inspect cache and buffer release logic.
3. Restart service only after recording evidence.
