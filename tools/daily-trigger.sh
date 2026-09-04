#!/usr/bin/env bash
# Trigger the daily build from a machine we control, because GitHub's own
# scheduler will not.
#
# The repo asked for 09:00, then 08:23, then 08:23 and 15:47 with a guard, and
# GitHub has never once delivered a scheduled trigger to it. The sibling
# clipping repo's cron does fire, three and a half hours late, so this is not
# the account, the org, the default branch or registration latency -- schedule
# delivery is simply best-effort and this repo keeps losing.
#
# So the cron slots stay as a free extra chance and this is the one that is
# actually relied on. It is a workflow_dispatch, which GitHub delivers
# immediately and always.
#
# It refuses to start a second build on a day that already has one. That check
# lives HERE as well as in the workflow, because the workflow's guard only
# applies to schedule events -- a dispatch always runs, by design, so that a
# person pressing the button is never second-guessed. This script is not a
# person pressing the button.
set -uo pipefail

REPO="${SCROLLREEL_REPO:-codeaz-org/scrollreel}"
WORKFLOW="${SCROLLREEL_WORKFLOW:-build.yml}"
LOG="${SCROLLREEL_LOG:-$HOME/.local/state/scrollreel-daily.log}"
mkdir -p "$(dirname "$LOG")"

say() { printf '%s  %s\n' "$(date -u +%FT%TZ)" "$*" >>"$LOG"; }

command -v gh >/dev/null || { say "gh not on PATH"; exit 1; }
gh auth status >/dev/null 2>&1 || { say "gh not authenticated"; exit 1; }

TODAY="$(date -u +%F)"

# Anything from today counts, including a run still going: two concurrent
# builds would race each other committing state.json.
EXISTING="$(gh api "/repos/$REPO/actions/runs?per_page=30" \
  --jq "[.workflow_runs[]
         | select(.created_at[0:10] == \"$TODAY\")
         | select(.conclusion == \"success\" or .status == \"in_progress\" or .status == \"queued\")]
        | length" 2>/dev/null)"

if [ -z "$EXISTING" ]; then
  say "could not read run history for $REPO; not dispatching"
  exit 1
fi

if [ "$EXISTING" -gt 0 ]; then
  say "skip: $EXISTING run(s) already today ($TODAY)"
  exit 0
fi

if gh workflow run "$WORKFLOW" --repo "$REPO" >>"$LOG" 2>&1; then
  say "dispatched $WORKFLOW on $REPO"
else
  say "dispatch FAILED"
  exit 1
fi
