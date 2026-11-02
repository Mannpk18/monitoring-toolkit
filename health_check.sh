#!/usr/bin/env bash
# =============================================================================
# health_check.sh
# Automated operational health check script for simulated services.
#
# Usage:
#   ./health_check.sh                  # Run all checks, output to terminal
#   ./health_check.sh --report         # Save report to reports/health_<date>.txt
#   ./health_check.sh --quiet          # Suppress output (for cron jobs)
#
# Schedule with cron (every 30 minutes):
#   */30 * * * * /path/to/health_check.sh --report --quiet
# =============================================================================

set -euo pipefail

# --- Config ---
LOG_DIR="logs"
REPORT_DIR="reports"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE_SLUG=$(date '+%Y%m%d_%H%M%S')
REPORT_FILE="${REPORT_DIR}/health_${DATE_SLUG}.txt"
SAVE_REPORT=false
QUIET=false
EXIT_CODE=0

# Error thresholds
MAX_ERROR_RATE=10          # % of lines that can be ERROR/CRITICAL
MAX_LOG_AGE_MINUTES=60     # logs older than this trigger a warning
SLOW_MS_THRESHOLD=3000     # ms threshold for slow response detection

# Colour codes (suppressed in quiet mode)
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# --- Argument parsing ---
for arg in "$@"; do
  case $arg in
    --report) SAVE_REPORT=true ;;
    --quiet)  QUIET=true ;;
  esac
done

# --- Helpers ---
log()  { $QUIET || echo -e "$*"; }
info() { log "${CYAN}[INFO]${RESET}  $*"; }
ok()   { log "${GREEN}[OK]${RESET}    $*"; }
warn() { log "${YELLOW}[WARN]${RESET}  $*"; EXIT_CODE=1; }
fail() { log "${RED}[FAIL]${RESET}  $*"; EXIT_CODE=2; }

# Tee to report file if --report
if $SAVE_REPORT; then
  mkdir -p "$REPORT_DIR"
  exec > >(tee "$REPORT_FILE") 2>&1
fi

# =============================================================================
log ""
log "${BOLD}=============================================${RESET}"
log "${BOLD}  OPERATIONAL HEALTH CHECK${RESET}"
log "${BOLD}  ${TIMESTAMP}${RESET}"
log "${BOLD}=============================================${RESET}"
log ""

# --- Check 1: Log directory exists ---
info "Checking log directory..."
if [[ ! -d "$LOG_DIR" ]]; then
  fail "Log directory '$LOG_DIR' not found. Has generate_logs.py been run?"
  exit 2
fi

LOG_FILES=("${LOG_DIR}"/*.log)
if [[ ${#LOG_FILES[@]} -eq 0 ]]; then
  fail "No .log files found in $LOG_DIR"
  exit 2
fi
ok "Found ${#LOG_FILES[@]} log file(s)"

# --- Check 2: Log file freshness ---
log ""
info "Checking log file freshness (threshold: ${MAX_LOG_AGE_MINUTES} min)..."
for f in "${LOG_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then continue; fi
  # Last modified time in seconds since epoch
  mod_time=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
  now_time=$(date +%s)
  age_min=$(( (now_time - mod_time) / 60 ))
  name=$(basename "$f")
  if (( age_min > MAX_LOG_AGE_MINUTES )); then
    warn "$name — last modified ${age_min} minutes ago"
  else
    ok "$name — ${age_min} min ago"
  fi
done

# --- Check 3: Error rate per service ---
log ""
info "Analysing error rates (threshold: ${MAX_ERROR_RATE}%)..."
for f in "${LOG_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then continue; fi
  name=$(basename "$f" .log)
  total=$(wc -l < "$f")
  errors=$(grep -cE "\[(ERROR|CRITICAL)\]" "$f" || true)
  if (( total == 0 )); then
    warn "$name — log file is empty"
    continue
  fi
  rate=$(( errors * 100 / total ))
  if (( rate >= MAX_ERROR_RATE )); then
    fail "$name — error rate ${rate}% (${errors}/${total} lines)"
  else
    ok "$name — error rate ${rate}% (${errors}/${total} lines)"
  fi
done

# --- Check 4: Critical events in last hour ---
log ""
info "Scanning for CRITICAL events..."
RECENT_CUTOFF=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
  || date -v-1H '+%Y-%m-%d %H:%M:%S' 2>/dev/null \
  || echo "")

CRIT_COUNT=0
for f in "${LOG_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then continue; fi
  count=$(grep -c "\[CRITICAL\]" "$f" || true)
  if (( count > 0 )); then
    fail "$(basename "$f" .log) — ${count} CRITICAL event(s) found"
    CRIT_COUNT=$((CRIT_COUNT + count))
  fi
done
if (( CRIT_COUNT == 0 )); then
  ok "No CRITICAL events found"
fi

# --- Check 5: Slow response detection ---
log ""
info "Checking for slow responses (>${SLOW_MS_THRESHOLD}ms)..."
SLOW_TOTAL=0
for f in "${LOG_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then continue; fi
  slow=$(grep -oE '[0-9]+ms' "$f" \
    | grep -oE '[0-9]+' \
    | awk -v t="$SLOW_MS_THRESHOLD" '$1 > t' \
    | wc -l || true)
  if (( slow > 0 )); then
    warn "$(basename "$f" .log) — ${slow} slow response(s) detected"
    SLOW_TOTAL=$((SLOW_TOTAL + slow))
  fi
done
if (( SLOW_TOTAL == 0 )); then
  ok "No slow responses detected"
fi

# --- Check 6: Disk space ---
log ""
info "Checking disk space on current partition..."
DISK_PCT=$(df . | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if (( DISK_PCT >= 90 )); then
  fail "Disk usage critical: ${DISK_PCT}%"
elif (( DISK_PCT >= 75 )); then
  warn "Disk usage elevated: ${DISK_PCT}%"
else
  ok "Disk usage: ${DISK_PCT}%"
fi

# --- Summary ---
log ""
log "${BOLD}=============================================${RESET}"
if (( EXIT_CODE == 0 )); then
  log "${GREEN}${BOLD}  RESULT: ALL CHECKS PASSED${RESET}"
elif (( EXIT_CODE == 1 )); then
  log "${YELLOW}${BOLD}  RESULT: WARNINGS DETECTED — review above${RESET}"
else
  log "${RED}${BOLD}  RESULT: FAILURES DETECTED — action required${RESET}"
fi
log "${BOLD}=============================================${RESET}"
log ""

$SAVE_REPORT && info "Report saved to: $REPORT_FILE"

exit $EXIT_CODE
