"""Install Mika's evidence layer into the Duck harness (Franzen's Milestone-2 patch applied).

Writes mika_layer_core.py next to tool_agent.py and makes two anchored edits to tool_agent.py:
  1. a method ToolAgent._mika_layer_lines(history_entries) that feeds the layer the presses since the last
     turn and returns its notes;
  2. one call in _build_user_prompt, right after the death-ledger lines (next to the valid-actions line):
         if ARC3_MIKA_LAYER is on: lines.extend(self._mika_layer_lines(history_entries))
Every anchor must match exactly once, otherwise nothing is changed and the harness runs as the original.
With ARC3_MIKA_LAYER off the prompt is unchanged.

    python install_mika_layer.py <path to ARC3-Inference/inference/agent> <path to mika_layer_core.py>"""
import sys
from pathlib import Path

METHOD = '''
    def _mika_layer_lines(self, history_entries):
        """Mika's evidence layer: facts computed from the frames since the last turn (never by the model)."""
        try:
            import os as _os
            from inference.agent.mika_layer_core import MikaLayer
            sess = getattr(self, "_session_runtime_dir", None)
            if getattr(self, "_mika_layer", None) is None or getattr(self, "_mika_sess", None) != sess:
                self._mika_layer = MikaLayer(max_lines=int(_os.environ.get("ARC3_MIKA_MAX_LINES", "3")))
                self._mika_seen = 0
                self._mika_sess = sess
            layer = self._mika_layer
            entries = list(history_entries or [])
            if self._mika_seen > len(entries):
                self._mika_seen = 0
            chain = list(getattr(self, "_last_animation_chain", None) or [])
            for i in range(max(1, self._mika_seen), len(entries)):
                prev, cur = entries[i - 1], entries[i]
                if prev.frame is None or cur.frame is None or not prev.frame.grid or not cur.frame.grid:
                    continue
                act = str(cur.action or "")
                res = dict(cur.result or {})
                if act.upper().startswith("RESET"):
                    layer.reset_life(cur.frame.grid)
                    continue
                done = bool(res.get("level_completed"))
                frames, known = [cur.frame.grid], True
                if done:
                    if i == len(entries) - 1 and len(chain) >= 3:
                        frames = [chain[1], cur.frame.grid]
                    else:
                        known = False
                layer.observe(prev.frame.grid, frames, act, level=max(0, int(prev.frame.level or 1) - 1),
                              level_done=done, game_over=bool(res.get("game_over")), effect_known=known)
            self._mika_seen = len(entries)
            out = layer.notes()
            log = _os.environ.get("ARC3_MIKA_LOG", "")
            if log and out:
                import json as _json
                with open(log, "a") as fh:
                    fh.write(_json.dumps({"session": str(sess), "presses": len(entries) - 1, "notes": out}) + "\\n")
            return out
        except Exception:
            return []

'''
ANCHOR_METHOD = "    def _build_user_prompt(\n        self,\n        action_num: int,\n"
ANCHOR_CALL = "        lines.extend(\n            [\n                \"Only tool: `python`. It receives"
CALL = ("        if _get_env_bool(\"ARC3_MIKA_LAYER\", False):\n"
        "            lines.extend(self._mika_layer_lines(history_entries))\n")


def install(agent_dir, core_path):
    agent_dir = Path(agent_dir)
    ta = agent_dir / "tool_agent.py"
    src = ta.read_text()
    if "_mika_layer_lines" in src:
        print("mika layer: already installed"); return True
    if src.count(ANCHOR_METHOD) != 1 or src.count(ANCHOR_CALL) != 1:
        print(f"mika layer: anchors not unique ({src.count(ANCHOR_METHOD)}, {src.count(ANCHOR_CALL)}); NOT installed")
        return False
    new = src.replace(ANCHOR_METHOD, METHOD.lstrip("\n") + ANCHOR_METHOD, 1)
    new = new.replace(ANCHOR_CALL, CALL + ANCHOR_CALL, 1)
    try:
        compile(new, str(ta), "exec")
    except Exception as exc:
        print(f"mika layer: patched file does not compile ({exc}); NOT installed")
        return False
    (agent_dir / "mika_layer_core.py").write_text(Path(core_path).read_text())
    ta.write_text(new)
    print("mika layer: installed")
    return True


def install_safe(agent_dir, core_path):
    try:
        return install(agent_dir, core_path)
    except Exception as exc:
        print(f"mika layer: install failed ({exc}); NOT installed")
        return False


if __name__ == "__main__":
    ok = install(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
