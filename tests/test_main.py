from unittest.mock import MagicMock, patch


def test_main_initialises_all_components_without_error():
    """Smoke test: main() constructs all hardware objects and starts threads."""
    with patch("main.LCD") as MockLCD, \
         patch("main.MotorDriver") as MockMotors, \
         patch("main.Ultrasonic") as MockSensor, \
         patch("main.Picamera2") as MockCamera, \
         patch("main.start_stream"), \
         patch("main.ClaudeVision") as MockVision, \
         patch("main.BluetoothController") as MockBT, \
         patch("main.AutonomousMode") as MockAuto, \
         patch("main.GPIO"), \
         patch("main.time.sleep"):

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
