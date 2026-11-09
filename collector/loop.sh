#!/bin/bash
# One long job: collect every 5 minutes for LOOP_MIN minutes, then start the next job. GitHub drops most runs of a
# */5 schedule (8 Nov: one scheduled run in four hours), so the 5-minute rhythm is kept inside the job.
# Log: per source only platform, HTTP status, new posts, requests, seconds (collect_run.py); never post text.
set -u
LOOP_MIN=${LOOP_MIN:-340}
END=$(( $(date +%s) + LOOP_MIN * 60 ))
mkdir -p run/out
gh release download collector-state -p state.json -D run --clobber || echo "no saved state: starting from seed_state.json"
while [ "$(date +%s)" -lt "$END" ]; do
  T0=$(date +%s)
  rm -f run/out/*
  echo "=== cycle $(date -u +%FT%TZ)"
  if python collector/collect_run.py --state run/state.json --out run/out --budget 240; then
    D=$(date +%F)
    ok=1
    if ls run/out/chunk_*.jsonl.gz >/dev/null 2>&1; then
      if ! gh release list --limit 300 --json tagName -q '.[].tagName' | grep -qx "raw-$D"; then
        gh release create "raw-$D" --draft --title "Raw posts $D" --notes "Collection chunks of $D (New York date of the run); merged after midnight into raw_$D.jsonl.gz. Draft: visible only to the owner."
      fi
      ok=0
      for i in 1 2 3 4 5; do gh release upload "raw-$D" run/out/chunk_*.jsonl.gz --clobber && { ok=1; break; }; sleep 5; done
    fi
    if [ "$ok" -eq 1 ]; then
      cp run/out/state_new.json run/state.json
      cp run/state.json run/out/state.json
      gh release view collector-state >/dev/null 2>&1 || gh release create collector-state --prerelease --title "Collector state" --notes "Last id / time per source and source health (no post text). Replaced every run."
      gh release upload collector-state run/out/state.json run/out/health.json --clobber || echo "state upload failed; kept locally"
      if gh cache list --key night- --limit 1 --json key -q '.[].key' 2>/dev/null | grep -q night-; then
        gh workflow run build.yml --ref main >/dev/null 2>&1 && echo "page update started" || echo "page update not started"
      else
        echo "no nightly state yet: page update waits for the first nightly run"
      fi
    else
      echo "chunk upload failed: position not advanced, the same posts are fetched again next cycle"
    fi
  else
    echo "collect_run failed; retry next cycle"
  fi
  # GitHub skips most scheduled runs (9 Nov: nightly 08:00 UTC and raw-daily 08:40 UTC never started), so the loop
  # starts them: after 03:00 New York, nightly if today's state (cache night-<today>) is missing, raw-daily if
  # yesterday's merged file is missing; each at most once every 150 minutes (a failed run is retried after that).
  if [ "$(date +%H)" -ge 3 ]; then
    TODAY=$(date +%F); YDAY=$(date -d yesterday +%F); NOW=$(date +%s)
    recent() { local c; c=$(gh run list -w "$1" --limit 1 --json createdAt -q '.[0].createdAt' 2>/dev/null); [ -n "$c" ] && [ $(( NOW - $(date -d "$c" +%s) )) -lt 9000 ]; }
    if ! gh cache list --key "night-$TODAY" --limit 1 --json key -q '.[].key' 2>/dev/null | grep -q . && ! recent nightly; then
      gh workflow run nightly.yml --ref main >/dev/null 2>&1 && echo "nightly started"
    fi
    A=$(gh api "repos/{owner}/{repo}/releases?per_page=100" -q ".[]|select(.tag_name==\"raw-$YDAY\")|.assets[].name" 2>/dev/null)
    if [ -n "$A" ] && ! echo "$A" | grep -qx "raw_$YDAY.jsonl.gz" && ! recent raw-daily; then
      gh workflow run raw_daily.yml --ref main >/dev/null 2>&1 && echo "raw-daily started"
    fi
  fi
  W=$(( 300 - ($(date +%s) - T0) )); [ "$W" -gt 0 ] && sleep "$W"
done
gh workflow run collect.yml --ref main && echo "next job started"
