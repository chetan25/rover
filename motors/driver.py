import RPi.GPIO as GPIO


class MotorDriver:
    """
    Controls 4WD chassis via L298N dual H-bridge.

    Pin wiring (BCM numbering):
      IN1/IN2 — left  motors direction  (OUTPUT)
      IN3/IN4 — right motors direction  (OUTPUT)
      ENA     — left  motors PWM speed  (OUTPUT, GPIO 12 hardware PWM)
      ENB     — right motors PWM speed  (OUTPUT, GPIO 13 hardware PWM)
    """

    def __init__(self, in1, in2, in3, in4, ena, enb):
        self.IN1, self.IN2 = in1, in2
        self.IN3, self.IN4 = in3, in4
        self.ENA, self.ENB = ena, enb

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in (in1, in2, in3, in4, ena, enb):
            GPIO.setup(pin, GPIO.OUT)

        self.pwm_a = GPIO.PWM(ena, 1000)   # 1 kHz PWM on ENA
        self.pwm_b = GPIO.PWM(enb, 1000)   # 1 kHz PWM on ENB
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
        self._set_left(False, speed)   # left wheels backward
        self._set_right(True, speed)   # right wheels forward

    def turn_right(self, speed=60):
        self._set_left(True, speed)    # left wheels forward
        self._set_right(False, speed)  # right wheels backward

    def stop(self):
        self.pwm_a.ChangeDutyCycle(0)
        self.pwm_b.ChangeDutyCycle(0)

    def cleanup(self):
        self.stop()
        self.pwm_a.stop()
        self.pwm_b.stop()
        GPIO.cleanup()
