import RPi.GPIO as GPIO
from motors.driver import MotorDriver


def make_driver():
    GPIO.output.reset_mock()
    return MotorDriver(in1=17, in2=18, in3=27, in4=22, ena=12, enb=13)


def test_forward_sets_both_sides_forward():
    d = make_driver()
    d.forward(speed=70)
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
