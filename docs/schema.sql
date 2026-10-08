CREATE TABLE devices (
    device_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    device_type VARCHAR(64) NOT NULL,
    location VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL
);

CREATE TABLE metric_points (
    id BIGINT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    timestamp DATETIME NOT NULL,
    cpu_percent DOUBLE NOT NULL,
    memory_percent DOUBLE NOT NULL,
    disk_percent DOUBLE NOT NULL,
    heartbeat_ok BOOLEAN NOT NULL
);

CREATE TABLE historical_alerts (
    id BIGINT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    alert_type VARCHAR(64) NOT NULL,
    root_cause TEXT NOT NULL,
    resolution TEXT NOT NULL
);

CREATE TABLE recent_deployments (
    id BIGINT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    changed_at DATETIME NOT NULL,
    change_type VARCHAR(64) NOT NULL,
    summary TEXT NOT NULL,
    risk_hint TEXT NOT NULL
);

CREATE TABLE diagnosis_reports (
    run_id VARCHAR(128) PRIMARY KEY,
    alert_id VARCHAR(128) NOT NULL,
    report_json TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
