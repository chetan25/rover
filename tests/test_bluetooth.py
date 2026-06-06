from unittest.mock import MagicMock, patch
from modes.bluetooth import BluetoothController


def _make_event(type_, code, value):
    e = MagicMock()
    e.type = type_
    e.code = code
    e.value = value
    return e


def _make_controller(events):
    motors = MagicMock()
    ctrl = BluetoothController(motors=motors)

    mock_device = MagicMock()
    mock_device.name = "8BitDo Zero 2 gamepad"
    mock_device.read_loop.return_value = iter(events)

    ctrl.running = True
    with patch("modes.bluetooth._find_controller", return_value="/dev/input/event5"), \
         patch("modes.bluetooth.InputDevice", return_value=mock_device):
        ctrl._handle_events()

    return motors


def test_dpad_up_drives_forward():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_ABS, ecodes.ABS_Y, 0)])
    motors.forward.assert_called_once()


def test_dpad_down_drives_backward():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_ABS, ecodes.ABS_Y, 255)])
    motors.backward.assert_called_once()


def test_dpad_left_turns_left():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_ABS, ecodes.ABS_X, 0)])
    motors.turn_left.assert_called_once()


def test_dpad_right_turns_right():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_ABS, ecodes.ABS_X, 255)])
    motors.turn_right.assert_called_once()


def test_dpad_release_stops():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_ABS, ecodes.ABS_Y, 127)])
    motors.stop.assert_called_once()


def test_non_abs_events_ignored():
    from evdev import ecodes
    motors = _make_controller([_make_event(ecodes.EV_KEY, ecodes.ABS_Y, 0)])
    motors.forward.assert_not_called()
    motors.backward.assert_not_called()
