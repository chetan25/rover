from RPLCD.i2c import CharLCD


class LCD:
    """
    LCD 1602 I2C display wrapper (16 columns, 2 rows).

    Wiring (I2C — not GPIO-controlled directly):
      VCC → 3.3 V (Pi physical pin 1)
      GND → GND   (Pi physical pin 9)
      SDA → GPIO 2 / SDA (Pi physical pin 3)
      SCL → GPIO 3 / SCL (Pi physical pin 5)

    Run `i2cdetect -y 1` on Pi to confirm the I2C address (0x27 or 0x3F).
    """

    def __init__(self, address=0x27):
        self.lcd = CharLCD(
            i2c_expander="PCF8574",
            address=address,
            port=1,       # I2C bus 1 (default on all Pi models)
            cols=16,
            rows=2,
            dotsize=8,
        )
        self.lcd.clear()

    def write(self, line1: str, line2: str = ""):
        self.lcd.clear()
        self.lcd.write_string(line1[:16])
        if line2:
            self.lcd.crlf()
            self.lcd.write_string(line2[:16])

    def clear(self):
        self.lcd.clear()
