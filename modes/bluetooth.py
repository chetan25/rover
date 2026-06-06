import threading
from evdev import InputDevice, ecodes, list_devices
from config import DRIVE_SPEED, TURN_SPEED


def _find_controller():
    for path in list_devices():
        dev = InputDevice(path)
        if any(k in dev.name for k in ("8BitDo", "Zero", "Gamepad", "gamepad")):
            return path
    raise RuntimeError("No Bluetooth controller found — is it paired and connected?")


class BluetoothController:
    def __init__(self, motors):
        self.motors = motors
        self.running = False

    def _handle_events(self):
        device = InputDevice(_find_controller())
        print(f"[BT] Connected to {device.name}")
        for event in device.read_loop():
            if not self.running:
                break
            if event.type != ecodes.EV_ABS:
                continue
            # D-pad vertical: -1 = up (forward), 1 = down (backward), 0 = released
            if event.code == ecodes.ABS_HAT0Y:
                if event.value == -1:
                    self.motors.forward(DRIVE_SPEED)
                elif event.value == 1:
                    self.motors.backward(DRIVE_SPEED)
                else:
                    self.motors.stop()
            # D-pad horizontal: -1 = left, 1 = right, 0 = released
            elif event.code == ecodes.ABS_HAT0X:
                if event.value == -1:
                    self.motors.turn_left(TURN_SPEED)
                elif event.value == 1:
                    self.motors.turn_right(TURN_SPEED)
                else:
                    self.motors.stop()

    def start(self):
        self.running = True
        t = threading.Thread(target=self._handle_events, daemon=True)
        t.start()

    def stop(self):
        self.running = False
