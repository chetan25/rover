from unittest.mock import MagicMock, patch
import RPi.GPIO as GPIO
from sensors.ultrasonic import Ultrasonic


def make_sensor():
    GPIO.input.reset_mock()
    GPIO.input.side_effect = None  # clear any iterator left by a previous test
    GPIO.input.return_value = 0
    GPIO.output.reset_mock()
    return Ultrasonic(trig=23, echo=24)


def test_distance_returns_calculated_cm():
    sensor = make_sensor()
    # ECHO sequence: LOW (1 loop in first while) → HIGH (exits) → HIGH (1 loop in second while) → LOW (exits)
    GPIO.input.side_effect = [0, 1, 1, 0]
    with patch("time.time", side_effect=[
        0,           # timeout init → deadline = 0.05
        0,           # first while body timeout check (0 > 0.05 → no timeout)
        1000.0,      # pulse_start captured after first while exits
        0,           # second while body timeout check (0 > 0.05 → no timeout)
        1000.00116,  # pulse_end captured after second while exits (~20 cm)
    ]):
        dist = sensor.distance_cm()
    assert 19.0 < dist < 21.0


def test_distance_returns_999_on_timeout():
    sensor = make_sensor()
    GPIO.input.return_value = 0  # ECHO stuck LOW forever
    with patch("time.time", side_effect=[
        0,     # timeout init → deadline = 0.05
        100.0, # first while body check: 100.0 > 0.05 → timeout → return 999
    ]):
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
