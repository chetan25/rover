import threading
from unittest.mock import MagicMock, patch
from modes.autonomous import AutonomousMode


def make_auto(distances):
    motors = MagicMock()
    sensor = MagicMock()
    lcd = MagicMock()
    sensor.distance_cm.side_effect = distances
    return AutonomousMode(motors=motors, sensor=sensor, lcd=lcd), motors, sensor, lcd


def test_drives_forward_when_clear():
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
    motors.turn_right.assert_called()  # random=0.1 < 0.5 → turn_right


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
    motors = MagicMock()
    sensor = MagicMock()
    lcd = MagicMock()
    sensor.distance_cm.return_value = 50.0  # unlimited — never exhausts
    auto = AutonomousMode(motors=motors, sensor=sensor, lcd=lcd)

    started = threading.Event()
    motors.forward.side_effect = lambda *a, **kw: started.set()

    def kill():
        started.wait(timeout=5)  # wait for loop to start
        auto.stop()

    t = threading.Thread(target=kill)
    # patch only the autonomous module's sleep so kill-thread timing is real
    with patch("modes.autonomous.time.sleep"):
        t.start()
        auto.run()
        t.join()

    motors.stop.assert_called()
