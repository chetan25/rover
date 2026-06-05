import time
import random
from config import OBSTACLE_DISTANCE_CM, DRIVE_SPEED, TURN_SPEED, TURN_DURATION


class AutonomousMode:
    """
    Obstacle-avoidance drive loop.

    Reads HC-SR04 distance at ~20 Hz. If clear: drive forward.
    If blocked: stop, back up, turn randomly left or right, resume.
    LCD shows status at each state change.
    """

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

            time.sleep(0.05)  # 20 Hz sensor poll

    def stop(self):
        self.running = False
        self.motors.stop()
