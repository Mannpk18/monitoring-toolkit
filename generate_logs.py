"""
generate_logs.py
Generates realistic simulated application logs for testing the monitoring toolkit.
Run this once before running monitor.py.
"""

import random
import os
from datetime import datetime, timedelta

SERVICES = ["auth-service", "payment-service", "api-gateway", "user-service"]

LOG_TEMPLATES = {
    "INFO": [
        "Request processed successfully in {ms}ms",
        "User {uid} logged in",
        "Cache hit for key={key}",
        "Health check passed",
        "Config reloaded",
    ],
    "WARNING": [
        "Response time {ms}ms exceeds threshold",
        "Retry attempt {n} for downstream call",
        "Memory usage at {pct}%",
        "Rate limit approaching for client {uid}",
        "Deprecated endpoint called by {uid}",
    ],
    "ERROR": [
        "Database connection timeout after {ms}ms",
        "Unhandled exception in request handler: NullPointerException",
        "Failed to connect to upstream service: ConnectionRefused",
        "Authentication failed for user {uid}: invalid token",
        "Disk write error: no space left on device",
    ],
    "CRITICAL": [
        "Service crashed: out of memory",
        "SSL certificate expired",
        "Data corruption detected in table=orders",
        "All DB replicas unreachable",
    ],
}

def random_line(level, service, timestamp):
    template = random.choice(LOG_TEMPLATES[level])
    msg = template.format(
        ms=random.randint(50, 9000),
        uid=f"u{random.randint(1000,9999)}",
        key=f"cache:{random.randint(1,100)}",
        n=random.randint(1, 5),
        pct=random.randint(70, 99),
    )
    return f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] [{service}] {msg}\n"


def generate_logs():
    os.makedirs("logs", exist_ok=True)
    now = datetime.now()

    for service in SERVICES:
        path = f"logs/{service}.log"
        with open(path, "w") as f:
            t = now - timedelta(hours=6)
            while t <= now:
                # Weighted level distribution
                level = random.choices(
                    ["INFO", "WARNING", "ERROR", "CRITICAL"],
                    weights=[70, 18, 10, 2]
                )[0]
                f.write(random_line(level, service, t))
                t += timedelta(seconds=random.randint(5, 60))
        print(f"  Generated: {path}")


if __name__ == "__main__":
    print("Generating simulated service logs...")
    generate_logs()
    print("Done.\n")
