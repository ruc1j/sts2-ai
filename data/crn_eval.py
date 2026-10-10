import json, sys, random, glob, time
sys.path.insert(0, '.'); sys.path.insert(0, 'data')
import official_agent, combat
from model_match_audit import merged_enemy_data
ed = merged_enemy_data()
orig = combat.search

def old_search(c, data, simulations, seed):
    # pre-change search: one shared stream across moves
    rng = random.Random(seed); results = []
    acts = combat.legal_actions(c)
    for action in acts:
        scores = []
        for _ in range(max(1, simulations // len(acts))):
            scores.append(one(c, action, data, rng))
        results.append((action, sum(scores) / len(scores)))
    return sorted(results, key=lambda x: -x[1])

def crn_search(c, data, simulations, seed):
    results = []; acts = combat.legal_actions(c)
    for action in acts:
        scores = [one(c, action, data, random.Random(seed * 1_000_003 + k)) for k in range(max(1, simulations // len(acts)))]
        results.append((action, sum(scores) / len(scores)))
    return sorted(results, key=lambda x: -x[1])

def one(c, action, data, rng):
    # reuse real search body for exactly one simulation by calling it with a 1-action view
    state = combat.step(c, action, data, rng)
    card_value = combat._action_card(c, action)
    self_killed = action != combat.END_TURN and state.player_hp <= 0
    immediate = 0.0 if action == combat.END_TURN or state.player_hp <= 0 else (combat._step_score(c, state, data) + combat._setup_bonus(c, state, card_value, data)) / 100
    for _ in range(60):
        if state.terminal: break
        state = combat.step(state, combat._greedy_action(state, data), data, rng)
    won = state.player_hp > 0 and not any((e.alive or (e.model == combat.TEST_SUBJECT and e.move == combat.RESPAWN_MOVE)) and e.primary for e in state.enemies) and not any(e.escaped and e.primary for e in state.enemies)
    hp = max(0, state.player_hp)
    return (1 if won else -1 if state.player_hp <= 0 else 0) + hp / 100 + immediate - (0.01 if self_killed else 0.0)

cap = {}
def grab(c, data, simulations=5000, seed=0):
    cap['c'] = c; cap['d'] = data; return [(combat.END_TURN, 0.0)]
official_agent.search = grab

files = sorted(glob.glob('data/astra_eval_v[12]_*_agent.jsonl'))
states = []
rnd = random.Random(7)
for p in files:
    for l in open(p):
        r = json.loads(l)
        if r.get('phase') == 'combat' and r.get('decision_source') == 'rollout_success' and r.get('type') in ('card', 'end_turn'):
            states.append(r)
rnd.shuffle(states)
N = int(sys.argv[1]); TRUTH = int(sys.argv[2])
res = {'old': [0, 0.0], 'crn': [0, 0.0]}; used = 0; t0 = time.time()
for r in states:
    if used >= N: break
    cap.clear()
    try: official_agent.rollout_choice(r, r['legal_actions'], ed, 100)
    except Exception: continue
    if 'c' not in cap: continue
    c, d = cap['c'], cap['d']
    if len(combat.legal_actions(c)) < 2: continue
    truth = dict(crn_search(c, d, TRUTH, 999_983))  # independent seed for ground truth
    best = max(truth.values())
    for name, fn in (('old', old_search), ('crn', crn_search)):
        pick = fn(c, d, 100, r['seq'])[0][0]
        res[name][0] += pick == max(truth, key=truth.get)
        res[name][1] += best - truth[pick]
    used += 1
print('states', used, 'secs', round(time.time() - t0))
for k, (hit, regret) in res.items(): print(k, 'top-match', round(hit / used, 3), 'mean regret', round(regret / used, 4))
