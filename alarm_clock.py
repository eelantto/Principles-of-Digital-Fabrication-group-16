from machine import Pin, I2C, PWM
import utime

# LCD
class LCD:
    def __init__(self, i2c, addr, rows, cols):
        self.i2c = i2c
        self.addr = addr
        self.rows = rows
        self.cols = cols
        self.init()
    
    def init(self):
        for cmd in [0x33, 0x32, 0x28, 0x0C, 0x06, 0x01]:
            self.cmd(cmd)
            utime.sleep_ms(2)
    
    def cmd(self, cmd, mode=0):
        high = mode | (cmd & 0xF0) | 0x08
        low = mode | ((cmd << 4) & 0xF0) | 0x08
        for val in [high | 4, high, low | 4, low]:
            self.i2c.writeto(self.addr, bytes([val]))
        
        utime.sleep_us(50)

    def move_to(self, col, row):
        addr_begin = [0, 64, 20, 84] #I have no idea where these come from, but these works with 4x20 display
        addr = 0x80 + addr_begin[row] + col
        self.cmd(addr)

    def clear(self):
        self.cmd(0x01)
        utime.sleep_ms(2)

    def putstr(self, s):
        for c in s:
            self.cmd(ord(c), 1)

#RTC
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
lcd = LCD(i2c, 0x27, 4, 20)
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
