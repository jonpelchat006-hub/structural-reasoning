"""Pin-local, reversible spectral symbols. This is a codec, NOT encryption.

Meaning and evidence identity are independent of wavelength/orientation. SHA256
names the complete canonical content; its colour projection is never an ID.
Unknown meanings stay questions. Translation never grants execution authority.
"""
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType


PHASES = ('requested', 'executed', 'observed', 'hypothesis')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 1024:
        raise ValueError('bounded nonempty identity required')
    return value


@dataclass(frozen=True)
class Message:
    # Store JSON text, not a mutable payload hidden inside a frozen dataclass.
    content: str

    def __post_init__(self):
        if not isinstance(self.content, str) or len(self.content) > 1_000_000:
            raise ValueError('bounded canonical message required')
        value = json.loads(self.content)
        if set(value) != {'id', 'scope', 'semantic', 'phase', 'payload', 'evidence'}:
            raise ValueError('message schema mismatch')
        for key in ('id', 'scope', 'semantic'):
            name(value[key])
        if value['phase'] not in PHASES or not isinstance(value['payload'], dict):
            raise ValueError('explicit message phase and payload required')
        if not isinstance(value['evidence'], list) or len(value['evidence']) > 64:
            raise ValueError('bounded evidence identities required')
        for item in value['evidence']:
            name(item)
        if canonical(value) != self.content:
            raise ValueError('noncanonical message')

    @classmethod
    def create(cls, identifier, scope, semantic, phase, payload, evidence=()):
        return cls(canonical(dict(id=identifier, scope=scope, semantic=semantic,
                                  phase=phase, payload=payload, evidence=list(evidence))))

    @property
    def value(self):
        return json.loads(self.content)

    @property
    def identity(self):
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Signal:
    pin: str
    scope: str
    version: int
    codebook: str
    wavelength: int
    orientation: int
    message: Message
    checksum: str

    def snapshot(self):
        return dict(pin=self.pin, scope=self.scope, version=self.version, codebook=self.codebook,
                    wavelength=self.wavelength, orientation=self.orientation,
                    message=self.message.value, checksum=self.checksum)


class PinCodebook:
    def __init__(self, pin, scope, version, symbols):
        self.pin, self.scope = name(pin), name(scope)
        if type(version) is not int or version < 1:
            raise ValueError('positive codebook version required')
        if not 1 <= len(symbols) <= 512:
            raise ValueError('codebook needs 1..512 symbols')
        clean = {}
        for (semantic, phase), (wavelength, orientation) in symbols.items():
            name(semantic)
            if phase not in PHASES:
                raise ValueError('invalid phase')
            if type(wavelength) is not int or not 380 <= wavelength <= 780:
                raise ValueError('symbol outside the configured visible window')
            if type(orientation) is not int or not 0 <= orientation < 360:
                raise ValueError('integer orientation 0..359 required')
            clean[(semantic, phase)] = (wavelength, orientation)
        if len(set(clean.values())) != len(clean):
            raise ValueError('ambiguous wavelength/orientation collision')
        self.version = version
        self.symbols = MappingProxyType(clean)
        self.reverse = MappingProxyType({value: key for key, value in clean.items()})
        self.fingerprint = digest(self.manifest())

    @classmethod
    def assigned(cls, pin, scope, meanings, version=1):
        """Deterministic collision-free local assignments, not learned semantics."""
        meanings = sorted(set(meanings))
        if not 1 <= len(meanings) <= 512:
            raise ValueError('codebook needs 1..512 meanings')
        symbols, used = {}, set()
        for key in meanings:
            slot = int(digest([pin, version, key]), 16) % (401 * 360)
            while slot in used:
                slot = (slot + 1) % (401 * 360)
            used.add(slot)
            symbols[key] = (380 + slot // 360, slot % 360)
        return cls(pin, scope, version, symbols)

    def manifest(self):
        return dict(pin=self.pin, scope=self.scope, version=self.version,
                    symbols=[[s, p, w, o] for (s, p), (w, o) in sorted(self.symbols.items())])

    def supports(self, message):
        value = message.value
        return value['scope'] == self.scope and (value['semantic'], value['phase']) in self.symbols

    def encode(self, message):
        if not self.supports(message):
            raise ValueError('meaning not visible in this pin/scope')
        value = message.value
        wavelength, orientation = self.symbols[value['semantic'], value['phase']]
        metadata = [self.pin, self.scope, self.version, self.fingerprint, wavelength, orientation, message.identity]
        return Signal(*metadata[:6], message, digest(metadata))

    def decode(self, signal):
        if (signal.pin, signal.scope, signal.version, signal.codebook) != (self.pin, self.scope, self.version, self.fingerprint):
            raise ValueError('wrong pin, scope or codebook revision')
        expected = self.encode(signal.message)
        if signal != expected:
            raise ValueError('signal symbol/content integrity mismatch')
        meaning = self.reverse.get((signal.wavelength, signal.orientation))
        value = signal.message.value
        if meaning != (value['semantic'], value['phase']):
            raise ValueError('symbol meaning mismatch')
        return signal.message


class ChannelRouter:
    """Bounded explicit connections; opaque relays can forward but not interpret."""
    def __init__(self, books, edges):
        books = list(books)
        self.books = {b.pin: b for b in books}
        if not 1 <= len(books) <= 64 or len(self.books) != len(books):
            raise ValueError('1..64 distinct pins required')
        self.edges = {pin: [] for pin in self.books}
        for source, target in edges:
            if source not in self.books or target not in self.books:
                raise ValueError('connection references unknown pin')
            if target not in self.edges[source]:
                self.edges[source].append(target)

    def route(self, signal, target, max_hops=8):
        if type(max_hops) is not int or not 0 <= max_hops <= 64:
            raise ValueError('hop budget 0..64 required')
        if signal.pin not in self.books or target not in self.books:
            raise ValueError('unknown endpoint')
        message = self.books[signal.pin].decode(signal)
        queue, visited = deque([(signal.pin, [signal.pin])]), {signal.pin}
        selected = None
        while queue:
            pin, path = queue.popleft()
            if pin == target and self.books[pin].supports(message):
                selected = path
                break
            if len(path) - 1 >= max_hops:
                continue
            for neighbor in self.edges[pin]:
                if neighbor not in visited and self.books[neighbor].scope == message.value['scope']:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        if selected is None:
            return dict(status='question', question=f'Which connected pin can translate {message.value["semantic"]} ({message.value["phase"]}) into {target}?',
                        message=message.value, visited=sorted(visited), execution_authorized=False)
        hops = []
        for pin in selected:
            book = self.books[pin]
            visible = book.supports(message)
            local = book.encode(message) if visible else None
            if local is not None and book.decode(local) != message:
                raise ValueError('translation failed round trip')
            hops.append(dict(pin=pin, visible=visible, signal=None if local is None else local.snapshot()))
        return dict(status='delivered', message_id=message.identity, hops=hops,
                    message=message.value, execution_authorized=False)


class ControlChannels:
    """Typed control request/receipt and measured outcome, with pin-local codecs.

    Calling receipt means the caller received an SDK response, not game success.
    No method here calls a game, discovers an action meaning, or authorizes one.
    """
    def __init__(self, scope):
        self.scope = name(scope)
        meanings = [(f'action.{a}', phase) for a in range(8) for phase in PHASES[:3]]
        self.books = {pin: PinCodebook.assigned(pin, scope, meanings)
                      for pin in ('planner', 'controls')}
        for action in range(8):
            pin = self.outcome_pin(action)
            self.books[pin] = PinCodebook.assigned(pin, scope,
                [(f'action.{action}', phase) for phase in PHASES[:3]])
        self.router = ChannelRouter(self.books.values(), [('planner', 'controls')] +
                                    [('controls', self.outcome_pin(a)) for a in range(8)])

    @staticmethod
    def outcome_pin(action):
        return f'action-{action}-frame-change'

    def request(self, identifier, action, data):
        if type(action) is not int or not 0 <= action <= 7 or not isinstance(data, dict):
            raise ValueError('explicit action 0..7 and data required')
        message = Message.create(identifier, self.scope, f'action.{action}', 'requested', dict(action=action, data=data))
        signal = self.books['planner'].encode(message)
        route = self.router.route(signal, 'controls')
        if route['status'] != 'delivered':
            raise ValueError('control request did not arrive')
        return dict(request=message.value, request_id=message.identity, request_route=route)

    def receipt(self, request, observation_id):
        original = Message(canonical(request['request']))
        if original.identity != request['request_id'] or original.value['phase'] != 'requested' or original.value['scope'] != self.scope:
            raise ValueError('invalid request receipt binding')
        value = original.value
        action = value['payload'].get('action')
        if type(action) is not int or not 0 <= action <= 7 or value['semantic'] != f'action.{action}':
            raise ValueError('request action and semantic disagree')
        message = Message.create(value['id'] + ':receipt', self.scope, value['semantic'], 'executed',
                                 dict(request_id=original.identity, returned_observation=name(observation_id)), [observation_id])
        signal = self.books['controls'].encode(message)
        return dict(**deepcopy(request), receipt=message.value,
                    receipt_route=self.router.route(signal, self.outcome_pin(action)))

    def observed(self, identifier, action, before_id, after_id, frame_changed):
        if type(frame_changed) is not bool or type(action) is not int or not 0 <= action <= 7:
            raise ValueError('measured boolean outcome/action required')
        message = Message.create(identifier, self.scope, f'action.{action}', 'observed',
                                 dict(frame_changed=frame_changed), [before_id, after_id])
        return self.books[self.outcome_pin(action)].encode(message).snapshot()

    def manifest(self):
        return {pin: book.manifest() for pin, book in self.books.items()}
