from RPLCD.i2c import CharLCD
from display.lcd import LCD


def make_lcd():
    CharLCD.return_value.reset_mock()  # clear shared mock's call history between tests
    return LCD(address=0x27)


def test_write_calls_clear_then_writes_line1():
    lcd = make_lcd()
    lcd.write("Hello World")
    lcd.lcd.clear.assert_called()
    lcd.lcd.write_string.assert_called_with("Hello World")


def test_write_truncates_to_16_chars():
    lcd = make_lcd()
    lcd.write("123456789012345678")  # 18 chars
    lcd.lcd.write_string.assert_called_with("1234567890123456")


def test_write_adds_second_line():
    lcd = make_lcd()
    lcd.write("Line one", "Line two")
    calls = [c.args[0] for c in lcd.lcd.write_string.call_args_list]
    assert calls == ["Line one", "Line two"]
    lcd.lcd.crlf.assert_called_once()


def test_write_truncates_line2_to_16_chars():
    lcd = make_lcd()
    lcd.write("Top", "123456789012345678")
    calls = [c.args[0] for c in lcd.lcd.write_string.call_args_list]
    assert calls[1] == "1234567890123456"


def test_clear_delegates_to_charlcd():
    lcd = make_lcd()
    lcd.clear()
    lcd.lcd.clear.assert_called()
