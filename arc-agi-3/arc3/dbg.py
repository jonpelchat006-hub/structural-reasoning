"""Run one game in-process and print the mind's level stats."""
import sys, harness, logging, numpy as np
from arc_agi import Arcade, OperationMode
spec, game = sys.argv[1], sys.argv[2]; maxa = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
cls = harness.load_class(spec); cls.MAX_ACTIONS = maxa
arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))
card = arcade.open_scorecard(); env = arcade.make(game, scorecard_id=card)
ag = cls(card_id=card, game_id=game, agent_name="d", ROOT_URL="", record=False, arc_env=env)
levels_seen = {}
orig = ag.mind.act
def act(latest):
    r = orig(latest)
    L = ag.mind.level
    if L is not None: levels_seen[L.idx] = L
    return r
ag.mind.act = act
ag.main()
m = ag.mind
print(game, "mask rows", m.mask_rows, "cols", m.mask_cols, "T", m.T)
for i, L in sorted(levels_seen.items()):
    nd = len(L.nodes); ne = len(L.edges); dead = sum(1 for v in L.edges.values() if v == "DEATH")
    unt = sum(len(n["cands"]) - len(n["tried"]) for n in L.nodes.values())
    ncand = np.mean([len(n["cands"]) for n in L.nodes.values()]) if L.nodes else 0
    print(f" level {i}: nodes {nd} edges {ne} death-edges {dead} untried {unt} mean cands {ncand:.1f} budget {L.budget} death_steps {L.death_steps[:12]}")
mv = getattr(m, "mover", None)
print(" act_stats", dict(m.act_stats), "stats", dict(getattr(m, "stats", {})))
if mv is not None:
    print(" mover d", mv.d, "patch", None if mv.patch is None else mv.patch.shape, "floor", mv.floor.most_common(3))
    print(" pass", mv.passable, "block", mv.blocking, "push", mv.pushable, "dead", mv.deadly, "ok", dict(mv.ok), "bad", dict(mv.bad))
ks = sorted(m.kind.items(), key=lambda kv: -kv[1][0])[:12]; print(" kinds", ks)
sc = arcade.get_scorecard(card); r = sc.environments[0].runs[0]; print(" score", r.score, "levels", r.levels_completed, r.level_actions)
