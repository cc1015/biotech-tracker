#!/bin/zsh
# Daily biotech-tracker news sweep. Run by launchd (see com.biotech-tracker.sweep.plist)
# or by hand: ./sweep/run_sweep.sh
set -u
ROOT="/Users/curiecha/biotech-tracker"
LOG_DIR="$ROOT/sweep/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%Y-%m-%d).log"
export PATH="/Users/curiecha/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
# what the sweep writes; only these paths are committed
OUTPUT=(data notes web/logos)
# detached checkout of origin/main, used to carry each sweep commit onto main (GitHub Pages deploys main)
MAIN_WT="$ROOT/sweep/main-worktree"

# Commit the sweep's output on dev and push it, then apply the same commit to main and push that.
# Skips (and says why in the log) rather than guessing whenever something looks off.
publish() {
  local branch p sha
  local -a paths
  branch="$(git branch --show-current)"
  [ "$branch" = "dev" ] || { echo "publish: on '$branch', not dev; not committing"; return 1; }
  for p in $OUTPUT; do [ -e "$p" ] && paths+=("$p"); done   # notes/ appears after the first sweep
  git add -A -- $paths
  git diff --cached --quiet -- $paths && { echo "publish: nothing changed"; return 0; }
  git commit -q -m "$(date +%m_%d_%Y) sweep" -- $paths || return 1
  git pull -q --rebase --autostash origin dev || { git rebase --abort 2>/dev/null; echo "publish: pull of dev failed"; return 1; }
  git push -q origin dev || { echo "publish: push of dev failed"; return 1; }
  sha="$(git rev-parse HEAD)"
  [ -d "$MAIN_WT" ] || git worktree add -q --detach "$MAIN_WT" origin/main || return 1
  git -C "$MAIN_WT" checkout -q --detach origin/main || return 1
  git -C "$MAIN_WT" cherry-pick "$sha" >/dev/null ||
    { git -C "$MAIN_WT" cherry-pick --abort; echo "publish: $sha does not apply to main; dev pushed, main left alone"; return 1; }
  git -C "$MAIN_WT" push -q origin HEAD:main || { echo "publish: push of main failed"; return 1; }
  echo "publish: pushed $(git rev-parse --short "$sha") to dev and main"
}

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
  python3 "$ROOT/sweep/fetch_frontiers.py"   # Frontiers papers + preprints (preprint days are cached)
  python3 "$ROOT/sweep/fetch_field_scores.py"   # silo scores from OpenAlex + preprint momentum; needs OPENALEX_API_KEY
  claude -p "$(cat "$ROOT/sweep/PROMPT.md")" \
    --permission-mode acceptEdits \
    --allowedTools "WebSearch" "WebFetch" "Read" "Edit" "Write" "Glob" "Grep" "Bash(python3:*)"
  rc=$?
  echo "=== sweep end $(date) exit=$rc ==="
  # first successful sweep of each month: re-check the pharma, builder, investor and lab profiles,
  # which the daily sweep never revisits. The stamp makes a missed or failed month retry the next day.
  STAMP="$ROOT/sweep/cache/profiles-checked-$(date +%Y-%m)"
  if [ "$rc" = 0 ] && [ ! -f "$STAMP" ]; then
    echo "=== profile check start $(date) ==="
    claude -p "$(cat "$ROOT/sweep/PROFILES_PROMPT.md")" \
      --permission-mode acceptEdits \
      --allowedTools "WebSearch" "WebFetch" "Read" "Edit" "Write" "Glob" "Grep" "Bash(python3:*)"
    prc=$?
    echo "=== profile check end $(date) exit=$prc ==="
    [ "$prc" = 0 ] && touch "$STAMP"
    python3 "$ROOT/web/build.py"   # pick up profile edits made after the news sweep rebuilt the page
  fi
  git fetch -q origin
  if [ "$rc" != 0 ]; then
    echo "publish: sweep exited $rc; not committing"
  # same row-width check as PROMPT.md step 4, so a broken CSV is never pushed
  elif ! python3 -c "import csv,glob,sys
sys.exit(any(len({len(r) for r in csv.reader(open(f))})>1 for f in glob.glob('data/*.csv')))"; then
    echo "publish: a CSV in data/ has rows of the wrong width; not committing"
  elif ! python3 -c "import glob,json
[json.load(open(f)) for f in glob.glob('data/**/*.json', recursive=True)]"; then
    echo "publish: a JSON file in data/ doesn't parse; not committing"
  else
    publish
  fi
} >> "$LOG" 2>&1
