import RPi.GPIO as GPIO
import time


class Ultrasonic:
    """
    HC-SR04 ultrasonic distance sensor.

    Pin wiring (BCM numbering):
      TRIG → GPIO 23 (OUTPUT) — Pi physical pin 16
      ECHO → GPIO 24 (INPUT)  — Pi physical pin 18
             ECHO is 5 V — use a 1kΩ+2kΩ voltage divider before the GPIO pin!
    """

    def __init__(self, trig, echo):
        self.TRIG = trig
        self.ECHO = echo
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        GPIO.output(trig, False)
        time.sleep(0.1)  # let sensor settle

    def distance_cm(self) -> float:
        # Send 10 µs trigger pulse
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)

        timeout = time.time() + 0.05  # 50 ms max — avoids hanging on no echo

        # Wait for ECHO to go HIGH (rising edge = pulse start)
        while GPIO.input(self.ECHO) == 0:
            if time.time() > timeout:
                return 999.0

        pulse_start = time.time()

        # Wait for ECHO to go LOW (falling edge = pulse end)
        while GPIO.input(self.ECHO) == 1:
            if time.time() > timeout:
                return 999.0

        pulse_end = time.time()

        return round((pulse_end - pulse_start) * 17150, 1)  # speed of sound / 2

    def is_clear(self, threshold_cm=25) -> bool:
        return self.distance_cm() > threshold_cm
