"""Single-flight action/observation port. Offline transport adapter prototype.

Helpers receive observations/proposals, not this port's transport. This is an
in-process contract, not a security boundary. No SDK or network calls here.
"""
from copy import deepcopy
import json
from threading import Lock
from uuid import uuid4


def _copy(value):
    raw = json.dumps(value, allow_nan=False)
    if len(raw.encode('utf-8')) > 1_000_000:
        raise ValueError('port message too large')
    return json.loads(raw)


class GamePort:
    def __init__(self, scope, observation, transport, *, budget=100):
        if not isinstance(scope,str) or not scope or not callable(transport):
            raise ValueError('scope and transport required')
        if type(budget) is not int or budget < 0:
            raise ValueError('nonnegative action budget required')
        self._scope, self._observation = scope, _copy(observation)
        self._transport, self._remaining = transport, budget
        self._version, self._pending, self._fault = 0, None, None
        self._lock = Lock()
        self._events = []

    def snapshot(self):
        return deepcopy({'scope':self._scope,'version':self._version,
                         'observation':self._observation,'remaining':self._remaining,
                         'outstanding':int(self._pending is not None),'fault':self._fault,
                         'events':self._events})

    def exchange(self, action, *, expected_version, available_actions):
        """A central caller supplies legal actions from its current observation.

        Transport receives an envelope and must echo scope/request_id/action.
        On an uncertain call the spent budget is retained and port stays blocked.
        New port/bootstrap reconciliation is an explicit caller responsibility.
        """
        if not self._lock.acquire(blocking=False):
            raise ValueError('one game exchange at a time')
        try:
            if self._pending is not None:
                raise ValueError('unresolved exchange; do not retry an uncertain action')
            if type(expected_version) is not int or expected_version != self._version:
                raise ValueError('stale observation version')
            if type(action) is not int or action not in available_actions:
                raise ValueError('action not currently available')
            if self._remaining <= 0:
                raise ValueError('action budget exhausted')
            request={'scope':self._scope,'request_id':uuid4().hex,'action':action,
                     'before_version':self._version}
            self._pending=request
            self._remaining-=1
            self._events.append({**request,'event':'sent'})
            try:
                response=_copy(self._transport(deepcopy(request)))
                if not isinstance(response,dict) or any(response.get(k)!=request[k]
                    for k in ('scope','request_id','action')) or type(response.get('action')) is not int:
                    raise ValueError('return does not match originating request')
                if 'observation' not in response:
                    raise ValueError('missing returned observation')
            except Exception as exc:
                self._fault=type(exc).__name__
                self._events.append({**request,'event':'uncertain','reason':self._fault})
                return self.snapshot()
            self._observation=response['observation']
            self._version+=1
            self._events.append({**request,'event':'returned','after_version':self._version})
            self._pending=None
            return self.snapshot()
        finally:
            self._lock.release()
