"""One external game port -> two outer relays -> four inner views -> circuit.

Declared layout and message routing only, not optical/BEC physics. The two
relays are a new paired interface, NOT a replacement for OuterEyeCube's six
fixed face eyes. Internal edges are logical tunnels through the cube boundary.
"""
from copy import deepcopy
from uuid import uuid4

from game_port import GamePort


class ExternalEyeCircuit:
    def __init__(self, scope, observation, transport, *, budget=100):
        self._port = GamePort(scope, observation, transport, budget=budget)
        self._session = uuid4().hex
        self._positions = {'port': (0, 0, 4), 'outer:left': (-.75, 0, 2),
                           'outer:right': (.75, 0, 2), 'inner:0': (-.5, -.5, 1),
                           'inner:1': (-.5, .5, 1), 'inner:2': (.5, -.5, 1),
                           'inner:3': (.5, .5, 1), 'circuit': (0, 0, 0)}
        self._routes = {f'view:{i}': ('port', 'outer:left' if i < 2 else 'outer:right',
                                    f'inner:{i}', 'circuit') for i in range(4)}

    def layout(self):
        return deepcopy(dict(outer_bounds=[[-2, -2, -2], [2, 2, 2]],
                             inner_bounds=[[-1, -1, -1], [1, 1, 1]],
                             positions=self._positions, routes=self._routes,
                             visibility='port-to-front-relays unobstructed in this declared empty layout; internal edges are tunnels'))

    def snapshot(self):
        return self._port.snapshot()

    def views(self):
        state = self._port.snapshot()
        if state['outstanding']:
            raise ValueError('unresolved game exchange; no new views until reconciliation')
        observation_id = f"{self._session}:{state['version']}"
        return [dict(route=name, path=list(path), scope=state['scope'],
                     version=state['version'], observation_id=observation_id,
                     observation=deepcopy(state['observation']),
                     direction=[-v for v in self._positions[path[-2]]])
                for name, path in self._routes.items()]

    def act(self, proposals, *, available_actions):
        """Merge one response per view; agreement is NOT four votes of evidence.

        Each response echoes route/scope/version/observation_id and supplies an
        integer action or None (abstain). A conflict cannot dispatch an action.
        The trusted central adapter, not these proposals, supplies legal actions.
        """
        if not isinstance(proposals, (list, tuple)) or len(proposals) != 4:
            raise ValueError('exactly one proposal/abstention per inner view required')
        expected = {v['route']: v for v in self.views()}
        seen, actions = set(), set()
        for proposal in proposals:
            if not isinstance(proposal, dict) or proposal.get('route') not in expected:
                raise ValueError('unknown route')
            route = proposal['route']
            if route in seen:
                raise ValueError('duplicate return route')
            seen.add(route)
            if type(proposal.get('version')) is not int or any(
                    proposal.get(k) != expected[route][k] for k in ('scope', 'version', 'observation_id')):
                raise ValueError('stale or mismatched view return')
            if 'action' not in proposal or (proposal['action'] is not None and type(proposal['action']) is not int):
                raise ValueError('integer action or explicit abstention required')
            if proposal['action'] is not None:
                actions.add(proposal['action'])
        if len(actions) != 1:
            return dict(status='conflicting_proposals' if actions else 'all_abstained',
                        dispatched=False, state=self._port.snapshot())
        state = self._port.exchange(actions.pop(), expected_version=next(iter(expected.values()))['version'],
                                    available_actions=available_actions)
        return dict(status='unresolved' if state['outstanding'] else 'returned',
                    dispatched=True, state=state)
