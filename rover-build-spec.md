# AI Rover — Complete Build Spec

> 4WD chassis + Pi 5 + L298N + HC-SR04 + Camera + Claude Vision

---

## What this rover does

| Mode            | How to trigger        | What happens                                                      |
| --------------- | --------------------- | ----------------------------------------------------------------- |
| Autonomous      | Default on boot       | HC-SR04 avoids obstacles, drives freely                           |
| FPV             | Open browser on phone | Live camera stream at `rover.local:8080`                          |
| Claude Vision   | Automatic every 5s    | Camera snapshot → Claude describes what it sees → LCD displays it |
| Manual override | Keyboard / web UI     | WASD control from browser                                         |

---

## Hardware you have

| Part                   | Role on rover                           |
| ---------------------- | --------------------------------------- |
| 4WD acrylic chassis    | Already built                           |
| 4x DC yellow TT motors | Already mounted                         |
| L298N motor driver     | Controls all 4 motors                   |
| Raspberry Pi 5         | Brain — runs all code and AI            |
| Pi M2 Hat (NVMe)       | Fast storage, model cache               |
| Pi Camera rev 1.3      | FPV stream + Claude Vision snapshots    |
| HC-SR04                | Front obstacle detection                |
| Pico                   | Optional: LED animations while thinking |
| LCD 1602 IIC           | Displays Claude Vision narration        |
| AA battery pack (6V)   | Powers motors via L298N                 |
| USB power bank         | Powers Pi 5 separately                  |

---

## Power architecture — critical to get right

```
AA Battery Pack (6V)
    └── L298N motor power input (VM pin)
        ├── L298N 5V out → NOT used for Pi (too weak)
        └── 4x motors via OUT1-OUT4

USB Power Bank (5V 3A+)
    └── Pi 5 USB-C
        ├── Pi 5 GPIO 5V → HC-SR04 VCC
        ├── Pi 5 GPIO 3.3V → LCD VCC
        └── Pi 5 GPIO → L298N logic pins (IN1-IN4, ENA, ENB)
```

**Why separate supplies:** Pi 5 draws up to 5A under load (camera + AI). Motors cause voltage spikes. Mixing them causes Pi to reboot mid-drive. Separate supplies = rock solid.

**Important:** L298N GND and Pi GND must be connected together (shared ground) even though power sources are separate.

---

## L298N wiring to Pi 5

### L298N module pinout

```
L298N Pin    →    Pi 5 GPIO Pin    →    Wire colour (suggest)
─────────────────────────────────────────────────────────────
IN1          →    GPIO 17          →    Yellow
IN2          →    GPIO 18          →    Orange
IN3          →    GPIO 27          →    Green
IN4          →    GPIO 22          →    Blue
ENA          →    GPIO 12 (PWM)    →    White
ENB          →    GPIO 13 (PWM)    →    Grey
GND          →    Pi GND (Pin 6)   →    Black  ← shared ground!
VM (12V in)  →    AA Battery +     →    Red
GND (power)  →    AA Battery -     →    Black
```

**Motor wiring on L298N:**

```
OUT1 + OUT2  →  Left motors  (both wired in parallel)
OUT3 + OUT4  →  Right motors (both wired in parallel)
```

To wire 2 motors to one output pair — connect both motor + wires together to OUT1, both - wires together to OUT2. Same for right side.

**ENA/ENB jumpers:** Remove the jumpers on ENA and ENB — these enable PWM speed control. If you leave jumpers on, motors run full speed only.

---

## HC-SR04 wiring to Pi 5

```
HC-SR04 Pin  →  Pi 5 GPIO
────────────────────────────
VCC          →  5V (Pin 2)
GND          →  GND (Pin 6)
TRIG         →  GPIO 23 (Pin 16)
ECHO         →  GPIO 24 (Pin 18)  ← via voltage divider!
```

**Voltage divider for ECHO pin — required:**
Pi 5 GPIO is 3.3V max. HC-SR04 ECHO outputs 5V. Without a divider you will damage the Pi.

```
HC-SR04 ECHO → 1kΩ → GPIO 24
                          ↓
                        2kΩ
                          ↓
                         GND
```

This divides 5V to ~3.3V. Any resistors in roughly 1:2 ratio work (e.g. 1kΩ + 2kΩ, or 470Ω + 1kΩ).

---

## Pi Camera wiring

CSI ribbon cable into Pi 5 Camera port (the slot next to the USB-C). Gently lift the connector latch, slide ribbon in blue-side up, press latch down.

Mount camera on the front of the top chassis layer facing forward. Use a servo for pan/tilt later (Phase 2).

---

## LCD 1602 IIC wiring to Pi 5

```
LCD Pin  →  Pi 5
─────────────────
VCC      →  3.3V (Pin 1)
GND      →  GND (Pin 9)
SDA      →  GPIO 2 / SDA (Pin 3)
SCL      →  GPIO 3 / SCL (Pin 5)
```

Enable I2C: `sudo raspi-config` → Interface Options → I2C → Enable

---

## Project structure

```
rover-pi/
├── main.py                    # Entry point — wires all components, starts threads
├── config.py                  # All constants: GPIO pins, speeds, API key, camera settings
├── requirements.txt           # Pinned dependencies
├── install.sh                 # Pi setup script (apt + pip + hardware checks)
├── motors/
│   ├── __init__.py
│   └── driver.py              # L298N PWM motor control — forward/back/turn/stop
├── sensors/
│   ├── __init__.py
│   └── ultrasonic.py          # HC-SR04 distance measurement with timeout safety
├── camera/
│   ├── __init__.py
│   ├── stream.py              # MJPEG HTTP server — shares camera with vision via lock
│   └── vision.py              # Claude Vision — snapshot → describe → LCD write
├── display/
│   ├── __init__.py
│   └── lcd.py                 # LCD 1602 I2C 2-line write wrapper
├── modes/
│   ├── __init__.py
│   ├── autonomous.py          # Obstacle-avoid loop — reads sensor, commands motors
│   └── manual.py              # WebSocket WASD handler — receives commands, drives motors
├── web/
│   └── index.html             # Phone browser UI — FPV stream + WASD keyboard/touch control
└── tests/
    ├── __init__.py
    ├── conftest.py            # Mocks for RPi.GPIO, picamera2, RPLCD, websockets
    ├── test_motors.py
    ├── test_ultrasonic.py
    ├── test_lcd.py
    ├── test_autonomous.py
    ├── test_vision.py
    ├── test_stream.py
    └── test_main.py
```

**Key design decision — shared camera:** Pi only allows one `Picamera2` instance at a time. `main.py` creates it once and passes it (with a `threading.Lock`) to both `start_stream` and `ClaudeVision`. The lock ensures the MJPEG loop and vision snapshots never call `capture_file` simultaneously.

---

## config.py

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
OBSTACLE_DISTANCE_CM = 25      # stop and turn if closer than this
DRIVE_SPEED = 70               # 0-100 PWM duty cycle
TURN_SPEED = 60
TURN_DURATION = 0.5            # seconds to turn when avoiding

# Claude Vision
VISION_INTERVAL_SEC = 5        # how often to snapshot + narrate
CLAUDE_API_KEY = "sk-ant-..."
CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # fastest, cheapest

# Camera stream
STREAM_PORT = 8080
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
STREAM_FPS = 15

# LCD I2C address (run i2cdetect -y 1 to confirm — usually 0x27 or 0x3F)
LCD_ADDRESS = 0x27
```

---

## motors/driver.py

```python
import RPi.GPIO as GPIO
import time

class MotorDriver:
    def __init__(self, in1, in2, in3, in4, ena, enb):
        self.IN1, self.IN2 = in1, in2
        self.IN3, self.IN4 = in3, in4
        self.ENA, self.ENB = ena, enb

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in [in1, in2, in3, in4, ena, enb]:
            GPIO.setup(pin, GPIO.OUT)

        self.pwm_a = GPIO.PWM(ena, 1000)   # 1kHz PWM
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
        self._set_left(False, speed)    # left wheels backward
        self._set_right(True, speed)    # right wheels forward

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

---

## sensors/ultrasonic.py

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
        # Send pulse
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)

        # Wait for echo
        timeout = time.time() + 0.05   # 50ms timeout
        while GPIO.input(self.ECHO) == 0:
            if time.time() > timeout:
                return 999.0            # no echo = open space
            pulse_start = time.time()

        while GPIO.input(self.ECHO) == 1:
            if time.time() > timeout:
                return 999.0
            pulse_end = time.time()

        duration = pulse_end - pulse_start
        distance = duration * 17150     # speed of sound / 2
        return round(distance, 1)

    def is_clear(self, threshold_cm=25) -> bool:
        return self.distance_cm() > threshold_cm
```

---

## modes/autonomous.py

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
                # Obstacle detected
                self.motors.stop()
                self.lcd.write("Obstacle!", f"{dist}cm away")
                time.sleep(0.2)

                self.motors.backward(DRIVE_SPEED)
                time.sleep(0.3)

                # Randomly turn left or right
                if random.random() > 0.5:
                    self.motors.turn_left(TURN_SPEED)
                else:
                    self.motors.turn_right(TURN_SPEED)

                time.sleep(TURN_DURATION)
                self.motors.stop()

            time.sleep(0.05)    # 20Hz sensor loop

    def stop(self):
        self.running = False
        self.motors.stop()
```

---

## camera/vision.py — the AI layer

`ClaudeVision` accepts the shared `camera` and `camera_lock` from `main.py` rather than creating its own `Picamera2` instance — only one instance is allowed per Pi.

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

---

## camera/stream.py — FPV to phone

Serves two routes: `GET /` returns an HTML page with an `<img>` tag, `GET /stream` is the MJPEG feed. Uses the same `camera_lock` as `ClaudeVision` so captures don't collide.

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
    _StreamHandler.camera = camera
    _StreamHandler.camera_lock = camera_lock or threading.Lock()
    server = HTTPServer(("0.0.0.0", STREAM_PORT), _StreamHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[Stream] FPV at http://rover.local:{STREAM_PORT}")
```

---

## display/lcd.py

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
            dotsize=8
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

---

## modes/manual.py — WASD over WebSocket

The web UI sends keyboard/touch commands to a WebSocket server on port 8081. `ManualMode` listens and dispatches to `MotorDriver`.

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
                await asyncio.Future()

        t = threading.Thread(target=lambda: asyncio.run(_serve()), daemon=True)
        t.start()
        print(f"[Manual] WebSocket on ws://rover.local:{MANUAL_WS_PORT}")
```

**Why WebSocket for manual control?** HTTP is request/response — you'd need to poll the server every ~50ms for smooth control, wasting bandwidth and adding latency. WebSocket keeps a persistent connection open so each keypress/release sends a message instantly with no overhead. The rover reacts in <10ms instead of the 50–200ms you'd get with polling.

---

## web/index.html — phone browser UI

Served from the Pi's filesystem. Open `http://rover.local:8080` on your phone — the page loads the FPV stream and connects to the WebSocket on port 8081. WASD keys on desktop or tap-and-hold buttons on mobile.

- `W` / up-button → `forward`
- `S` / down-button → `backward`
- `A` / left-button → `left`
- `D` / right-button → `right`
- Key/button release → `stop`

Auto-reconnects to WebSocket every 2 seconds if connection drops.

---

## main.py

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

---

## Install

`install.sh` handles the full Pi setup in one shot:

```bash
chmod +x install.sh
./install.sh
```

It runs: `apt update/upgrade`, enables camera + I2C via `raspi-config`, creates a venv, installs all Python deps, then runs `i2cdetect -y 1` and `libcamera-hello` to confirm hardware is wired up.

After it finishes:

```bash
# 1. Set your API key
nano config.py   # set CLAUDE_API_KEY = "sk-ant-..."

# 2. Confirm LCD address matches i2cdetect output (usually 0x27 or 0x3F)
#    Update LCD_ADDRESS in config.py if needed

# 3. Run
source rover-env/bin/activate
python main.py
```

**Python dependencies** (`requirements.txt`):

```
RPi.GPIO==0.7.1
picamera2==0.3.21
RPLCD==1.3.0
anthropic>=0.50.0
websockets==13.1
pytest==8.3.4
pytest-mock==3.14.0
```

---

## Tests

The test suite runs on Windows/Mac/Linux — all Pi-only hardware (`RPi.GPIO`, `picamera2`, `RPLCD`, `websockets`) is mocked in `tests/conftest.py`.

```bash
python -m pytest tests/ -v
```

Expected: 26 passed.

---

## Access from phone

Connect phone to same WiFi as Pi 5. Open browser:

```
http://rover.local:8080
```

You see the live FPV stream and WASD touch buttons. Tap and hold a button to drive; release to stop. Claude Vision narration appears on the LCD every 5 seconds.

| Port | What's there |
|------|-------------|
| 8080 | FPV stream + web UI (`web/index.html`) |
| 8081 | WebSocket for WASD commands (used by the web UI automatically) |

To find Pi IP if `.local` doesn't work:

```bash
hostname -I
# e.g. 192.168.1.42 → open http://192.168.1.42:8080
```

---

## Claude Vision prompt tuning

The vision prompt in `camera/vision.py` is the personality. Change it to change the experience:

**For your child watching:**

```
You are a curious little robot exploring a home.
Describe what you see in ONE excited sentence, max 10 words.
Start with "Ooh!" or "Whoa!" or "Look!"
```

**For obstacle narration:**

```
You are a rover. In max 8 words describe:
what is in front of you and if the path is clear.
```

**For a game — child has to guess where the rover is:**

```
Give ONE clue about where you are in the house.
Max 8 words. Don't say the room name directly.
```

---

## Phase 2 upgrades (after this works)

| Upgrade          | What to add                                          |
| ---------------- | ---------------------------------------------------- |
| Pan/tilt camera  | MS18 servo on camera mount — controlled from web UI  |
| Voice commands   | USB mic + "forward", "stop", "turn left" via Whisper |
| LED headlights   | WS2812B strip on front — lights up when moving       |
| Speed control    | Web UI slider → PWM duty cycle via WebSocket         |
| Object detection | YOLOv5 on Pi 5 — stops when it sees a person         |
| Return home      | Add compass module — rover navigates back to start   |

---

## Build order for today

```
Step 1 (20 min) — Mount Pi 5 on top chassis layer
Step 2 (20 min) — Wire L298N to motors and battery pack
Step 3 (15 min) — Wire L298N logic pins to Pi 5 GPIO
Step 4 (10 min) — Wire HC-SR04 with voltage divider
Step 5 (10 min) — Wire LCD via I2C
Step 6 (10 min) — Mount camera on front
Step 7 (30 min) — Install software and test each component
Step 8 (20 min) — Run main.py and watch it drive
Step 9 (10 min) — Open browser on phone — FPV live
Step 10 (ongoing) — Watch Claude narrate what the rover sees
```

Total: ~2.5 hours from now to a driving AI rover.
