# ── Motors — L298N logic pins (all OUTPUT via GPIO BCM numbering) ──────────────
PIN_IN1 = 17   # Left  motors fwd/rev A  → L298N IN1  → Pi physical pin 11
PIN_IN2 = 18   # Left  motors fwd/rev B  → L298N IN2  → Pi physical pin 12
PIN_IN3 = 27   # Right motors fwd/rev A  → L298N IN3  → Pi physical pin 13
PIN_IN4 = 22   # Right motors fwd/rev B  → L298N IN4  → Pi physical pin 15
PIN_ENA = 12   # Left  speed PWM         → L298N ENA  → Pi physical pin 32
PIN_ENB = 13   # Right speed PWM         → L298N ENB  → Pi physical pin 33

# ── HC-SR04 ultrasonic sensor ──────────────────────────────────────────────────
PIN_TRIG = 23  # OUTPUT — Pi physical pin 16 — 10µs pulse to trigger measurement
PIN_ECHO = 24  # INPUT  — Pi physical pin 18 — HIGH pulse width = distance
               # WARNING: HC-SR04 ECHO is 5V; use voltage divider (1kΩ+2kΩ) before GPIO!

# ── Rover behaviour ────────────────────────────────────────────────────────────
OBSTACLE_DISTANCE_CM = 25   # reverse+turn if obstacle closer than this
DRIVE_SPEED = 70             # PWM duty cycle 0-100 for straight driving
TURN_SPEED = 60              # PWM duty cycle 0-100 for turning
TURN_DURATION = 0.5          # seconds to spin when avoiding an obstacle

# ── Claude Vision ──────────────────────────────────────────────────────────────
VISION_INTERVAL_SEC = 5
CLAUDE_API_KEY = "sk-ant-..."  # set this before deploying to Pi
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# ── Camera / FPV stream ────────────────────────────────────────────────────────
STREAM_PORT = 8080
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
STREAM_FPS = 15

# ── LCD 1602 I2C ───────────────────────────────────────────────────────────────
# SDA → GPIO 2 (Pi physical pin 3), SCL → GPIO 3 (Pi physical pin 5)
# Run `i2cdetect -y 1` on Pi to confirm address — usually 0x27 or 0x3F
LCD_ADDRESS = 0x27
