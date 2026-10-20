#!/bin/zsh
# Daily biotech-tracker news sweep. Run by launchd (see com.biotech-tracker.sweep.plist)
# or by hand: ./sweep/run_sweep.sh
set -u
ROOT="/Users/curiecha/biotech-tracker"
LOG_DIR="$ROOT/sweep/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%Y-%m-%d).log"
export PATH="/Users/curiecha/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cd "$ROOT" || exit 1
# optional credentials for collect_leads.py (SEC_USER_AGENT, BSKY_HANDLE, BSKY_APP_PASSWORD)
[ -f "$ROOT/sweep/.env" ] && { set -a; source "$ROOT/sweep/.env"; set +a; }
{
  echo "=== sweep start $(date) ==="
  # bulk company list + logos (no LLM needed), Mondays only: it re-downloads ~95k trial records
  # and the list barely changes day to day. The sweep below rebuilds web/index.html afterwards.
  if [ "$(date +%u)" = "1" ] || [ ! -f "$ROOT/data/universe.csv" ]; then
    python3 "$ROOT/sweep/build_universe.py"
    python3 "$ROOT/sweep/fetch_logos.py"   # only fetches logos not already in web/logos/
  fi
  python3 "$ROOT/sweep/fetch_trials.py"   # daily ClinicalTrials.gov snapshot (last 90 days of milestones)
  claude -p "$(cat "$ROOT/sweep/PROMPT.md")" \
    --permission-mode acceptEdits \
    --allowedTools "WebSearch" "WebFetch" "Read" "Edit" "Write" "Glob" "Grep" "Bash(python3:*)"
  echo "=== sweep end $(date) exit=$? ==="
} >> "$LOG" 2>&1
