# Production Monitoring & Log Analysis Toolkit

A lightweight production support toolkit that parses application logs, detects anomalies, queries operational data with SQL, and automates health checks via Linux shell scripts.

---

## Project Structure

```
monitoring-toolkit/
├── logs/                  # Simulated service log files (auto-generated)
├── data/                  # SQLite operational database
├── reports/               # Auto-generated health reports
├── generate_logs.py       # Simulates realistic multi-service log output
├── log_parser.py          # Parses logs and detects anomalies
├── sql_analysis.py        # SQLite schema + SQL query library
├── monitor.py             # Main orchestrator — runs the full pipeline
├── health_check.sh        # Bash script for scheduled health checks
└── README.md
```

---

## Quick Start

### 1. Run the full Python pipeline

```bash
python monitor.py
```

This will:
- Generate simulated logs for 4 services (`auth-service`, `payment-service`, `api-gateway`, `user-service`)
- Parse all logs and detect anomalies (error bursts, slow responses, repeated errors)
- Initialise a SQLite database and run 5 SQL analysis queries
- Save a consolidated health report to `reports/`

To reuse existing logs without regenerating:

```bash
python monitor.py --no-regen
```

---

### 2. Run the shell health check

```bash
chmod +x health_check.sh
./health_check.sh
```

With a saved report:

```bash
./health_check.sh --report
```

To schedule with cron (every 30 minutes):

```bash
*/30 * * * * /path/to/health_check.sh --report --quiet
```

---

## Components

### `log_parser.py` — Anomaly Detection

Parses structured log lines using regex and applies three detection rules:

| Rule | Trigger |
|---|---|
| `ERROR_BURST` | 3+ errors/criticals within a 5-minute window |
| `SLOW_RESPONSE` | Any response time exceeding 3000ms |
| `REPEATED_ERROR` | Same error message appearing more than twice |

### `sql_analysis.py` — Operational SQL Queries

Uses a SQLite database (`data/operations.db`) with an `incidents` and `services` schema. Includes 5 queries:

- Top failing services by incident count
- Most common failure categories (% breakdown)
- Open / investigating incidents
- Average resolution time per service
- P1 incidents in the last 30 days

### `health_check.sh` — Shell Automation

Runs 6 checks and colour-codes output by severity:

1. Log directory existence
2. Log file freshness (configurable threshold)
3. Error rate per service
4. Critical event scan
5. Slow response detection
6. Disk space usage

Exits with code `0` (all clear), `1` (warnings), or `2` (failures) — compatible with monitoring systems and cron alerting.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Log parsing & orchestration | Python 3, `re`, `collections`, `sqlite3` |
| Operational data & queries | SQL (SQLite) |
| Shell automation | Bash (Linux/macOS) |
| Data storage | SQLite (zero-dependency) |

---

## Sample Output

```
[1/4] Generating simulated service logs...
  Generated: logs/auth-service.log
  Generated: logs/payment-service.log
  ...

[2/4] Parsing logs and detecting anomalies...
=======================================================
  LOG ANALYSIS SUMMARY
=======================================================
  Total log entries parsed : 1,847
  Total anomalies detected : 12
  ...

[3/4] Running SQL analysis on operations database...
  ── Services with the most incidents ──
  service                | total_incidents | p1_count
  -------------------------------------------------
  payment-service        | 28              | 4
  ...
```
