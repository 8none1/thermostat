#!/usr/bin/python

# Seperate file to hold all of the switching GPIO logic


import RPi.GPIO as GPIO
from RPIO import PWM
from subprocess import call

CODE_LOOKUP = {'1':"0FFF", '2':"F0FF", '3':"FF0F", '4':"FFF0", 'on':"FF", 'off':"F0"}

GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)

DEBUG=True
TESTING = False


def log(message):
  if DEBUG:
    print (message)


class backlight(object):
    def __init__(self, gpio):
        self.gpio = gpio
        if not PWM.is_setup():
          PWM.setup()
        if not PWM.is_channel_initialized(0):
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
    def close_cleanly(self):
        PWM.clear_channel_gpio(0,self.gpio)
        PWM.cleanup()
 
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
  def close_cleanly(self):
      GPIO.cleanup()


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


class txPower(object):
  def __init__(self,gpio):
    self.gpio = gpio
    GPIO.setup(self.gpio, GPIO.OUT, initial=False)
  def on(self):
    print "Power on Transmitter"
    GPIO.output(self.gpio, True)
  def off(self):
    print "Power off transmitter"
    GPIO.output(self.gpio, False)


def build_bits(group=1, rxer=1, state="on"):
  '''Pass in group number (1->4), rx number (1->4), and state as "on"  or "off"'''
  bits = ""
  bits += CODE_LOOKUP[group]
  bits += CODE_LOOKUP[rxer]
  bits += "FF" # unused
  bits += CODE_LOOKUP[state]
  bits += "S"
  log(bits)
  return bits


def send_code(txpwr, bits):
  txpwr.on()
  # sendTriState is from https://github.com/thjm/rcswitch-pi
  # I've changed sendTriState a little bit to add a wait while the tx settles, and
  # then just to send the codes a few times to make sure.
  status = call(["/home/pi/source/rcswitch-pi/sendTriState", bits])
  #Popen(["/home/pi/source/rcswitch-pi/sendTriState", bits]) # Actaully, this won't work, we need to block
  #otherwise the power gets turned off before the send has happened :)
  # Really though, this needs to be turned in to a web service so that general things can use it
  # TODO:  Turn sending the codes in to a web service.
  txpwr.off()




