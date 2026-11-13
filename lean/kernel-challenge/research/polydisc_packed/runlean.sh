#!/bin/bash
# run lean on polydev/Submission.lean, report exit code, peak RSS (KB) and seconds
export PATH=$HOME/.elan/bin:$PATH
cd /home/claude/polydev
start=$(date +%s)
lake env lean Submission.lean > /tmp/runlean.out 2>&1 &
P=$!
M=0
while kill -0 $P 2>/dev/null; do
  for q in $(pgrep -f "bin/lean Submission.lean"); do
    R=$(ps -o rss= -p $q 2>/dev/null | tr -d ' ')
    [ -n "$R" ] && [ "$R" -gt "$M" ] && M=$R
  done
  sleep 0.3
done
wait $P; E=$?
tail -c 1500 /tmp/runlean.out
echo "EXIT $E MAXRSS_KB $M SECS $(( $(date +%s) - start ))"
