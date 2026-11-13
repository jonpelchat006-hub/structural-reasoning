#!/bin/bash
# End-to-end check of the Kaggle rerun flow: a local competition-mode gateway + the official runner + my_agent.py
set -e
cd /home/claude/arc3
GAMES=${1:-}
rm -rf /tmp/e2e && mkdir -p /tmp/e2e && cp -r data/ARC-AGI-3-Agents /tmp/e2e/ && cp kaggle/mika-arc3/my_agent.py /tmp/e2e/ARC-AGI-3-Agents/agents/templates/my_agent.py
mkdir -p /tmp/e2e/env && if [ -n "$GAMES" ]; then for g in $GAMES; do cp -r data/environment_files/$g /tmp/e2e/env/; done; else cp -r data/environment_files/* /tmp/e2e/env/; fi
cat > /tmp/e2e/ARC-AGI-3-Agents/agents/__init__.py <<'P'
from typing import Type, cast
from dotenv import load_dotenv
from .agent import Agent, Playback
from .swarm import Swarm
from .templates.random_agent import Random
from .templates.my_agent import MikaAgent

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    "random": Random,
    "mika": MikaAgent,
}
P
cat > /tmp/e2e/ARC-AGI-3-Agents/.env <<'P'
SCHEME=http
HOST=localhost
PORT=8011
ARC_API_KEY=test-key-123
ARC_BASE_URL=http://localhost:8011/
OPERATION_MODE=online
ENVIRONMENTS_DIR=
RECORDINGS_DIR=/tmp/e2e/server_recording
P
cat > /tmp/e2e/gateway.py <<'P'
import logging
from arc_agi import Arcade, OperationMode
def on_close(sc):
    import json
    open("/tmp/e2e/final_scorecard.json", "w").write(sc.model_dump_json(indent=1))
a = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir="/tmp/e2e/env", logger=logging.getLogger("gw"))
a.listen_and_serve(host="127.0.0.1", port=8011, competition_mode=True, on_scorecard_close=on_close)
P
cd /tmp/e2e && (/home/claude/arc3/venv/bin/python gateway.py > gateway.log 2>&1 & echo $! > /tmp/e2e/gw.pid) && cd /home/claude/arc3
sleep 4
curl -s --retry 10 --retry-connrefused http://127.0.0.1:8011/api/games | head -c 300; echo
cd /tmp/e2e/ARC-AGI-3-Agents && MPLBACKEND=agg timeout 1500 /home/claude/arc3/venv/bin/python main.py --agent mika > /tmp/e2e/run.log 2>&1 || true
tail -n 5 /tmp/e2e/run.log
kill $(cat /tmp/e2e/gw.pid) 2>/dev/null || true
