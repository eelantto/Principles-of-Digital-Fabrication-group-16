from machine import Pin, I2C, PWM
import utime

class LCD:
    def __init__(self, rs, en, d4, d5, d6, d7):
        self.rs = Pin(rs, Pin.OUT)
        self.en = Pin(en, Pin.OUT)
        self.data_pins = [Pin(d4, Pin.OUT), Pin(d5, Pin.OUT),
                          Pin(d6, Pin.OUT), Pin(d7, Pin.OUT)]
        self.init()

    def pulse_enable(self):
        self.en.low()
        utime.sleep_us(1)
        self.en.high()
        utime.sleep_us(1)
        self.en.low()
        utime.sleep_us(100)

    def send(self, data, rs_mode):
        self.rs.value(rs_mode)
        for i in range(4):
            self.data_pins[i].value((data >> (4 + i)) & 0x01)
        self.pulse_enable()
        for i in range(4):
            self.data_pins[i].value((data >> i) & 0x01)
        self.pulse_enable()

    def cmd(self, data):
        self.send(data, 0)

    def putstr(self, s):
        for c in s:
            self.send(ord(c), 1)

    def clear(self):
        self.cmd(0x01)
        utime.sleep_ms(2)

    def move_to(self, col, row):
        row_offsets = [0x00, 0x40]
        self.cmd(0x80 | (col + row_offsets[row]))

    def init(self):
        utime.sleep_ms(50)
        self.send(0x33, 0)
        self.send(0x32, 0)
        self.send(0x28, 0)
        self.send(0x0C, 0)
        self.send(0x06, 0)
        self.clear()


class RTC:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr

    def _bcd2dec(self, bcd):
        return (bcd >> 4) * 10 + (bcd & 0x0F)

    def _dec2bcd(self, dec):
        return ((dec // 10) << 4) + (dec % 10)

    def get_time(self):
        raw = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        seconds = self._bcd2dec(raw[0] & 0x7F)
        minutes = self._bcd2dec(raw[1])
        hours = self._bcd2dec(raw[2])
        weekday = self._bcd2dec(raw[3])
        day = self._bcd2dec(raw[4])
        month = self._bcd2dec(raw[5])
        year = self._bcd2dec(raw[6])  
        return year, month, day, weekday, hours, minutes, seconds

    def set_time(self, year, month, day, weekday, hours, minutes, seconds):
        year_short = year % 100
        self.i2c.writeto_mem(self.addr, 0x00, bytes([
            self._dec2bcd(seconds),
            self._dec2bcd(minutes),
            self._dec2bcd(hours),
            self._dec2bcd(weekday),
            self._dec2bcd(day),
            self._dec2bcd(month),
            self._dec2bcd(year_short)
        ]))

    
# Measuring distance (by using ultrasonic sensor)
def get_distance_cm():
    trig.low()
    utime.sleep_us(2)
    trig.high()
    utime.sleep_us(10)
    trig.low()
    while echo.value() == 0:
        start = utime.ticks_us()
    while echo.value() == 1:
        end = utime.ticks_us()
    duration = utime.ticks_diff(end, start)
    return duration / 58.0


i2c = I2C(0, scl=Pin(1), sda=Pin(0))
lcd = LCD(rs=2, en=3, d4=4, d5=5, d6=6, d7=7)
rtc = RTC(i2c)


# Button
btn_hour = Pin(10, Pin.IN, Pin.PULL_UP)
btn_min = Pin(11, Pin.IN, Pin.PULL_UP)
btn_set = Pin(12, Pin.IN, Pin.PULL_UP)


# Motor and buzzer
buzzer = Pin(15, Pin.OUT)
motorA1 = Pin(8, Pin.OUT)
motorA2 = Pin(9, Pin.OUT)
servo1 = PWM(Pin(2))
servo2 = PWM(Pin(3))
servo1.freq(50)
servo2.freq(50)


# Ultrasonic Sensor
trig = Pin(4, Pin.OUT)
echo = Pin(5, Pin.IN)


def move_servo(angle):
    duty = int(((angle / 180) * 2 + 0.5) / 20 * 65535)
    servo1.duty_u16(duty)
    servo2.duty_u16(duty)

def start():
    motorA1.high()
    motorA2.low()
    buzzer.high()
    move_servo(90)

def stop():
    motorA1.low()
    motorA2.low()
    buzzer.low()
    move_servo(0)

def set_alarm():
    global alarm_hour, alarm_min, alarm_done
    while not alarm_done:
        if not btn_hour.value():
            alarm_hour = (alarm_hour + 1) % 24
            utime.sleep(0.2)
        if not btn_min.value():
            alarm_min = (alarm_min + 1) % 60
            utime.sleep(0.2)
        if not btn_set.value():
            alarm_done = True
            utime.sleep(0.2)
        lcd.move_to(0, 1)
        lcd.putstr(f"Set {alarm_hour:02}:{alarm_min:02}")
