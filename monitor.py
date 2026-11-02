"""
monitor.py
Main entry point for the Production Monitoring & Log Analysis Toolkit.

Runs the full pipeline:
  1. Generate simulated service logs
  2. Parse logs and detect anomalies
  3. Initialise SQLite DB and run SQL analysis
  4. Write a consolidated health report

Usage:
  python monitor.py             # Full run
  python monitor.py --no-regen  # Skip log regeneration (reuse existing logs)
"""

import sys
import os
from datetime import datetime

from generate_logs import generate_logs
from log_parser    import parse_all_logs, summarize
from sql_analysis  import init_db, run_queries

REPORT_DIR = "reports"


def write_report(entries, anomalies, sql_results):
    """Write a consolidated plaintext health report to reports/."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{REPORT_DIR}/report_{slug}.txt"

    level_counts = {}
    for e in entries:
        level_counts[e["level"]] = level_counts.get(e["level"], 0) + 1

    with open(path, "w") as f:
        f.write("=" * 55 + "\n")
        f.write("  MONITORING TOOLKIT — HEALTH REPORT\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 55 + "\n\n")

        # Log summary
        f.write("LOG SUMMARY\n")
        f.write(f"  Total entries  : {len(entries)}\n")
        f.write(f"  Anomalies found: {len(anomalies)}\n")
        for level in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
            f.write(f"  {level:<12}: {level_counts.get(level, 0)}\n")
        f.write("\n")

        # Anomalies
        f.write("ANOMALIES\n")
        if anomalies:
            for a in anomalies:
                ts = a["timestamp"].strftime("%H:%M:%S") if a["timestamp"] else "N/A"
                f.write(f"  [{a['type']}] {a['service']} @ {ts}\n")
                f.write(f"    {a['detail']}\n")
        else:
            f.write("  None detected.\n")
        f.write("\n")

        # SQL highlights
        f.write("TOP FAILING SERVICES (SQL)\n")
        for row in sql_results.get("top_failing_services", []):
            f.write(f"  {row['service']:<22} incidents={row['total_incidents']}  p1={row['p1_count']}\n")
        f.write("\n")

        f.write("OPEN / INVESTIGATING INCIDENTS\n")
        open_incidents = sql_results.get("open_incidents", [])
        if open_incidents:
            for row in open_incidents:
                f.write(f"  [{row['severity']}] {row['service']:<20} {row['category']:<10} {row['status']}\n")
        else:
            f.write("  None.\n")

    print(f"\n  Report saved → {path}")
    return path


def main():
    regen = "--no-regen" not in sys.argv

    print("\n" + "=" * 55)
    print("  PRODUCTION MONITORING TOOLKIT")
    print("=" * 55)

    # Step 1: Generate logs
    if regen:
        print("\n[1/4] Generating simulated service logs...")
        generate_logs()
    else:
        print("\n[1/4] Skipping log regeneration (--no-regen)")

    # Step 2: Parse logs + detect anomalies
    print("\n[2/4] Parsing logs and detecting anomalies...")
    entries, anomalies = parse_all_logs("logs")
    print(f"  Parsed {len(entries)} entries, found {len(anomalies)} anomaly/anomalies")
    print()
    summarize(entries, anomalies)

    # Step 3: SQL analysis
    print("\n[3/4] Running SQL analysis on operations database...")
    init_db()
    sql_results = run_queries()

    # Step 4: Write report
    print("\n[4/4] Writing consolidated health report...")
    write_report(entries, anomalies, sql_results)

    print("\n  All checks complete.")
    print("  Run './health_check.sh --report' for the shell-based health check.\n")


if __name__ == "__main__":
    main()
