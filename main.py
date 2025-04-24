from machine import Pin, I2C, PWM, RTC
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

    
class Motor:
    def __init__(self, en_pin, pin0, pin1):
       self.en_pin = PWM(en_pin);
       self.pin0 = pin0;
       self.pin1 = pin1;
       self.en_pin.freq(512)
       
    def drive(self, val): #1.0 full forward, -1.0 full backward, 0.0 off
        print("Motor drive {}".format(val))
        pwm = 0
        if (val >= 0):
            pwm = int(65536*val)
            self.pin0.low()
            self.pin1.high()
        else:
            pwm = int(-65536*val)
            self.pin1.low()
            self.pin0.high()
        
        self.en_pin.duty_u16(pwm)
    
class Buzzer:
    def __init__(self, buzzer_pin):
        self.pin = PWM(buzzer_pin)
        self.freq = 3000
        
    def set_freq(self, f):
        self.freq = f
        
    def on(self):
        print("buzzer on")
        self.pin.freq(self.freq)
        self.pin.duty_u16(int(0.5*65536))
    def off(self):
        print("buzzer off")
        self.pin.duty_u16(0)

class Ultrasonic:
    def __init__(self, trig_pin, ech_pin):
        self.trig = trig_pin
        self.echo = ech_pin;
        self.trig.low()
        
    def get_distance_cm(self):
        self.trig.low()
        utime.sleep_us(2)
        self.trig.high()
        utime.sleep_us(10)
        self.trig.low()
        while self.echo.value() == 0:
            start = utime.ticks_us()
        while self.echo.value() == 1:
            end = utime.ticks_us()
        duration = utime.ticks_diff(end, start)
        return duration / 58.0
    
class Buttons:
    def __init__(self, b0_pin, b1_pin, b2_pin):
        self.pins = [b0_pin, b1_pin, b2_pin]
        
    def is_button_pressed(self, button):
        return (self.pins[button].value() == 1)
    
    def any_pressed(self):
        return (self.is_button_pressed(0) or self.is_button_pressed(1) or self.is_button_pressed(2))
    
    def wait_for_input(self):
        pressed = [self.is_button_pressed(0), self.is_button_pressed(1), self.is_button_pressed(2)]
        while True:
            curr = [self.is_button_pressed(0), self.is_button_pressed(1), self.is_button_pressed(2)]
            for i in range(3):
                if (curr[i] == False and pressed[i] == True):
                    return i
        
            pressed = curr
            utime.sleep_ms(10)



def select_dialog(lcd, buttons, options):
    selected_option = 0
    while True:
        lcd.move_to(0, 0)
        lcd.clear()
        for i in range(len(options)):
            o = options[i]
            lcd.move_to(0, i)
            
            if (i == selected_option):
                lcd.putstr("->" + o)
            else:
                lcd.putstr("  " + o)
                
        input = buttons.wait_for_input()

        if (input == 0):
            return options[selected_option]
        elif (input == 1):
            selected_option = (selected_option-1) % len(options)
        elif (input == 2):
            selected_option = (selected_option+1) % len(options)
            

def time_dialog(lcd, buttons, hours, minutes, seconds, show_str = "", offset_x = 0, offset_y = 0):
    numbers = [hours, minutes, seconds]
    numbers_mod = [24, 60, 60]
    selected_number = 0
    
    while True:
        lcd.clear()
        lcd.move_to(offset_x, offset_y)
        lcd.putstr("{}{:02d}:{:02d}:{:02d}".format(show_str, numbers[0], numbers[1], numbers[2]))
        lcd.move_to(offset_x+len(show_str), offset_y+1)
        lcd.putstr("   "*selected_number + "^^")
        
        input = buttons.wait_for_input()

        if (input == 0):
            selected_number += 1
            if (selected_number > 2):
                return (numbers[0], numbers[1], numbers[2])
        elif (input == 1):
            numbers[selected_number] = (numbers[selected_number]-1) % numbers_mod[selected_number];
        elif (input == 2):
            numbers[selected_number] = (numbers[selected_number]+1) % numbers_mod[selected_number];


def get_clock(rtc):
    year, month, day, weekday, hours, minutes, seconds = rtc.get_time()
    return (hours, minutes, seconds)

def set_clock(rtc, new_hours, new_minutes, new_seconds):
    year, month, day, weekday, hours, minutes, seconds = rtc.get_time()
    rtc.set_time(year, month, day, weekday, new_hours, new_minutes, new_seconds)

    

def alarm_action(lcd, buttons, buzzer, motor0, motor1, sonic):
    while (not buttons.any_pressed()):
        #there buzzer, motor control etc.
        
        utime.sleep_ms(10)
        pass
    
    while (buttons.any_pressed()):
        utime.sleep_ms(10)
        
        

def main():
    
    i2c = I2C(0, scl=machine.Pin(17), sda=machine.Pin(16))
    lcd = LCD(rs=2, en=3, d4=4, d5=5, d6=6, d7=7)
    buttons = Buttons(machine.Pin(9, Pin.IN), machine.Pin(8, Pin.IN), machine.Pin(7, Pin.IN))
    
    motor0 = Motor(machine.Pin(13), machine.Pin(12, Pin.OUT), machine.Pin(11, Pin.OUT))
    motor1 = Motor(machine.Pin(18), machine.Pin(19, Pin.OUT), machine.Pin(20, Pin.OUT))
    
    buzzer = Buzzer(machine.Pin(6, Pin.OUT))
    sonic = Ultrasonic(machine.Pin(15, Pin.OUT), machine.Pin(14, Pin.IN))
    
    rtc = RTC(i2c)
        
    alarm_enabled = False
    alarm_hours, alarm_minutes, alarm_seconds = (0, 0, 0)
    
    prev_time = (0, 0, 0)
    
    while True:
        hours, minutes, seconds = get_clock(rtc)
        needs_redraw = False
        
        if (buttons.any_pressed()):
            buttons.wait_for_input()
            choice = select_dialog(lcd, buttons, ["set alarm", "disable alarm", "set time", "exit"])
            if (choice == "set time"):
                hours, minutes, seconds = time_dialog(lcd, buttons, hours, minutes, seconds, show_str="Set time: ")
                set_clock(rtc, hours, minutes, seconds)
                
            elif (choice == "disable alarm"):
                alarm_enabled = False
                
            elif (choice == "set alarm"):
                if (not alarm_enabled):
                    alarm_hours, alarm_minutes, alarm_seconds = (hours, minutes, seconds)
        
                alarm_hours, alarm_minutes, alarm_seconds = time_dialog(lcd, buttons, alarm_hours, alarm_minutes, alarm_seconds, show_str="Set alarm: ")
                alarm_enabled = True
                
            needs_redraw = True
                
        if (prev_time != (hours, minutes, seconds)):
            prev_time = (hours, minutes, seconds)
            needs_redraw = True
    
        if (needs_redraw):
            lcd.clear()
            lcd.move_to(0, 0)
            lcd.putstr("Time:  {:02d}:{:02d}:{:02d}".format(hours, minutes, seconds))
            if (alarm_enabled):
                lcd.move_to(0, 1)
                lcd.putstr("Alarm: {:02d}:{:02d}:{:02d}".format(alarm_hours, alarm_minutes, alarm_seconds))
            
        if alarm_enabled and (hours, minutes, seconds) == (alarm_hours, alarm_minutes, alarm_seconds):
            alarm_action(lcd, buttons, buzzer, motor0, motor1, sonic);
            alarm_enabled = False  
        utime.sleep_ms(10)
        
        
if __name__ == "__main__":
    main()
