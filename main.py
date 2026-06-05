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
