"""Run a local red-to-green translation and an unresolved-meaning example."""
import json
from pin_channels import Message, PinCodebook, ChannelRouter, ControlChannels


def demo():
    scope = 'demo-game/attempt-1'
    controls = PinCodebook('controls', scope, 1, {('action.3', 'requested'): (650, 0)})
    relay = PinCodebook('relay', scope, 1, {('frame', 'observed'): (480, 45)})
    pin = PinCodebook('void-pin', scope, 1, {('action.3', 'requested'): (530, 90)})
    message = Message.create('command-1', scope, 'action.3', 'requested', {'action': 3, 'data': {}})
    router = ChannelRouter([controls, relay, pin], [('controls', 'relay'), ('relay', 'void-pin')])
    delivered = router.route(controls.encode(message), 'void-pin')
    unresolved = router.route(controls.encode(message), 'relay')
    bus = ControlChannels(scope)
    request = bus.request('command-1', 3, {})
    receipt = bus.receipt(request, 'frame-1')
    unchanged = bus.observed('outcome-1', 3, 'frame-0', 'frame-1', False)
    return dict(note='Synthetic example, not a game run or learned control meaning.',
                translated=delivered, unresolved=unresolved,
                lifecycle=dict(request=request['request'], receipt=receipt['receipt'], observed=unchanged['message']))


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
