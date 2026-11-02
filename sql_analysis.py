"""
sql_analysis.py
Sets up a SQLite database of operational incident data and runs SQL queries
to investigate failures, identify recurring patterns, and support troubleshooting.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = "data/operations.db"

# --- Database Setup ---

def init_db():
    """Create and populate the operations database with simulated incident data."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS incidents;
        DROP TABLE IF EXISTS services;

        CREATE TABLE services (
            id      INTEGER PRIMARY KEY,
            name    TEXT NOT NULL,
            team    TEXT NOT NULL,
            tier    INTEGER NOT NULL  -- 1 = critical, 2 = standard, 3 = low priority
        );

        CREATE TABLE incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id  INTEGER NOT NULL,
            severity    TEXT NOT NULL,   -- P1, P2, P3
            status      TEXT NOT NULL,   -- open, resolved, investigating
            category    TEXT NOT NULL,   -- db, network, memory, auth, unknown
            started_at  TEXT NOT NULL,
            resolved_at TEXT,
            duration_min INTEGER,
            FOREIGN KEY (service_id) REFERENCES services(id)
        );
    """)

    services = [
        (1, "auth-service",    "platform",  1),
        (2, "payment-service", "fintech",   1),
        (3, "api-gateway",     "platform",  1),
        (4, "user-service",    "product",   2),
        (5, "report-service",  "data",      3),
    ]
    cur.executemany("INSERT INTO services VALUES (?,?,?,?)", services)

    # Simulate 60 days of incidents
    categories = ["db", "network", "memory", "auth", "unknown"]
    severities  = ["P1", "P2", "P3"]
    statuses    = ["resolved", "resolved", "resolved", "investigating", "open"]

    now = datetime.now()
    for _ in range(120):
        svc_id   = random.randint(1, 5)
        sev      = random.choices(severities, weights=[10, 30, 60])[0]
        status   = random.choice(statuses)
        category = random.choice(categories)
        started  = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
        duration = random.randint(5, 480) if status == "resolved" else None
        resolved = (started + timedelta(minutes=duration)).isoformat() if duration else None

        cur.execute("""
            INSERT INTO incidents (service_id, severity, status, category, started_at, resolved_at, duration_min)
            VALUES (?,?,?,?,?,?,?)
        """, (svc_id, sev, status, category, started.isoformat(), resolved, duration))

    conn.commit()
    conn.close()
    print(f"  Database initialised: {DB_PATH}")


# --- Query Library ---

QUERIES = {
    "top_failing_services": {
        "description": "Services with the most incidents (all time)",
        "sql": """
            SELECT s.name AS service, COUNT(*) AS total_incidents,
                   SUM(CASE WHEN i.severity = 'P1' THEN 1 ELSE 0 END) AS p1_count
            FROM incidents i
            JOIN services s ON i.service_id = s.id
            GROUP BY s.name
            ORDER BY total_incidents DESC;
        """
    },
    "recurring_categories": {
        "description": "Most common failure categories",
        "sql": """
            SELECT category, COUNT(*) AS occurrences,
                   ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM incidents), 1) AS pct
            FROM incidents
            GROUP BY category
            ORDER BY occurrences DESC;
        """
    },
    "open_incidents": {
        "description": "Currently open or investigating incidents",
        "sql": """
            SELECT i.id, s.name AS service, i.severity, i.status, i.category, i.started_at
            FROM incidents i
            JOIN services s ON i.service_id = s.id
            WHERE i.status IN ('open', 'investigating')
            ORDER BY i.severity ASC, i.started_at ASC;
        """
    },
    "avg_resolution_time": {
        "description": "Average resolution time (minutes) per service",
        "sql": """
            SELECT s.name AS service,
                   ROUND(AVG(i.duration_min), 1) AS avg_resolution_min,
                   MAX(i.duration_min) AS max_resolution_min
            FROM incidents i
            JOIN services s ON i.service_id = s.id
            WHERE i.status = 'resolved'
            GROUP BY s.name
            ORDER BY avg_resolution_min DESC;
        """
    },
    "p1_incidents_last_30_days": {
        "description": "P1 incidents in the last 30 days",
        "sql": """
            SELECT i.id, s.name AS service, i.category, i.status,
                   i.started_at, i.duration_min
            FROM incidents i
            JOIN services s ON i.service_id = s.id
            WHERE i.severity = 'P1'
              AND i.started_at >= DATE('now', '-30 days')
            ORDER BY i.started_at DESC;
        """
    },
}


def run_queries():
    """Execute all queries and print results in a clean table format."""
    if not os.path.exists(DB_PATH):
        print("  [!] Database not found. Run init_db() first.")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    results = {}

    for key, q in QUERIES.items():
        print(f"\n  ── {q['description']} ──")
        cur.execute(q["sql"])
        rows = cur.fetchall()
        results[key] = [dict(r) for r in rows]

        if not rows:
            print("    (no results)")
            continue

        # Print column headers
        cols = rows[0].keys()
        header = "  " + " | ".join(f"{c:<22}" for c in cols)
        print(header)
        print("  " + "-" * (len(header) - 2))
        for row in rows:
            print("  " + " | ".join(f"{str(row[c]):<22}" for c in cols))

    conn.close()
    return results


if __name__ == "__main__":
    print("Initialising operations database...")
    init_db()
    print("\nRunning SQL analysis queries...")
    run_queries()
