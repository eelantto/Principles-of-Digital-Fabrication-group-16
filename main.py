from machine import Pin, I2C, PWM, RTC
import utime
import random

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
            utime.sleep_us(10)
            
        utime.sleep_ms(2)

    def move_to(self, col, row):
        addr_begin = [0, 64, 20, 84] 
        addr = 0x80 + addr_begin[row] + col
        self.cmd(addr)

    def clear(self):
        self.cmd(0x01)
        utime.sleep_ms(2)

    def putstr(self, s):
        for c in s:
            self.cmd(ord(c), 1)

#We couldn't use DS1307 RTC module, because its supply voltage is 4.5-5.5v and its SDA and SCL has 10k pull-ups to Vcc.
#Without physical modification to module, its not safe to use with Picos 3.3v GPIO.
#class RTC:
#    def __init__(self, i2c, addr=0x68):
#        self.i2c = i2c
#        self.addr = addr

#    def _bcd2dec(self, bcd):
#        return (bcd >> 4) * 10 + (bcd & 0x0F)

#    def _dec2bcd(self, dec):
#        return ((dec // 10) << 4) + (dec % 10)

#    def get_time(self):
#        raw = self.i2c.readfrom_mem(self.addr, 0x00, 7)
#        seconds = self._bcd2dec(raw[0] & 0x7F)
#        minutes = self._bcd2dec(raw[1])
#        hours = self._bcd2dec(raw[2])
#        weekday = self._bcd2dec(raw[3])
#        day = self._bcd2dec(raw[4])
#        month = self._bcd2dec(raw[5])
#        year = self._bcd2dec(raw[6])
#        return year, month, day, weekday, hours, minutes, seconds


#    def set_time(self, year, month, day, weekday, hours, minutes, seconds):
#        year_short = year % 100
#        self.i2c.writeto_mem(self.addr, 0x00, bytes([
#            self._dec2bcd(seconds),
#            self._dec2bcd(minutes),
#            self._dec2bcd(hours),
#            self._dec2bcd(weekday),
#            self._dec2bcd(day),
#            self._dec2bcd(month),
#            self._dec2bcd(year_short)
#        ]))

    
class Motor:
    def __init__(self, en_pin, pin0, pin1):
       self.en_pin = PWM(en_pin)
       self.pin0 = pin0
       self.pin1 = pin1
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
        timeout = utime.ticks_us()
        
        self.trig.low()
        utime.sleep_us(5)
        self.trig.high()
        utime.sleep_us(20)
        self.trig.low()
        while self.echo.value() == 0:
            start = utime.ticks_us()
            if (utime.ticks_diff(start, timeout) > 100000):
                return -1
        while self.echo.value() == 1:
            end = utime.ticks_us()
            if (utime.ticks_diff(end, timeout) > 100000):
                return -1
            
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
     year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
     return (hours, minutes, seconds)
 
def set_clock(rtc, new_hours, new_minutes, new_seconds):
     year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
     
     rtc.datetime((year, month, day, weekday, new_hours, new_minutes, new_seconds, subseconds))


def alarm_action(lcd, buttons, buzzer, motor0, motor1, sonic):
     while (not buttons.any_pressed()):
         #there buzzer, motor control etc.
         
         utime.sleep_ms(10)
         pass
     
     while (buttons.any_pressed()):
         utime.sleep_ms(10)
        

def main():
    
    i2c = I2C(0, scl=machine.Pin(17), sda=machine.Pin(16))
    lcd = LCD(i2c, 0x27, 4, 20)
    buttons = Buttons(machine.Pin(9, Pin.IN), machine.Pin(8, Pin.IN), machine.Pin(7, Pin.IN))
    
    motor0 = Motor(machine.Pin(13), machine.Pin(12, Pin.OUT), machine.Pin(11, Pin.OUT))
    motor1 = Motor(machine.Pin(18), machine.Pin(19, Pin.OUT), machine.Pin(20, Pin.OUT))
    
    buzzer = Buzzer(machine.Pin(6, Pin.OUT))
    sonic = Ultrasonic(machine.Pin(15, Pin.OUT), machine.Pin(14, Pin.IN))
    
    rtc = machine.RTC()
        
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
