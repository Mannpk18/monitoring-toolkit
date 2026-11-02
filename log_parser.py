"""
log_parser.py
Parses application log files, detects anomalies, and produces a structured summary.

Anomaly detection rules:
  - ERROR/CRITICAL bursts: >3 errors within a 5-minute window
  - Slow response times: >3000ms in any log line
  - Repeated identical errors: same message appearing >2 times
"""

import re
import os
from collections import defaultdict
from datetime import datetime, timedelta

LOG_PATTERN = re.compile(
    r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] "
    r"\[(?P<level>INFO|WARNING|ERROR|CRITICAL)\] "
    r"\[(?P<service>[^\]]+)\] "
    r"(?P<message>.+)"
)
SLOW_THRESHOLD_MS = 3000
ERROR_BURST_WINDOW = timedelta(minutes=5)
ERROR_BURST_LIMIT = 3


def parse_log_file(filepath):
    """Parse a single log file and return a list of structured log entries."""
    entries = []
    with open(filepath, "r") as f:
        for line in f:
            match = LOG_PATTERN.match(line.strip())
            if match:
                entries.append({
                    "timestamp": datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S"),
                    "level": match.group("level"),
                    "service": match.group("service"),
                    "message": match.group("message"),
                })
    return entries


def detect_anomalies(entries):
    """
    Run anomaly detection over parsed log entries.
    Returns a list of anomaly dicts describing each issue found.
    """
    anomalies = []

    # Group entries by service
    by_service = defaultdict(list)
    for e in entries:
        by_service[e["service"]].append(e)

    for service, logs in by_service.items():
        error_logs = [e for e in logs if e["level"] in ("ERROR", "CRITICAL")]

        # --- Rule 1: Error burst detection ---
        for i, entry in enumerate(error_logs):
            window_end = entry["timestamp"] + ERROR_BURST_WINDOW
            burst = [e for e in error_logs if entry["timestamp"] <= e["timestamp"] <= window_end]
            if len(burst) >= ERROR_BURST_LIMIT:
                anomalies.append({
                    "type": "ERROR_BURST",
                    "service": service,
                    "timestamp": entry["timestamp"],
                    "detail": f"{len(burst)} errors/criticals within 5 minutes starting {entry['timestamp']}",
                })
                break  # One burst report per service is enough

        # --- Rule 2: Slow response time ---
        for entry in logs:
            ms_match = re.search(r"(\d+)ms", entry["message"])
            if ms_match and int(ms_match.group(1)) > SLOW_THRESHOLD_MS:
                anomalies.append({
                    "type": "SLOW_RESPONSE",
                    "service": service,
                    "timestamp": entry["timestamp"],
                    "detail": f"Response time {ms_match.group(1)}ms exceeds {SLOW_THRESHOLD_MS}ms threshold",
                })

        # --- Rule 3: Repeated identical errors ---
        message_counts = defaultdict(int)
        for entry in error_logs:
            message_counts[entry["message"]] += 1
        for msg, count in message_counts.items():
            if count > 2:
                anomalies.append({
                    "type": "REPEATED_ERROR",
                    "service": service,
                    "timestamp": None,
                    "detail": f"Message appeared {count}x: \"{msg}\"",
                })

    return anomalies


def parse_all_logs(log_dir="logs"):
    """Parse all .log files in a directory and return combined entries + anomalies."""
    all_entries = []
    if not os.path.exists(log_dir):
        print(f"  [!] Log directory '{log_dir}' not found.")
        return [], []

    for filename in os.listdir(log_dir):
        if filename.endswith(".log"):
            path = os.path.join(log_dir, filename)
            entries = parse_log_file(path)
            all_entries.extend(entries)

    anomalies = detect_anomalies(all_entries)
    return all_entries, anomalies


def summarize(entries, anomalies):
    """Print a human-readable summary of log analysis results."""
    level_counts = defaultdict(int)
    service_counts = defaultdict(int)
    for e in entries:
        level_counts[e["level"]] += 1
        service_counts[e["service"]] += 1

    print("=" * 55)
    print("  LOG ANALYSIS SUMMARY")
    print("=" * 55)
    print(f"  Total log entries parsed : {len(entries)}")
    print(f"  Total anomalies detected : {len(anomalies)}")
    print()
    print("  Log levels breakdown:")
    for level in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
        print(f"    {level:<12} {level_counts.get(level, 0)}")
    print()
    print("  Entries per service:")
    for svc, count in sorted(service_counts.items()):
        print(f"    {svc:<22} {count}")
    print()
    if anomalies:
        print("  Anomalies detected:")
        for a in anomalies:
            ts = a["timestamp"].strftime("%H:%M:%S") if a["timestamp"] else "N/A"
            print(f"    [{a['type']}] {a['service']} @ {ts}")
            print(f"      → {a['detail']}")
    else:
        print("  No anomalies detected.")
    print("=" * 55)
