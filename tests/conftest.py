import sys
import types
from unittest.mock import MagicMock

# --- RPi.GPIO mock ---
gpio_mock = types.ModuleType("RPi")
gpio_mock.GPIO = MagicMock()
gpio_mock.GPIO.BCM = 11
gpio_mock.GPIO.OUT = 0
gpio_mock.GPIO.IN = 1
gpio_mock.GPIO.HIGH = 1
gpio_mock.GPIO.LOW = 0
gpio_mock.GPIO.input = MagicMock(return_value=0)
gpio_mock.GPIO.output = MagicMock()
gpio_mock.GPIO.setup = MagicMock()
gpio_mock.GPIO.setmode = MagicMock()
gpio_mock.GPIO.setwarnings = MagicMock()
gpio_mock.GPIO.cleanup = MagicMock()

pwm_instance = MagicMock()
pwm_instance.start = MagicMock()
pwm_instance.ChangeDutyCycle = MagicMock()
pwm_instance.stop = MagicMock()
gpio_mock.GPIO.PWM = MagicMock(return_value=pwm_instance)

sys.modules["RPi"] = gpio_mock
sys.modules["RPi.GPIO"] = gpio_mock.GPIO

# --- picamera2 mock ---
picamera2_mock = types.ModuleType("picamera2")
mock_camera = MagicMock()
mock_camera.configure = MagicMock()
mock_camera.start = MagicMock()
mock_camera.stop = MagicMock()
mock_camera.capture_file = MagicMock()
mock_camera.create_still_configuration = MagicMock(return_value={})
mock_camera.create_video_configuration = MagicMock(return_value={})
picamera2_mock.Picamera2 = MagicMock(return_value=mock_camera)
sys.modules["picamera2"] = picamera2_mock

# --- RPLCD mock ---
rplcd_mock = types.ModuleType("RPLCD")
rplcd_i2c_mock = types.ModuleType("RPLCD.i2c")
mock_lcd_instance = MagicMock()
mock_lcd_instance.clear = MagicMock()
mock_lcd_instance.write_string = MagicMock()
mock_lcd_instance.crlf = MagicMock()
rplcd_i2c_mock.CharLCD = MagicMock(return_value=mock_lcd_instance)
rplcd_mock.i2c = rplcd_i2c_mock
sys.modules["RPLCD"] = rplcd_mock
sys.modules["RPLCD.i2c"] = rplcd_i2c_mock
