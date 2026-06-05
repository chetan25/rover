# AI Rover Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 4WD Raspberry Pi 5 rover that autonomously avoids obstacles, streams FPV video, and narrates what it sees via Claude Vision displayed on an LCD.

**Architecture:** All components run as Python threads from `main.py` — autonomous drive loop, MJPEG HTTP stream, Claude Vision narration, and a manual web UI all share a single Picamera2 instance via a threading lock. Hardware abstraction classes (MotorDriver, Ultrasonic, LCD) wrap GPIO directly and are mockable via `unittest.mock` for Windows development.

**Tech Stack:** Python 3.11+, RPi.GPIO, picamera2, RPLCD, anthropic SDK, Python's built-in `http.server` for FPV stream.

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | All constants: GPIO pins, speeds, API key, camera settings |
| `motors/driver.py` | L298N PWM motor control — forward/back/turn/stop |
| `motors/__init__.py` | Package marker |
| `sensors/ultrasonic.py` | HC-SR04 distance measurement with timeout safety |
| `sensors/__init__.py` | Package marker |
| `display/lcd.py` | LCD 1602 I2C 2-line write wrapper |
| `display/__init__.py` | Package marker |
| `modes/autonomous.py` | Obstacle-avoid loop — reads sensor, commands motors |
| `modes/manual.py` | WebSocket WASD handler — receives commands, drives motors |
| `modes/__init__.py` | Package marker |
| `camera/vision.py` | Claude Vision — snapshot → describe → LCD write |
| `camera/stream.py` | MJPEG HTTP server — shares camera with vision via lock |
| `camera/__init__.py` | Package marker |
| `web/index.html` | Phone browser UI — FPV stream + WASD keyboard control |
| `main.py` | Entry point — wires all components, starts threads |
| `tests/conftest.py` | Mocks for RPi.GPIO, picamera2, RPLCD (Pi-only libs) |
| `tests/test_motors.py` | MotorDriver unit tests |
| `tests/test_ultrasonic.py` | Ultrasonic unit tests |
| `tests/test_lcd.py` | LCD unit tests |
| `tests/test_autonomous.py` | AutonomousMode unit tests |
| `tests/test_vision.py` | ClaudeVision unit tests |
| `tests/test_stream.py` | StreamServer unit tests |
| `requirements.txt` | Pinned dependencies |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `motors/__init__.py`, `sensors/__init__.py`, `display/__init__.py`, `modes/__init__.py`, `camera/__init__.py`

- [ ] **Step 1: Create package `__init__.py` files**

Run in PowerShell from `D:\Programming\rover-pi`:
```powershell
New-Item -ItemType Directory -Force motors, sensors, display, modes, camera, tests, web
"" | Out-File motors/__init__.py -Encoding utf8
"" | Out-File sensors/__init__.py -Encoding utf8
"" | Out-File display/__init__.py -Encoding utf8
"" | Out-File modes/__init__.py -Encoding utf8
"" | Out-File camera/__init__.py -Encoding utf8
"" | Out-File tests/__init__.py -Encoding utf8
```

- [ ] **Step 2: Create `requirements.txt`**

```
RPi.GPIO==0.7.1
picamera2==0.3.21
RPLCD==1.3.0
anthropic==0.40.0
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 3: Create `tests/conftest.py` — mock all Pi-only modules**

This file runs before every test and injects fake modules for hardware that doesn't exist on Windows/CI.

```python
import sys
import types
from unittest.mock import MagicMock, patch

# --- RPi.GPIO mock ---
gpio_mock = types.ModuleType("RPi")
gpio_mock.GPIO = MagicMock()
gpio_mock.GPIO.BCM = 11
gpio_mock.GPIO.OUT = 0
gpio_mock.GPIO.IN = 1
gpio_mock.GPIO.HIGH = 1
gpio_mock.GPIO.LOW = 0
gpio_mock.GPIO.input = MagicMock(return_value=0)
gpio_mock.GPIO.output = MagicMock()
gpio_mock.GPIO.setup = MagicMock()
gpio_mock.GPIO.setmode = MagicMock()
gpio_mock.GPIO.setwarnings = MagicMock()
gpio_mock.GPIO.cleanup = MagicMock()

pwm_instance = MagicMock()
pwm_instance.start = MagicMock()
pwm_instance.ChangeDutyCycle = MagicMock()
pwm_instance.stop = MagicMock()
gpio_mock.GPIO.PWM = MagicMock(return_value=pwm_instance)

sys.modules["RPi"] = gpio_mock
sys.modules["RPi.GPIO"] = gpio_mock.GPIO

# --- picamera2 mock ---
picamera2_mock = types.ModuleType("picamera2")
mock_camera = MagicMock()
mock_camera.configure = MagicMock()
mock_camera.start = MagicMock()
mock_camera.stop = MagicMock()
mock_camera.capture_file = MagicMock()
mock_camera.create_still_configuration = MagicMock(return_value={})
mock_camera.create_video_configuration = MagicMock(return_value={})
picamera2_mock.Picamera2 = MagicMock(return_value=mock_camera)
sys.modules["picamera2"] = picamera2_mock

# --- RPLCD mock ---
rplcd_mock = types.ModuleType("RPLCD")
rplcd_i2c_mock = types.ModuleType("RPLCD.i2c")
mock_lcd_instance = MagicMock()
mock_lcd_instance.clear = MagicMock()
mock_lcd_instance.write_string = MagicMock()
mock_lcd_instance.crlf = MagicMock()
rplcd_i2c_mock.CharLCD = MagicMock(return_value=mock_lcd_instance)
rplcd_mock.i2c = rplcd_i2c_mock
sys.modules["RPLCD"] = rplcd_mock
sys.modules["RPLCD.i2c"] = rplcd_i2c_mock
```

- [ ] **Step 4: Verify pytest discovers the project**

```bash
cd D:\Programming\rover-pi
python -m pytest tests/ --collect-only
```
Expected: `no tests ran` with 0 errors (no import errors).

---

## Task 2: config.py

**Files:**
- Create: `config.py`

No test — pure constants, verified by import in later tasks.

- [ ] **Step 1: Create `config.py`**

```python
# GPIO pins — motors
PIN_IN1 = 17
PIN_IN2 = 18
PIN_IN3 = 27
PIN_IN4 = 22
PIN_ENA = 12   # PWM — left motors speed
PIN_ENB = 13   # PWM — right motors speed

# GPIO pins — HC-SR04
PIN_TRIG = 23
PIN_ECHO = 24

# Rover behaviour
OBSTACLE_DISTANCE_CM = 25
DRIVE_SPEED = 70               # 0-100 PWM duty cycle
TURN_SPEED = 60
TURN_DURATION = 0.5            # seconds to turn when avoiding

# Claude Vision
VISION_INTERVAL_SEC = 5
CLAUDE_API_KEY = "sk-ant-..."  # replace before deploying to Pi
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Camera stream
STREAM_PORT = 8080
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
STREAM_FPS = 15

# LCD I2C address (run: i2cdetect -y 1 to confirm — usually 0x27 or 0x3F)
LCD_ADDRESS = 0x27
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "import config; print(config.PIN_IN1, config.CLAUDE_MODEL)"
```
Expected: `17 claude-haiku-4-5-20251001`

- [ ] **Step 3: Commit**

```bash
git add config.py requirements.txt motors/__init__.py sensors/__init__.py display/__init__.py modes/__init__.py camera/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project scaffold and config"
```

---

## Task 3: Motor Driver

**Files:**
- Create: `motors/driver.py`
- Create: `tests/test_motors.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_motors.py
import RPi.GPIO as GPIO
from motors.driver import MotorDriver

def make_driver():
    return MotorDriver(in1=17, in2=18, in3=27, in4=22, ena=12, enb=13)

def test_forward_sets_both_sides_forward():
    d = make_driver()
    d.forward(speed=70)
    # IN1=HIGH (fwd), IN2=LOW; IN3=HIGH (fwd), IN4=LOW
    calls = {call.args for call in GPIO.output.call_args_list}
    assert (17, True) in calls
    assert (18, False) in calls
    assert (27, True) in calls
    assert (22, False) in calls

def test_backward_sets_both_sides_backward():
    d = make_driver()
    d.backward(speed=70)
    calls = {call.args for call in GPIO.output.call_args_list}
    assert (17, False) in calls
    assert (18, True) in calls
    assert (27, False) in calls
    assert (22, True) in calls

def test_turn_left_spins_wheels_opposite():
    d = make_driver()
    d.turn_left(speed=60)
    calls = {call.args for call in GPIO.output.call_args_list}
    # Left wheels backward, right wheels forward
    assert (17, False) in calls
    assert (18, True) in calls
    assert (27, True) in calls
    assert (22, False) in calls

def test_turn_right_spins_wheels_opposite():
    d = make_driver()
    d.turn_right(speed=60)
    calls = {call.args for call in GPIO.output.call_args_list}
    # Left wheels forward, right wheels backward
    assert (17, True) in calls
    assert (18, False) in calls
    assert (27, False) in calls
    assert (22, True) in calls

def test_stop_sets_duty_cycle_to_zero():
    d = make_driver()
    d.stop()
    d.pwm_a.ChangeDutyCycle.assert_called_with(0)
    d.pwm_b.ChangeDutyCycle.assert_called_with(0)

def test_cleanup_calls_gpio_cleanup():
    d = make_driver()
    d.cleanup()
    GPIO.cleanup.assert_called()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_motors.py -v
```
Expected: `ImportError: cannot import name 'MotorDriver' from 'motors.driver'`

- [ ] **Step 3: Create `motors/driver.py`**

```python
import RPi.GPIO as GPIO

class MotorDriver:
    def __init__(self, in1, in2, in3, in4, ena, enb):
        self.IN1, self.IN2 = in1, in2
        self.IN3, self.IN4 = in3, in4
        self.ENA, self.ENB = ena, enb

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in [in1, in2, in3, in4, ena, enb]:
            GPIO.setup(pin, GPIO.OUT)

        self.pwm_a = GPIO.PWM(ena, 1000)
        self.pwm_b = GPIO.PWM(enb, 1000)
        self.pwm_a.start(0)
        self.pwm_b.start(0)

    def _set_left(self, fwd: bool, speed: int):
        GPIO.output(self.IN1, fwd)
        GPIO.output(self.IN2, not fwd)
        self.pwm_a.ChangeDutyCycle(speed)

    def _set_right(self, fwd: bool, speed: int):
        GPIO.output(self.IN3, fwd)
        GPIO.output(self.IN4, not fwd)
        self.pwm_b.ChangeDutyCycle(speed)

    def forward(self, speed=70):
        self._set_left(True, speed)
        self._set_right(True, speed)

    def backward(self, speed=70):
        self._set_left(False, speed)
        self._set_right(False, speed)

    def turn_left(self, speed=60):
        self._set_left(False, speed)
        self._set_right(True, speed)

    def turn_right(self, speed=60):
        self._set_left(True, speed)
        self._set_right(False, speed)

    def stop(self):
        self.pwm_a.ChangeDutyCycle(0)
        self.pwm_b.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop()
        GPIO.cleanup()
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_motors.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add motors/driver.py tests/test_motors.py
git commit -m "feat: motor driver with PWM speed control"
```

---

## Task 4: Ultrasonic Sensor

**Files:**
- Create: `sensors/ultrasonic.py`
- Create: `tests/test_ultrasonic.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ultrasonic.py
import time
from unittest.mock import MagicMock, patch, call
import RPi.GPIO as GPIO
from sensors.ultrasonic import Ultrasonic

def make_sensor():
    return Ultrasonic(trig=23, echo=24)

def test_distance_returns_calculated_cm():
    sensor = make_sensor()
    # Simulate echo pulse of 0.00116s → ~20cm
    pulse_start = 1000.0
    pulse_end = 1000.00116
    side_effects = [0, 0, 1, 1, 0]  # echo low, low, high, high, low
    GPIO.input.side_effect = side_effects

    with patch("time.time", side_effect=[
        0,              # timeout check
        pulse_start,    # pulse_start capture
        0,              # timeout check
        pulse_end,      # pulse_end capture
    ]):
        dist = sensor.distance_cm()

    assert 19.0 < dist < 21.0

def test_distance_returns_999_on_timeout():
    sensor = make_sensor()
    # time.time() always > timeout (simulate stuck GPIO)
    with patch("time.time", return_value=9999.0):
        dist = sensor.distance_cm()
    assert dist == 999.0

def test_is_clear_returns_true_when_far():
    sensor = make_sensor()
    sensor.distance_cm = MagicMock(return_value=50.0)
    assert sensor.is_clear(threshold_cm=25) is True

def test_is_clear_returns_false_when_close():
    sensor = make_sensor()
    sensor.distance_cm = MagicMock(return_value=10.0)
    assert sensor.is_clear(threshold_cm=25) is False
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_ultrasonic.py -v
```
Expected: `ImportError: cannot import name 'Ultrasonic'`

- [ ] **Step 3: Create `sensors/ultrasonic.py`**

```python
import RPi.GPIO as GPIO
import time

class Ultrasonic:
    def __init__(self, trig, echo):
        self.TRIG = trig
        self.ECHO = echo
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        GPIO.output(trig, False)
        time.sleep(0.1)

    def distance_cm(self) -> float:
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)

        timeout = time.time() + 0.05
        while GPIO.input(self.ECHO) == 0:
            if time.time() > timeout:
                return 999.0
            pulse_start = time.time()

        while GPIO.input(self.ECHO) == 1:
            if time.time() > timeout:
                return 999.0
            pulse_end = time.time()

        duration = pulse_end - pulse_start
        return round(duration * 17150, 1)

    def is_clear(self, threshold_cm=25) -> bool:
        return self.distance_cm() > threshold_cm
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_ultrasonic.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sensors/ultrasonic.py tests/test_ultrasonic.py
git commit -m "feat: ultrasonic distance sensor with timeout safety"
```

---

## Task 5: LCD Display

**Files:**
- Create: `display/lcd.py`
- Create: `tests/test_lcd.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lcd.py
from RPLCD.i2c import CharLCD
from display.lcd import LCD

def make_lcd():
    return LCD(address=0x27)

def test_write_calls_clear_then_writes_line1():
    lcd = make_lcd()
    lcd.write("Hello World")
    lcd.lcd.clear.assert_called()
    lcd.lcd.write_string.assert_called_with("Hello World")

def test_write_truncates_to_16_chars():
    lcd = make_lcd()
    lcd.write("123456789012345678")  # 18 chars
    lcd.lcd.write_string.assert_called_with("1234567890123456")

def test_write_adds_second_line():
    lcd = make_lcd()
    lcd.write("Line one", "Line two")
    calls = [c.args[0] for c in lcd.lcd.write_string.call_args_list]
    assert calls == ["Line one", "Line two"]
    lcd.lcd.crlf.assert_called_once()

def test_write_truncates_line2_to_16_chars():
    lcd = make_lcd()
    lcd.write("Top", "123456789012345678")
    calls = [c.args[0] for c in lcd.lcd.write_string.call_args_list]
    assert calls[1] == "1234567890123456"

def test_clear_delegates_to_charlcd():
    lcd = make_lcd()
    lcd.clear()
    lcd.lcd.clear.assert_called()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_lcd.py -v
```
Expected: `ImportError: cannot import name 'LCD'`

- [ ] **Step 3: Create `display/lcd.py`**

```python
from RPLCD.i2c import CharLCD

class LCD:
    def __init__(self, address=0x27):
        self.lcd = CharLCD(
            i2c_expander="PCF8574",
            address=address,
            port=1,
            cols=16,
            rows=2,
            dotsize=8,
        )
        self.lcd.clear()

    def write(self, line1: str, line2: str = ""):
        self.lcd.clear()
        self.lcd.write_string(line1[:16])
        if line2:
            self.lcd.crlf()
            self.lcd.write_string(line2[:16])

    def clear(self):
        self.lcd.clear()
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_lcd.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add display/lcd.py tests/test_lcd.py
git commit -m "feat: LCD 1602 I2C display controller"
```

---

## Task 6: Autonomous Mode

**Files:**
- Create: `modes/autonomous.py`
- Create: `tests/test_autonomous.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_autonomous.py
from unittest.mock import MagicMock, patch
from modes.autonomous import AutonomousMode

def make_auto(distances):
    motors = MagicMock()
    sensor = MagicMock()
    lcd = MagicMock()
    sensor.distance_cm.side_effect = distances
    auto = AutonomousMode(motors=motors, sensor=sensor, lcd=lcd)
    return auto, motors, sensor, lcd

def test_drives_forward_when_clear():
    # Provide enough readings so the loop runs once then stops
    auto, motors, sensor, lcd = make_auto([50.0, 50.0])

    def stop_after_one(*args, **kwargs):
        auto.running = False

    motors.forward.side_effect = stop_after_one

    with patch("time.sleep"):
        auto.run()

    motors.forward.assert_called_once_with(70)
    motors.backward.assert_not_called()

def test_stops_and_avoids_on_obstacle():
    auto, motors, sensor, lcd = make_auto([10.0, 50.0])
    call_count = 0

    def stop_after_obstacle(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            auto.running = False

    motors.stop.side_effect = stop_after_obstacle

    with patch("time.sleep"), patch("random.random", return_value=0.1):
        auto.run()

    motors.stop.assert_called()
    motors.backward.assert_called()
    motors.turn_left.assert_called()

def test_lcd_shows_obstacle_distance():
    auto, motors, sensor, lcd = make_auto([10.0, 50.0])
    call_count = 0

    def stop_on_second(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            auto.running = False

    motors.stop.side_effect = stop_on_second

    with patch("time.sleep"), patch("random.random", return_value=0.1):
        auto.run()

    lcd.write.assert_any_call("Obstacle!", "10.0cm away")

def test_stop_method_halts_loop():
    auto, motors, sensor, lcd = make_auto([50.0] * 100)
    import threading

    def kill():
        import time as t
        t.sleep(0.05)
        auto.stop()

    t = threading.Thread(target=kill)
    with patch("time.sleep"):
        t.start()
        auto.run()
        t.join()

    motors.stop.assert_called()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_autonomous.py -v
```
Expected: `ImportError: cannot import name 'AutonomousMode'`

- [ ] **Step 3: Create `modes/autonomous.py`**

```python
import time
import random
from config import OBSTACLE_DISTANCE_CM, DRIVE_SPEED, TURN_SPEED, TURN_DURATION

class AutonomousMode:
    def __init__(self, motors, sensor, lcd):
        self.motors = motors
        self.sensor = sensor
        self.lcd = lcd
        self.running = False

    def run(self):
        self.running = True
        self.lcd.write("Rover: exploring!", "...")

        while self.running:
            dist = self.sensor.distance_cm()

            if dist > OBSTACLE_DISTANCE_CM:
                self.motors.forward(DRIVE_SPEED)
            else:
                self.motors.stop()
                self.lcd.write("Obstacle!", f"{dist}cm away")
                time.sleep(0.2)

                self.motors.backward(DRIVE_SPEED)
                time.sleep(0.3)

                if random.random() > 0.5:
                    self.motors.turn_left(TURN_SPEED)
                else:
                    self.motors.turn_right(TURN_SPEED)

                time.sleep(TURN_DURATION)
                self.motors.stop()

            time.sleep(0.05)

    def stop(self):
        self.running = False
        self.motors.stop()
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_autonomous.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add modes/autonomous.py tests/test_autonomous.py
git commit -m "feat: autonomous obstacle avoidance mode"
```

---

## Task 7: Claude Vision Narration

**Files:**
- Create: `camera/vision.py`
- Create: `tests/test_vision.py`

Note: The spec creates a new Picamera2 instance in ClaudeVision, but `main.py` also creates one for streaming — and only one Picamera2 instance is allowed at a time. This implementation accepts an existing `camera` and an optional `camera_lock` instead of creating its own.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_vision.py
import io
import threading
from unittest.mock import MagicMock, patch, call
from camera.vision import ClaudeVision

def make_vision():
    lcd = MagicMock()
    camera = MagicMock()
    client = MagicMock()
    # Simulate Claude returning a short description
    client.messages.create.return_value.content = [
        MagicMock(text="I see a cozy living room sofa.")
    ]
    vision = ClaudeVision(lcd=lcd, camera=camera)
    vision.client = client
    return vision, lcd, camera, client

def test_capture_jpeg_uses_provided_camera():
    vision, lcd, camera, client = make_vision()

    def fake_capture(stream, format):
        stream.write(b"FAKE_JPEG_DATA")

    camera.capture_file.side_effect = fake_capture
    result = vision._capture_jpeg()
    assert result == b"FAKE_JPEG_DATA"

def test_describe_calls_claude_with_base64_image():
    vision, lcd, camera, client = make_vision()
    desc = vision._describe(b"FAKE_JPEG")
    assert client.messages.create.called
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == vision.model
    content = call_kwargs["messages"][0]["content"]
    image_block = content[0]
    assert image_block["type"] == "image"
    assert image_block["source"]["type"] == "base64"

def test_describe_returns_stripped_text():
    vision, lcd, camera, client = make_vision()
    client.messages.create.return_value.content = [
        MagicMock(text="  I see a red chair.  ")
    ]
    assert vision._describe(b"data") == "I see a red chair."

def test_run_loop_writes_description_to_lcd():
    vision, lcd, camera, client = make_vision()
    vision._capture_jpeg = MagicMock(return_value=b"img")
    vision._describe = MagicMock(return_value="I see a bright kitchen window")
    vision.running = True

    call_count = [0]
    original_write = lcd.write

    def stop_after_one(l1, l2=""):
        call_count[0] += 1
        if call_count[0] >= 1:
            vision.running = False

    lcd.write.side_effect = stop_after_one

    with patch("time.sleep"):
        vision.run_loop()

    lcd.write.assert_called()

def test_run_loop_continues_on_error():
    vision, lcd, camera, client = make_vision()
    vision._capture_jpeg = MagicMock(side_effect=[Exception("camera fail"), b"img"])
    vision._describe = MagicMock(return_value="I see something")
    call_count = [0]

    def stop_after_two(l1, l2=""):
        call_count[0] += 1
        if call_count[0] >= 1:
            vision.running = False

    lcd.write.side_effect = stop_after_two
    vision.running = True

    with patch("time.sleep"):
        vision.run_loop()  # should not raise
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_vision.py -v
```
Expected: `ImportError: cannot import name 'ClaudeVision'`

- [ ] **Step 3: Create `camera/vision.py`**

```python
import base64
import io
import threading
import time
import anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL, VISION_INTERVAL_SEC

class ClaudeVision:
    def __init__(self, lcd, camera, camera_lock=None):
        self.lcd = lcd
        self.camera = camera
        self.camera_lock = camera_lock or threading.Lock()
        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        self.model = CLAUDE_MODEL
        self.running = False

    def _capture_jpeg(self) -> bytes:
        buf = io.BytesIO()
        with self.camera_lock:
            self.camera.capture_file(buf, format="jpeg")
        return buf.getvalue()

    def _describe(self, image_bytes: bytes) -> str:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are the eyes of a small robot rover exploring a home. "
                            "Describe what you see in ONE short sentence, max 12 words. "
                            "Be playful and curious. Start with 'I see' or 'I spot'."
                        ),
                    },
                ],
            }],
        )
        return response.content[0].text.strip()

    def run_loop(self):
        self.running = True
        while self.running:
            try:
                image_bytes = self._capture_jpeg()
                description = self._describe(image_bytes)
                words = description.split()
                line1 = " ".join(words[:8])[:16]
                line2 = " ".join(words[8:])[:16]
                self.lcd.write(line1, line2)
                print(f"[Claude Vision] {description}")
            except Exception as e:
                print(f"[Claude Vision] Error: {e}")
            time.sleep(VISION_INTERVAL_SEC)

    def start(self):
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_vision.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add camera/vision.py tests/test_vision.py
git commit -m "feat: Claude Vision narration with shared camera lock"
```

---

## Task 8: FPV Stream Server

**Files:**
- Create: `camera/stream.py`
- Create: `tests/test_stream.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stream.py
import io
import threading
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch
from camera.stream import start_stream

def test_stream_server_starts_and_serves_root():
    camera = MagicMock()

    def fake_capture(buf, format):
        buf.write(b"\xff\xd8\xff\xe0" + b"\x00" * 10)  # minimal JPEG header

    camera.capture_file.side_effect = fake_capture

    # Use a high ephemeral port to avoid conflicts
    with patch("camera.stream.STREAM_PORT", 18080):
        start_stream(camera)

    import time
    time.sleep(0.1)  # give server thread a moment

    conn = HTTPConnection("127.0.0.1", 18080, timeout=2)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    body = resp.read()
    assert b"<img" in body
    conn.close()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_stream.py -v
```
Expected: `ImportError: cannot import name 'start_stream'`

- [ ] **Step 3: Create `camera/stream.py`**

```python
import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import STREAM_PORT

class _StreamHandler(BaseHTTPRequestHandler):
    camera = None
    camera_lock = None

    def do_GET(self):
        if self.path == "/":
            self._serve_index()
        elif self.path == "/stream":
            self._serve_mjpeg()

    def _serve_index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""<html><body style='background:#000;margin:0'>
<img src='/stream' style='width:100%;height:100vh;object-fit:contain'>
</body></html>""")

    def _serve_mjpeg(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                buf = io.BytesIO()
                with _StreamHandler.camera_lock:
                    _StreamHandler.camera.capture_file(buf, format="jpeg")
                frame = buf.getvalue()
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except Exception:
            pass

    def log_message(self, *args):
        pass


def start_stream(camera, camera_lock=None):
    import threading as _threading
    _StreamHandler.camera = camera
    _StreamHandler.camera_lock = camera_lock or _threading.Lock()
    server = HTTPServer(("0.0.0.0", STREAM_PORT), _StreamHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[Stream] FPV at http://rover.local:{STREAM_PORT}")
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_stream.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add camera/stream.py tests/test_stream.py
git commit -m "feat: MJPEG FPV stream server with shared camera lock"
```

---

## Task 9: Web UI

**Files:**
- Create: `web/index.html`
- Create: `modes/manual.py`

No automated test — HTML is verified by opening in browser. Manual mode is thin glue code; the web UI is the real surface to test.

- [ ] **Step 1: Create `web/index.html`**

This page embeds the FPV stream and sends WASD keypresses to the rover via WebSocket (manual mode listens on port 8081).

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rover Control</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #111; color: #eee; font-family: monospace; display: flex; flex-direction: column; align-items: center; height: 100vh; }
    #stream { width: 100%; max-width: 640px; }
    #stream img { width: 100%; display: block; }
    #controls { padding: 16px; text-align: center; }
    #status { font-size: 12px; color: #888; margin-top: 8px; }
    .keys { display: grid; grid-template-columns: repeat(3, 56px); gap: 6px; justify-content: center; margin-top: 12px; }
    .key { width: 56px; height: 56px; border: 1px solid #444; background: #222; color: #eee; font-size: 18px; border-radius: 6px; display: flex; align-items: center; justify-content: center; user-select: none; cursor: pointer; transition: background 0.1s; }
    .key.active { background: #555; }
  </style>
</head>
<body>
  <div id="stream">
    <img src="/stream" alt="FPV stream" onerror="this.style.opacity=0.3">
  </div>
  <div id="controls">
    <div id="status">Connecting...</div>
    <div class="keys">
      <div></div>
      <div class="key" id="key-w">W</div>
      <div></div>
      <div class="key" id="key-a">A</div>
      <div class="key" id="key-s">S</div>
      <div class="key" id="key-d">D</div>
    </div>
    <div style="margin-top:10px;font-size:11px;color:#666">WASD to drive &bull; release to stop</div>
  </div>

  <script>
    const WS_PORT = 8081;
    let ws, reconnectTimer;

    function connect() {
      ws = new WebSocket(`ws://${location.hostname}:${WS_PORT}`);
      ws.onopen = () => { document.getElementById("status").textContent = "Connected"; };
      ws.onclose = () => {
        document.getElementById("status").textContent = "Disconnected — retrying...";
        reconnectTimer = setTimeout(connect, 2000);
      };
    }

    function send(cmd) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(cmd);
    }

    const keyMap = { w: "forward", s: "backward", a: "left", d: "right" };

    document.addEventListener("keydown", e => {
      const cmd = keyMap[e.key.toLowerCase()];
      if (cmd) { send(cmd); document.getElementById(`key-${e.key.toLowerCase()}`)?.classList.add("active"); }
    });
    document.addEventListener("keyup", e => {
      const cmd = keyMap[e.key.toLowerCase()];
      if (cmd) { send("stop"); document.getElementById(`key-${e.key.toLowerCase()}`)?.classList.remove("active"); }
    });

    // Touch buttons
    document.querySelectorAll(".key").forEach(el => {
      const key = el.id.replace("key-", "");
      el.addEventListener("pointerdown", () => { send(keyMap[key]); el.classList.add("active"); });
      el.addEventListener("pointerup",   () => { send("stop"); el.classList.remove("active"); });
      el.addEventListener("pointerleave",() => { send("stop"); el.classList.remove("active"); });
    });

    connect();
  </script>
</body>
</html>
```

- [ ] **Step 2: Create `modes/manual.py` — WebSocket command handler**

```python
import threading
import asyncio
import websockets
from config import DRIVE_SPEED, TURN_SPEED

MANUAL_WS_PORT = 8081

class ManualMode:
    def __init__(self, motors):
        self.motors = motors

    def _handle_command(self, cmd: str):
        dispatch = {
            "forward":  lambda: self.motors.forward(DRIVE_SPEED),
            "backward": lambda: self.motors.backward(DRIVE_SPEED),
            "left":     lambda: self.motors.turn_left(TURN_SPEED),
            "right":    lambda: self.motors.turn_right(TURN_SPEED),
            "stop":     self.motors.stop,
        }
        action = dispatch.get(cmd)
        if action:
            action()

    async def _handler(self, websocket):
        async for message in websocket:
            self._handle_command(message.strip())

    def start(self):
        async def _serve():
            async with websockets.serve(self._handler, "0.0.0.0", MANUAL_WS_PORT):
                await asyncio.Future()  # run forever

        def _run():
            asyncio.run(_serve())

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        print(f"[Manual] WebSocket on ws://rover.local:{MANUAL_WS_PORT}")
```

- [ ] **Step 3: Add `websockets` to requirements.txt**

```
RPi.GPIO==0.7.1
picamera2==0.3.21
RPLCD==1.3.0
anthropic==0.40.0
websockets==13.1
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 4: Commit**

```bash
git add web/index.html modes/manual.py requirements.txt
git commit -m "feat: web UI FPV + WASD control via WebSocket"
```

---

## Task 10: main.py — Wire Everything Together

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing integration smoke test**

```python
# tests/test_main.py
from unittest.mock import MagicMock, patch

def test_main_initialises_all_components_without_error():
    """Smoke test: main() constructs all hardware objects and starts threads."""
    with patch("main.LCD") as MockLCD, \
         patch("main.MotorDriver") as MockMotors, \
         patch("main.Ultrasonic") as MockSensor, \
         patch("main.Picamera2") as MockCamera, \
         patch("main.start_stream"), \
         patch("main.ClaudeVision") as MockVision, \
         patch("main.ManualMode") as MockManual, \
         patch("main.AutonomousMode") as MockAuto, \
         patch("main.GPIO"):

        mock_auto_instance = MagicMock()
        mock_auto_instance.run.side_effect = KeyboardInterrupt
        MockAuto.return_value = mock_auto_instance

        from main import main
        main()

        MockLCD.assert_called_once()
        MockMotors.assert_called_once()
        MockSensor.assert_called_once()
        MockCamera.assert_called_once()
        MockVision.assert_called_once()
        mock_auto_instance.run.assert_called_once()
```

- [ ] **Step 2: Run — verify FAIL**

```bash
python -m pytest tests/test_main.py -v
```
Expected: `ImportError: No module named 'main'` or `AttributeError`.

- [ ] **Step 3: Create `main.py`**

```python
import threading
import time
import RPi.GPIO as GPIO

from config import (
    PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4, PIN_ENA, PIN_ENB,
    PIN_TRIG, PIN_ECHO,
    STREAM_WIDTH, STREAM_HEIGHT,
    LCD_ADDRESS,
)
from motors.driver import MotorDriver
from sensors.ultrasonic import Ultrasonic
from display.lcd import LCD
from modes.autonomous import AutonomousMode
from modes.manual import ManualMode
from camera.vision import ClaudeVision
from camera.stream import start_stream
from picamera2 import Picamera2

def main():
    print("[Rover] Booting...")

    lcd = LCD(LCD_ADDRESS)
    lcd.write("Rover booting", "please wait...")

    motors = MotorDriver(PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4, PIN_ENA, PIN_ENB)
    sensor = Ultrasonic(PIN_TRIG, PIN_ECHO)

    camera = Picamera2()
    camera.configure(camera.create_video_configuration(
        main={"size": (STREAM_WIDTH, STREAM_HEIGHT)}
    ))
    camera.start()

    camera_lock = threading.Lock()

    lcd.write("Camera ready", "Starting...")

    start_stream(camera, camera_lock)

    vision = ClaudeVision(lcd=lcd, camera=camera, camera_lock=camera_lock)
    vision.start()

    manual = ManualMode(motors)
    manual.start()

    lcd.write("Rover ready!", "Exploring...")
    time.sleep(1)

    auto = AutonomousMode(motors, sensor, lcd)

    try:
        auto.run()
    except KeyboardInterrupt:
        print("[Rover] Stopping...")
    finally:
        auto.stop()
        vision.stop()
        motors.cleanup()
        lcd.write("Rover stopped", "Goodbye!")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — verify PASS**

```bash
python -m pytest tests/test_main.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: all tests pass, no warnings about uncollected items.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: main entry point wiring all rover subsystems"
```

---

## Task 11: Pi Deployment

**Files:**
- Create: `install.sh` (runs on the Pi)

No test — this is a shell script for the Pi environment.

- [ ] **Step 1: Create `install.sh`**

```bash
#!/bin/bash
set -e

echo "=== Rover Pi Setup ==="

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv i2c-tools git

# Enable camera + I2C (requires reboot after)
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0

python3 -m venv rover-env
source rover-env/bin/activate

pip install --upgrade pip
pip install RPi.GPIO picamera2 RPLCD anthropic websockets

echo ""
echo "=== Hardware checks ==="
echo "I2C devices (expect 0x27 or 0x3F for LCD):"
i2cdetect -y 1 || echo "  [SKIP] I2C not enabled yet — reboot first"

echo "Camera test:"
libcamera-hello --timeout 2000 || echo "  [SKIP] Camera not detected"

echo ""
echo "=== Setup complete ==="
echo "1. Edit config.py — set CLAUDE_API_KEY"
echo "2. Confirm LCD_ADDRESS matches i2cdetect output"
echo "3. Run: source rover-env/bin/activate && python main.py"
```

- [ ] **Step 2: Make it executable**

On Pi:
```bash
chmod +x install.sh
./install.sh
```

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: Pi install script with hardware verification"
```

---

## Self-Review

### Spec Coverage Check

| Spec requirement | Covered in task |
|---|---|
| HC-SR04 obstacle avoidance | Task 4 (sensor) + Task 6 (autonomous mode) |
| FPV stream at rover.local:8080 | Task 8 (stream server) |
| Claude Vision every 5s → LCD | Task 7 (vision) |
| WASD web UI | Task 9 (web/index.html + manual.py) |
| L298N PWM motor control | Task 3 (motor driver) |
| LCD 1602 I2C display | Task 5 (lcd.py) |
| Shared camera (single Picamera2) | Tasks 7 + 8 — camera_lock threaded sharing |
| Voltage divider note on ECHO pin | Hardware-only — in spec, no code needed |
| config.py all constants | Task 2 |
| main.py boot sequence | Task 10 |
| Pi installation | Task 11 |

### Placeholder Scan

No TBD, TODO, or placeholder step found.

### Type Consistency

- `MotorDriver.forward(speed)` defined Task 3, called with `DRIVE_SPEED` (int) in Tasks 6, 9 ✓
- `LCD.write(line1, line2="")` defined Task 5, called consistently in Tasks 6, 7, 10 ✓
- `ClaudeVision(lcd, camera, camera_lock)` defined Task 7, constructed with all args in Task 10 ✓
- `start_stream(camera, camera_lock)` defined Task 8, called with both args in Task 10 ✓
- `ManualMode(motors)` defined Task 9, constructed in Task 10 ✓

All interfaces consistent.
