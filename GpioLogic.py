#!/usr/bin/python

# Seperate file to hold all of the switching GPIO logic


import RPi.GPIO as GPIO
from RPIO import PWM

GPIO.setmode(GPIO.BCM)
DEBUG=True
TESTING = False
def log(message):
  if DEBUG:
    print (message)


class backlight(object):
    def __init__(self, gpio):
        self.gpio = gpio
        PWM.setup()
        PWM.init_channel(0,10000) # 100 Hz?
        PWM.add_channel_pulse(0,self.gpio, 0, 990)
        self.state = "full"
    def full(self):
        if self.state != "full":
          PWM.add_channel_pulse(0,self.gpio, 0, 990)
          self.state="full"
    def off(self):
        if self.state != "off":
            PWM.add_channel_pulse(0,self.gpio, 0, 0)
            self.state = "off"
    def low(self):
        if self.state != "low":
            PWM.add_channel_pulse(0,self.gpio, 0, 200)
            self.state = "low"
 
class basicRelay(object):
  def __init__(self, relay_gpio, common_name="Undefined Relay"):
    self.relay_gpio = relay_gpio
    self.name = common_name
    self.enabled = True
    GPIO.setup(self.relay_gpio, GPIO.OUT, initial=True)
  def on(self):
    if TESTING == True:
      log("TEST:  Would be turning on "+self.name)
      return True
    if self.enabled == True:
      GPIO.output(self.relay_gpio, False)
      return True
    else:  return False
  def off(self):
    if TESTING == True:
      log("TEST: Would be turning off "+self.name) 
      return True
    GPIO.output(self.relay_gpio, True)
    return True
  def get_state(self):
    return not GPIO.input(self.relay_gpio)
  def toggle(self):
    current = self.get_state()
    if current == True:
      self.off()
    else:
      self.on()


def get_room_temp(device):
    path="/sys/bus/w1/devices/"
    reading="w1_slave"
    tdevice=path+device+"/"+reading
    try:
        tfile=open(tdevice)
        text=tfile.read()
        tfile.close()
        second=text.split("\n")[1]
        tempdata=second.split(" ")[9]
        log(str(float(tempdata[2:])/1000))
        temperature = float(tempdata[2:])/1000
        return temperature
    except:
        return False




