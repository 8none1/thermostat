#!/usr/bin/python

import sys
import pygame
from pygame.locals import *
import time
import os
import array
import math
import cairo
import rsvg
import Image
from xml.dom import minidom
import requests
import json
import atexit
import re
import signal
import traceback
import datetime
import copy
import GpioLogic
import io
from urllib2 import urlopen

DEBUG = True
TESTING = True
FAST_RENDERING = True

#  UPDATE:  Looks like a proper fix was merged on 2015-05-14 so this patch
#  isn't needed anymore.  But you stil have to pull the version from Git and
#  build it I think.
#  We use the PWM code from RPIO (https://github.com/metachris/RPIO)
#  because it has a much better PWM implentation (or at least it had
#  at the time of writing.  But, there is a "bug" in the PWM code
#  which means it terminates on *any* signal, for example SIGWINCH
#  when the terminal resizes.  This patch "fixes" it for SIGWINCH:
#"""
#*** RPIO/source/c_pwm/pwm.c     2015-02-15 13:08:36.278338553 +0000
#--- RPIO-mine/source/c_pwm/pwm.c        2015-02-15 10:24:53.836897585 +0000
#*************** setup_sighandlers(void)
#*** 338,343 ****
#--- 338,344 ----
#  {
#      int i;
#      for (i = 0; i < 64; i++) {
#+         if (i == 28) continue;
#          struct sigaction sa;
#          memset(&sa, 0, sizeof(sa));
#          sa.sa_handler = (void *) terminate;
#"""

# Basically it doesnt react to sig 28, which is SIGWINCH.
# It's a hack, but it works for me.




os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Set up Pygame stuff
#pygame.init()
pygame.font.init()
pygame.display.init()
pygame.mouse.set_visible(False)
default_fontstyle = "none"
#default_fontname = pygame.font.match_font(default_fontstyle)
default_fontname = None
size = screen_width, screen_height = 480, 320
screen = pygame.display.set_mode(size)
screen.fill((255,255,255))
pygame.display.flip()
pygame.event.pump()

#define colours
blue = 0, 0, 255
cream = 254, 255, 250
black = 0, 0, 0
white = 255, 255, 255
red = 255,0,0
green = 0,255,0
dk_grey = 160,160,160
wall_col = 201,155,92


# Set up user events and associated bits - can only have 9
TICK1M = USEREVENT+1
BUTTONHIGHLIGHT = USEREVENT+2
TICK15M = USEREVENT+3
IDLETIMEOUT = USEREVENT+4
TICK10SEC = USEREVENT+5

# Other globals
BUTTON_ACTION_LIST = []
BUTTON_LIST = []
IDLE_LIST = []
SCRAP = 1
STAT_TEMPERATURE = 20
MAIN_STAT_GOAL = 21
BACKGROUND_COLOUR = wall_col
HEATING = False
HOTWATER = False
ALL_ONSCREEN_OBJECTS = []
WEATHER_VISIBLE = True
CLOCK_STYLE = True
SAT_IMAGE = ""
wdict = []

thermostat_relay = GpioLogic.basicRelay(17, "Thermostat")
top_data = mid_data = btm_data = 0


class bcolours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BOLD = '\033[1m'


def log(message, col=None):
  if DEBUG:
    if col is not None and message is not None:
      print col + message + bcolours.ENDC
    elif col is None and message is not None:
      print message
    else:
      print "Something happened"
      return

def exit_handler(signal, frame):
    log("Tidying up...")
    backlight_control.close_cleanly()
    thermostat_relay.close_cleanly()
    pygame.quit()
    sys.exit(0)

def grid():
    if TESTING:
        for x in range(0,screen_width,10):
            if x % 2 == 0: col = red
            else: col = blue
            pygame.draw.line(screen,col,(x,0),(x,screen_height))
        for y in range(0,screen_height,10):
            if y % 2 == 0: col = red
            else: col = black
            pygame.draw.line(screen,col,(0,y),(screen_width,y))
        pygame.display.flip()
        
################################################################################
##  WEATHER STUFF 
################################################################################

import metoffer
# create a file called weather_api.txt and add your api key to it on a line
# of it's own
with open('weather_api.txt') as f:
  lines = f.readlines()
for each in lines:
  if each[0] == "#": continue
  elif len(each) < 34: continue
  else:
    weather_api_key = each
    break

weather_location = "353363" # Sandy
METDATA = metoffer.MetOffer(weather_api_key)

weather_dict = {}
weather_today_day =      {}
weather_today_night =    {}
weather_tomorrow_day =   {}
weather_tomorrow_night = {}


WEATHER_CODES_DAY = {"NA": "Not available",
                 0: ["Clear night","Moon.svg"],
                 1: ["Sunny day", "Sun.svg"],
                 2: ["Partly cloudy (night)","Cloud-Moon.svg"],
                 3: ["Partly cloudy (day)","Cloud-Sun.svg"],
                 4: ["Not used"],
                 5: ["Mist","Cloud-Fog-Alt.svg"],
                 6: ["Fog","Cloud-Fog.svg"],
                 7: ["Cloudy","Cloud.svg"],
                 8: ["Overcast","Cloud.svg"],
                 9: ["Light rain shower (night)","Cloud-Drizzle-Moon-Alt.svg"],
                 10: ["Light rain shower (day)","Cloud-Drizzle-Alt.svg"],
                 11: ["Drizzle","Cloud-Drizzle-Alt.svg"],
                 12: ["Light rain","Cloud-Drizzle.svg"],
                 13: ["Heavy rain shower (night)","Cloud-Rain-Moon.svg"],
                 14: ["Heavy rain shower (day)","Cloud-Rain.svg"],
                 15: ["Heavy rain","Cloud-Rain.svg"],
                 16: ["Sleet shower (night)","Cloud-Snow-Moon.svg"],
                 17: ["Sleet shower (day)","Cloud-Snow.svg"],
                 18: ["Sleet","Cloud-Snow.svg"],
                 19: ["Hail shower (night)","Cloud-Hail-Moon.svg"],
                 20: ["Hail shower (day)","Cloud-Hail-Alt.svg"],
                 21: ["Hail","Cloud-Hail-Alt.svg"],
                 22: ["Light snow shower (night)","Cloud-Snow-Moon.svg"],
                 23: ["Light snow shower (day)","Cloud-Snow.svg"],
                 24: ["Light snow","Cloud-Snow.svg"],
                 25: ["Heavy snow shower (night)","Cloud-Snow-Moon.svg"],
                 26: ["Heavy snow shower (day)","Cloud-Snow.svg"],
                 27: ["Heavy snow","Cloud-Snow.svg"],
                 28: ["Thunder shower (night)","Cloud-Lightning-Moon.svg"],
                 29: ["Thunder shower (day)","Cloud-Lightning.svg"],
                 30: ["Thunder","Cloud-Lightning.svg"]}

WEATHER_CODES_NIGHT = {"NA": "Not available",
                 0: ["Clear night","Moon.svg"],
                 1: ["Sunny day", "Sun.svg"],
                 2: ["Partly cloudy (night)","Cloud-Moon.svg"],
                 3: ["Partly cloudy (day)","Cloud-Sun.svg"],
                 4: ["Not used"],
                 5: ["Mist","Cloud-Fog-Alt.svg"],
                 6: ["Fog","Cloud-Fog.svg"],
                 7: ["Cloudy","Cloud-Moon.svg"],
                 8: ["Overcast","Cloud-Moon.svg"],
                 9: ["Light rain shower (night)","Cloud-Drizzle-Moon-Alt.svg"],
                 10: ["Light rain shower (day)","Cloud-Drizzle-Alt.svg"],
                 11: ["Drizzle","Cloud-Drizzle-Alt.svg"],
                 12: ["Light rain","Cloud-Drizzle-Moon.svg"],
                 13: ["Heavy rain shower (night)","Cloud-Rain-Moon.svg"],
                 14: ["Heavy rain shower (day)","Cloud-Rain.svg"],
                 15: ["Heavy rain","Cloud-Rain-Moon.svg"],
                 16: ["Sleet shower (night)","Cloud-Snow-Moon.svg"],
                 17: ["Sleet shower (day)","Cloud-Snow.svg"],
                 18: ["Sleet","Cloud-Snow-Moon.svg"],
                 19: ["Hail shower (night)","Cloud-Hail-Moon.svg"],
                 20: ["Hail shower (day)","Cloud-Hail-Alt.svg"],
                 21: ["Hail","Cloud-Hail-Alt.svg"],
                 22: ["Light snow shower (night)","Cloud-Snow-Moon.svg"],
                 23: ["Light snow shower (day)","Cloud-Snow.svg"],
                 24: ["Light snow","Cloud-Snow.svg"],
                 25: ["Heavy snow shower (night)","Cloud-Snow-Moon.svg"],
                 26: ["Heavy snow shower (day)","Cloud-Snow.svg"],
                 27: ["Heavy snow","Cloud-Snow.svg"],
                 28: ["Thunder shower (night)","Cloud-Lightning-Moon.svg"],
                 29: ["Thunder shower (day)","Cloud-Lightning.svg"],
                 30: ["Thunder","Cloud-Lightning.svg"]}


def aspect_scale(img,(bx,by)):
    # http://www.pygame.org/pcr/transform_scale/
    """ Scales 'img' to fit into box bx/by.
     This method will retain the original image's aspect ratio """
    ix,iy = img.get_size()
    if ix > iy:
        # fit to width
        scale_factor = bx/float(ix)
        sy = scale_factor * iy
        if sy > by:
            scale_factor = by/float(iy)
            sx = scale_factor * ix
            sy = by
        else:
            sx = bx
    else:
        # fit to height
        scale_factor = by/float(iy)
        sx = scale_factor * ix
        if sx > bx:
            scale_factor = bx/float(ix)
            sx = bx
            sy = scale_factor * iy
        else:
            sy = by

    return pygame.transform.scale(img, (int(sx),int(sy)))

def get_outside_temp():
    resp = requests.get(url="http://calculon/home/current_temperature.py?basic=true")
    data = json.loads(resp.content)
    return int(data['rows'][0]['c'][0]['v'])

class weatherIcon(object):
    def __init__(self,period, day, wtype, windspeed, winddir, temp, pp, uv=0, scale=1, subscale=1):
        self.period = period
        self.dow = day
        self.wtype = wtype
        self.scale = scale
        self.subscale = subscale
        self.visible = True
        self.start_hidden = False
        self.kind = "WEATHER_ICON"
        if self.period == "Day":
            self.icon = WEATHER_CODES_DAY[self.wtype][1]
            self.wdesc = WEATHER_CODES_DAY[self.wtype][0]
        else:
            self.icon = WEATHER_CODES_NIGHT[self.wtype][1]
            self.wdesc = WEATHER_CODES_NIGHT[self.wtype][0]
        self.windspeed = windspeed
        self.winddir = winddir
        self.temp = temp
        self.pp = pp
        self.uv = uv
        self.subicons = []
        if self.pp > 60:
            self.pp_icon = svg_image("icons/Umbrella.svg",0,0,self.subscale)
            self.subicons.append(self.pp_icon)
        if self.windspeed > 25:
            self.wind_icon = svg_image("icons/Wind.svg",0,0,self.subscale)
            self.subicons.append(self.wind_icon)
        if self.temp < 5:
            self.ice_icon = svg_image("icons/Snowflake.svg",0,0,self.subscale)
            self.subicons.append(self.ice_icon)
        if self.uv > 5: #maybe 4 - http://www.metoffice.gov.uk/guide/weather/symbols#solar-uv-symbols
            self.shades = svg_image("icons/Shades.svg",0,0,self.subscale)
            self.subicons.append(self.shades)
        
        #print "==============================="
        #print "XXXXXX Weather Object:"
        #print "Day:"
        #print self.dow
        #print "Type:"
        #print self.wtype
        #print "Desc:"
        #print self.wdesc
        #print "Icon:"
        #print self.icon
        #print "Wind Speed:"
        #print self.windspeed
        #print "Wind Dir:"
        #print self.winddir
        #print "Temperature:"
        #print self.temp
        #print "Chance of rain:"
        #print self.pp
        #print "UV Index:"
        #print self.uv
        #print "------------------------------------"
        #     def __init__(self, filename,x,y, scale=1.0, visible=False):
        self.image = svg_image("icons/"+self.icon, 0, 0,self.scale)
    def draw(self, fast=None):
        # Don't support fast drawing at the moment because of the sub icons
        if False == self.visible:  return
        self.image.draw()
        for each in self.subicons:
            each.draw()
    def hide(self, fast=None):
        self.image.hide()
        self.visible = False
        for each in self.subicons:
            self.visible = False
            each.hide()            

def update_daily_weather():
    if False == WEATHER_VISIBLE: return
    global wdict, outttext
    wdict = []
    icon_list = []
    try:
        x = METDATA.loc_forecast(weather_location, metoffer.DAILY)
        weather = metoffer.parse_val(x)
    except:
        print "Couldn't parse weather data."
        return 
    # Things to care about:
    # "timestamp"[0] = datetime / timestamp[1] = period [Day|Night]
    # "Wind Speed"[0] = speed in mph
    # "Wind Direction"[0] = N, S, E, W, SSW, NE etc
    # "Feels Like Night Minimum Temperature"[0] = int
    # "Feels Like Day Maximum Temperature"[0] = int
    # DAY - "Max UV Index"[0] = int
    # "Weather Type"[0] = int, look up against METOFFER.WEATHER_CODES
    # DAY - "Precipitation Probabiliy Day"[0] = int %
    # NIGHT - "Precipitation Probabilty Night"[0] = int %
    #### (self,period, day,wtype, windspeed, winddir, temp, pp, uv=0, scale=1, subscale=1)
    for each in weather.data:
        day = time.strftime('%a',each['timestamp'][0].timetuple())
        if each['timestamp'][1] == "Day":
            wdict.append(weatherIcon(each['timestamp'][1],day,each['Weather Type'][0], each['Wind Speed'][0], each['Wind Direction'][0], each['Feels Like Day Maximum Temperature'][0], each['Precipitation Probability Day'][0], each['Max UV Index'][0],1,0.3))
        elif each['timestamp'][1] == "Night":
            wdict.append(weatherIcon(each['timestamp'][1],day,each['Weather Type'][0], each['Wind Speed'][0], each['Wind Direction'][0], each['Feels Like Night Minimum Temperature'][0], each['Precipitation Probability Night'][0],0,1,0.3))

    x = 2
    first = True
    now = time.localtime().tm_hour
    if now > 17:
        wdict = wdict[1:]
    blank_rect = pygame.Rect(0,0,screen_width, 80) # daily weather icons
    pygame.draw.rect(screen, BACKGROUND_COLOUR, blank_rect)
    blank_rect = pygame.Rect(0,80,160, 190) # current weather
    pygame.draw.rect(screen, BACKGROUND_COLOUR, blank_rect)
    
    for each in wdict[:8]:
        if first:
            first = False
            each.image = svg_image("icons/"+each.icon, 20, 80,2.5)
            icon_list.append(each.image.draw(fast=FAST_RENDERING))
            each.subicons = []
            x = 5# outttext.rect.x
            y = 210# outttext.rect.top-15
            if each.pp > 60:
                each.pp_icon = svg_image("icons/Umbrella.svg",x,y,1)
                each.subicons.append(each.pp_icon)
            if each.windspeed > 25:
                each.wind_icon = svg_image("icons/Wind.svg",x,y,1)
                each.subicons.append(each.wind_icon)
            if each.temp < 5:
                each.ice_icon = svg_image("icons/Snowflake.svg",x,y,1)
                each.subicons.append(each.ice_icon)
            if each.uv > 5: #maybe 4 - http://www.metoffice.gov.uk/guide/weather/symbols#solar-uv-symbols
                each.shades = svg_image("icons/Shades.svg",x,y,1)
                each.subicons.append(each.shades)
            for thing in each.subicons:
                thing.x = x
                x += 55
                icon_list.append(thing.draw(fast=FAST_RENDERING))
            x = 2
        else:
            each.image.x = x
            icon_list.append(each.image.draw(fast=FAST_RENDERING))
            string = each.dow + ": "+str(each.temp)+u'\N{DEGREE SIGN}'
            each.text = TextArea(each.image.rect.centerx,each.image.rect.bottom+5,19,black,BACKGROUND_COLOUR,string)        
            each.subicons.append(each.text)
            n = x
            for thing in each.subicons:
                if thing.kind == "TEXT": pass
                else:
                    thing.x = n
                    thing.y = each.image.y + 65
                    n += 15
                icon_list.append(thing.draw(fast=FAST_RENDERING))
            # class TextArea:
            #init__(self, x,y,size,colour,bgcol=None,string="",font=default_fontstyle):
            x += 60

    outtemp = get_outside_temp()
    outttext = TextArea(100, 243, 70, black, BACKGROUND_COLOUR, str(outtemp)+u'\N{DEGREE SIGN}')  
    if True == FAST_RENDERING:
        icon_list.append(outttext.draw(fast=FAST_RENDERING))      
    else:
        outttext.draw()

    if True == FAST_RENDERING:
      pygame.display.update(icon_list)

current_map_time = None

def update_sat_image():
    global current_map_time, SAT_IMAGE
    x = METDATA.map_overlay_obs()
    base_url = x['Layers']['BaseUrl']['$']
    # http://datapoint.metoffice.gov.uk/public/data/layer/wxobs/{LayerName}/{ImageFormat}?TIME={Time}Z&key={key}
    
    found = False
    for each in x['Layers']['Layer']:
      if each.values()[0] == "SatelliteVis":
        found = True
        break
    if True == found:
        layer_name = each['Service']['LayerName']
        img_fmt = each['Service']['ImageFormat']
        latest_map_time = each['Service']['Times']['Time'][0] # Assuming first is most recent
        if latest_map_time == current_map_time:  return
        else: current_map_time = latest_map_time
        base_url = base_url.split("{LayerName}")
        base_url = base_url[0]+layer_name+base_url[1]
        base_url = base_url.split("{ImageFormat}")
        base_url = base_url[0]+img_fmt+base_url[1]
        base_url = base_url.split("{Time}")
        base_url = base_url[0]+latest_map_time+base_url[1]
        base_url = base_url.split("{key}")
        base_url = base_url[0]+weather_api_key+base_url[1]
        image_str = urlopen(base_url).read()
        image_file = io.BytesIO(image_str)
        image = pygame.image.load(image_file)
        SAT_IMAGE = aspect_scale(image, (screen_width, screen_height))
        #screen.blit(image, (0,0))
        #pygame.display.flip()
        
    else:
        print "Couldn't get sat images."
        return    
        
def draw_sat_image():
    rect = screen.blit(SAT_IMAGE, (100,0))
    pygame.display.update(rect)

    
        
    
    
################################################################################
##                             END  WEATHER STUFF                             ##
################################################################################

pygame.event.pump()

################################################################################
##              IMAGE STUFF
################################################################################

class svg_image(object):
    def __init__(self, filename,x,y, scale=1.0, visible=False, clickable=False):
        self.x = x
        self.y = y
        self.filename = filename
        self.scale = scale
        self.visible=visible
        self.clickable = clickable
        self.start_hidden = False
        self.dom = minidom.parse(filename)
        self.index=0
        self.kind = "SVG"
        self.__actions = {}
        if True == self.clickable:
            BUTTON_LIST.append(self)        
        if scale is not 1.0:
            # Apply scaling here
            ori_w = self.dom.documentElement.getAttribute('width')
            ori_h = self.dom.documentElement.getAttribute('height')
            if type(ori_w) is not int:
                numbers = re.compile('\d+(?:\.\d+)?')
                ori_w = numbers.findall(ori_w)[0]
                ori_h = numbers.findall(ori_h)[0]
            ori_w = (float(ori_w) * scale)
            ori_h = (float(ori_h) * scale)
            self.dom.documentElement.setAttribute('width',str(ori_w))
            self.dom.documentElement.setAttribute('height', str(ori_h))
        self.svg = rsvg.Handle(data=self.dom.toxml())
        self.height = self.svg.get_property('height')
        self.width = self.svg.get_property('width')
        self.data = array.array('c', chr(0) * self.width * self.height * 4)
        self.surface = cairo.ImageSurface.create_for_data(self.data, 
          cairo.FORMAT_ARGB32, self.width, self.height, self.width * 4)
        self.context = cairo.Context(self.surface)
        self.render()
    def convert_cairo_to_pygame(self):
        img = Image.frombuffer(
            'RGBA', (self.surface.get_width(),
            self.surface.get_height()),
            self.surface.get_data(), 'raw', 'BGRA', 0 ,1)
        return img.tostring('raw','RGBA',0,1)
    def render(self):
        self.svg.render_cairo(self.context)
        data_string = self.convert_cairo_to_pygame()
        self.pygame_image = pygame.image.frombuffer(data_string, (self.width, self.height), 'RGBA')
    def update(self):
        self.svg = rsvg.Handle(data=self.dom.toxml())
        self.render()
    def draw(self, fast=False):
        if True == fast:
            self.rect = screen.blit(self.pygame_image, (self.x, self.y))
            return self.rect
        else:
            self.rect = screen.blit(self.pygame_image, (self.x, self.y))            
            pygame.display.update(self.rect)

    def hide(self):
        if True == self.visible:
            global BACKGROUND_COLOUR
            self.rect = pygame.draw.rect(screen, BACKGROUND_COLOUR, self.rect)
            pygame.display.update(self.rect)
            self.visible == False
    def pressed(self):
        self.execute_actions("clicked")
        BUTTON_ACTION_LIST.append(self)
        pygame.time.set_timer(BUTTONHIGHLIGHT,500)
    def released(self):
        self.execute_actions("released")
    def add_action(self, action_type, function, args=()):
        if action_type not in self.__actions:
            self.__actions[action_type] = []
        self.__actions[action_type].append((function, args))
    def execute_actions(self, action_type):
        try:
            for action,args in self.__actions.get(action_type, []):
                action(*args)
        except:
            raise

class PolyButton(object):
    def __init__(self,x,y,size,colour,inverted=False):
        self.x = x
        self.y = y
        self.size = size
        self.offset = self.size / 2
        self.colour = colour
        self.inverted = inverted
        self.ispressed = False
        self.visible = True
        self.start_hidden = False
        self.pcol = None
        self.index = 0
        self.kind = "POLYBUTTON"
        self.clickable = True
        self.__actions = {}
    def draw(self,draw_colour=None, fast=False):
        if self.visible == False: return
        if draw_colour == None: draw_colour=self.colour
        self.rect = pygame.draw.polygon(screen, draw_colour, self.pointlist)
	if True == fast:
	  # Idea - if we have a lot of things to update you set fast to True and rather than each object redrawing its area of the screen
	  # it passes back the rect which needs updating.  This is then put in a list and the calling function is responsible for calling
	  # display.update(the list of rects) which in theory is faster.
	  return self.rect
	else:	
          pygame.display.update(self.rect)
    def hide(self, fast=False):
        if True == self.visible:
            # Crude but will have to do - draw background over yourself
            global BACKGROUND_COLOUR
            self.rect = pygame.draw.polygon(screen, BACKGROUND_COLOUR, self.pointlist)
            self.visible = False
	    if True == fast:
	      return self.rect
 	    else:
              pygame.display.update(self.rect)
    def pressed(self):
        if True == self.ispressed: return
        if self.pcol is not None:
            self.draw(self.pcol)
        else:
            self.draw(green)
        BUTTON_ACTION_LIST.append(self)
        pygame.time.set_timer(BUTTONHIGHLIGHT,500) # Could just create a new one?  Try this anyway.
        self.ispressed=True
        self.execute_actions("clicked")  
    def released(self):
        self.draw()
        self.execute_actions("released")
        pygame.time.set_timer(BUTTONHIGHLIGHT,0)
        self.ispressed = False
        start_idle_timer(3000)
    def add_action(self, action_type, function, args=()):
        if action_type not in self.__actions:
            self.__actions[action_type] = []
        self.__actions[action_type].append((function, args))
    def execute_actions(self, action_type):
        for action, args in self.__actions.get(action_type, []):
            action(*args)

class Triangle(PolyButton):
    def __init__(self,x,y,size,colour, inverted=False):
        PolyButton.__init__(self, x,y,size,colour,inverted)
        self.kind = "TRIANGLE"
        if False == self.inverted:
            self.point1 = ((self.x - self.offset),self.y)
            self.point2 = (self.x, self.y-self.offset)
            self.point3 = ((self.x + self.offset), self.y)
        else:
            self.point1 = ((self.x - self.offset), self.y)
            self.point2 = ((self.x + self.offset), self.y)
            self.point3 = ((self.x, (self.y + self.offset)))
        self.pointlist = [self.point1, self.point2, self.point3]

class Rectangle(PolyButton):
    def __init__(self,x,y,size,colour):
        PolyButton.__init__(self, x,y,size,colour)
        self.colour = colour
        self.kind = "RECTANGLE"
        # Left, top, width, height
        self.point1 = self.x
        self.point2 = self.y
        self.point3 = (size)
        self.point4 = (size)
        self.borders = False
        self.size = size
        #self.pointlist = [self.point1, self.point2, self.point3, self.point4]
        self.rect = pygame.Rect(self.x, self.y, size*1.3, self.size)
    def draw(self, draw_colour = None, fast=False):
        if False == self.visible:  return
        if draw_colour == None:
            draw_colour=self.colour
        self.rect = pygame.draw.rect(screen, draw_colour, self.rect)
        if True == self.borders:
            lighter = ()
            darker = ()
            for each in self.colour:
              if each + 40 > 255:
                lighter = lighter + (255,)
              else:
                lighter = lighter + ((each+40),)
              if each - 40 < 0:
                darker = darker + (0,)
              else:
                darker = darker + ((each-40),)
            width = self.size*1.3
            height = self.size/10
            topb=(pygame.Rect(self.x, self.y, (self.rect.width-height), height))
            rightb=(pygame.Rect((self.x+self.rect.width)-height,self.y, height, self.rect.height))
            bottomb=(((self.rect.x+height),(self.y+self.rect.height)-height, self.rect.width-height, height))
            leftb=(self.x,self.y,height, self.rect.height)
            pygame.draw.rect(screen, lighter, topb)
            pygame.draw.rect(screen, darker, rightb)
            pygame.draw.rect(screen, darker, bottomb)
            pygame.draw.rect(screen, lighter, leftb)
        self.visible = True
	if True == fast:
		return self.rect
	else:
		pygame.display.update(self.rect)

        
class TextArea:
    def __init__(self, x,y,size,colour,bgcol=None,string="",font=default_fontstyle):
        self.x = x
        self.y = y
        self.size = size
        self.colour = colour
        self.string = string
        self.font = pygame.font.Font(pygame.font.match_font(font),size)
        self.ispressed = False
        self.visible = True
        self.start_hidden = False
        self.bgcol = bgcol
        self.rect = (0,0,0,0)
        self.kind = "TEXT"
        self.clickable = False
        #if True == self.clickable:  BUTTON_LIST.append(self)
        self.__actions = {}
    def draw(self, fast=False):
        if self.visible == False: return
        try:
            if self.rect:
                self.hide()
        except: pass
        self.output_size = self.font.size(self.string)    
        if self.bgcol is None:
            font_surface = self.font.render(self.string, 1, (self.colour))
        else:
            font_surface = self.font.render(self.string, 1, (self.colour), self.bgcol)
        render_x = self.x - (self.output_size[0]/2)
        render_y = self.y - (self.output_size[1]/2)
        self.rect = screen.blit(font_surface,(render_x,render_y))
        if True == fast:
          return self.rect
        else:
          pygame.display.update(self.rect)
    def hide(self):
        pygame.draw.rect(screen, BACKGROUND_COLOUR, self.rect)
        pygame.display.update(self.rect)
        #self.visible = False
    def pressed(self):
        self.execute_actions("clicked")
    def add_action(self, action_type, function, args=()):
        if action_type not in self.__actions:
            self.__actions[action_type] = []
        self.__actions[action_type].append((function, args))
    def execute_actions(self, action_type):
        try:
            for action,args in self.__actions.get(action_type, []):
                action(*args)
        except:
            #pass
            raise
      
class Bitmap(object):
        def __init__(self, filename,colour_key):
            self.x=0
            self.y=0
            self.visible=False
            self.start_hidden = True
            self.surface = pygame.image.load(filename)
            self.surface.set_colorkey(colour_key)
            self.surface = self.surface.convert()
            self.kind = "BITMAP"
        def draw(self):
            if False == self.visible:  return
            self.rect = screen.blit(self.surface, (self.x, self.y))
            pygame.display.update(self.rect)
        def hide(self):
            rect = pygame.draw.rect(screen, BACKGROUND_COLOUR, self.rect)
            pygame.display.update(rect)
            self.visible = False

class MenuScreen(object):
    def __init__(self, bgcol=BACKGROUND_COLOUR):
        self.visible = False
        self.objects = []
        self.kind = "SCREEN"
        self.name = "Unnamed"
        self.bgcol = bgcol
    def add(self, gfx_object):
        self.objects.append(gfx_object)
    def draw(self):
        print "Drawing: "+self.name
        global BUTTON_LIST
        BUTTON_LIST = []
        screen.fill(self.bgcol)
        self.visible = True
        for each in self.objects:
            if False == each.start_hidden:
                each.visible = True
            if True == each.clickable:
                BUTTON_LIST.append(each)
            a = each.draw(fast=True)
        pygame.display.flip()
    def hide(self):
        self.visible = False
        for each in self.objects:
            each.visible = False
            each.hide()
        pygame.display.flip()


################################################################################
############         END OF IMAGE STUFF            #############################
################################################################################

def adjust_therm_temp(adjustment,text_object):
    global STAT_TEMPERATURE
    global MAIN_STAT_GOAL
    if adjustment > 0 and MAIN_STAT_GOAL >= 30: return
    if adjustment < 0 and MAIN_STAT_GOAL <= 10: return
    MAIN_STAT_GOAL += adjustment
    text_object.string = str(MAIN_STAT_GOAL) + u'\N{DEGREE SIGN}'
    text_object.draw()

def start_idle_timer(ms):
    'In theory, this will reset the idle timeout to ms and remove the old time out from the queue'
    pygame.time.set_timer(IDLETIMEOUT, 0)
    pygame.time.set_timer(IDLETIMEOUT, ms)
    log('set idle timer to '+str(ms))

def edit_stat_goal(state):
    if True == state:
        temp_text.string = str(MAIN_STAT_GOAL) + u'\N{DEGREE SIGN}'
        temp_text.colour = red
        c=temp_text.draw(fast=FAST_RENDERING)
        uparrow.visible=True
        downarrow.visible=True
        a = uparrow.draw(fast=FAST_RENDERING)
        b = downarrow.draw(fast=FAST_RENDERING)
        pygame.display.update([c,a,b])
        start_idle_timer(3000)
        IDLE_LIST.append((edit_stat_goal,[False]))
    if False == state:
        # Done editing
        temp_text.colour = black
        temp_text.string = str(int(STAT_TEMPERATURE)) + u'\N{DEGREE SIGN}'
        temp_text.draw()
        uparrow.hide()
        downarrow.hide()
        wdict[7].draw() # Redraw the stuff we've over written
 

def on_click(click_pos):
    global BUTTON_LIST
    for each in BUTTON_LIST:
        if True == each.visible and True == each.clickable:
            try:
                if each.rect.collidepoint(click_pos):
                    each.pressed()
    	    except:
    	        log("Doesnt like being pressed: "+str(each))
    	        pass
        	        
def update_hw():
    global top_data, mid_data, btm_data
    try:
        resp = requests.get(url="http://calculon/home/current_hwc.py")
    except:
        print "Failed to get hot water status message from server"
        return
    data = json.loads(resp.content)
    tmb = data['rows'][0]['c'] # wtf
    top_data = tmb[0]['v']
    mid_data = tmb[1]['v']
    btm_data = tmb[2]['v']
    
    if mid_data <= 34:
        log("tank empty")
        hwc.dom.getElementsByTagName('linearGradient')[1].setAttribute('y1','-800')
    elif btm_data > 46:
        log("full tank")
        hwc.dom.getElementsByTagName('linearGradient')[1].setAttribute('y1','800')
    else:
        log("half tank")
        hwc.dom.getElementsByTagName('linearGradient')[1].setAttribute('y1','400')
        
    hwc.update()
    if HWCONSCREEN:
        hwc.draw()
    #rect = screen.blit(hwc.pygame_image, (hwc.x,hwc.y))
    #pygame.display.update(rect)

def update_hwchstatus():
    for n in range(3):
      try:
        ch_resp = requests.get(url="http://piwarmer/get/ch")
        hw_resp = requests.get(url="http://piwarmer/get/hw")
        #break
      except:
        log("Couldn't contact PiWarmer.  Trying again. #"+str(n)) # Need a function to handle these requests better, when a server has gone away etc, so we don't just crash
        pygame.time.wait(3000)
    try:    
        ch_data = json.loads(ch_resp.content)
        hw_data = json.loads(hw_resp.content)
    except:
        log("Unable to get HW/CH status, so giving up for now.")
        return
    HOTWATER = hw_data['state']
    HEATING = ch_data['state']
    if True == HOTWATER:
        hw_butt.colour = green
        hw_butt.pcol = dk_grey
        hw_text.bgcol = hw_butt.colour
    else:
        hw_butt.colour = dk_grey
        hw_butt.pcol = green
        hw_text.bgcol = hw_butt.colour        
    if True == HEATING:
        ch_butt.colour = green
        ch_butt.pcol = dk_grey
        ch_text.bgcol = ch_butt.colour
    else:
        ch_butt.colour = dk_grey
        ch_butt.pcol = green
        ch_text.bgcol = ch_butt.colour        
    screen.lock()
    hw_butt.draw()
    ch_butt.draw()
    screen.unlock()
    hw_text.draw()
    ch_text.draw()

def boiler_control(type):
    if TESTING == True:
        update_hwchstatus()
        return
    if type == "HW":
        hw_resp = requests.get(url="http://piwarmer/get/hw")
        hw_data = json.loads(hw_resp.content)
        HOTWATER = hw_data['state']
        if HOTWATER == True:
            # HW is on, so turn it off
            hw_resp = requests.post("http://piwarmer/set/hw/off")
            hw_data = json.loads(hw_resp.content)
        else:
            # HW is off, so turn it on
            hw_resp = requests.post("http://piwarmer/set/hw/on")
            hw_data = json.loads(hw_resp.content)
    if type == "CH":
        ch_resp = requests.get(url="http://piwarmer/get/ch")
        ch_data = json.loads(ch_resp.content)
        HEATING = ch_data['state']
        if HEATING == True:
            # CH is on, so turn it off
            ch_resp = requests.post("http://piwarmer/set/ch/off")
            ch_data = json.loads(ch_resp.content)
        else:
            # CH is off, so turn it on
            ch_resp = requests.post("http://piwarmer/set/ch/on")
            ch_data = json.loads(ch_resp.content)
    update_hwchstatus()

# Load Required SVGs
HWCONSCREEN=False
hwc = svg_image('hwc_new.svg', 85, 20,1.2)


def switch_control(icon, state, switchid=None):
    icon.hide()
    print "Shell out to remote sockets and switch %s to %s" % (switchid, state)
    if switchid == "lounge":
        if True == state:
            bits = GpioLogic.build_bits("3","2","on")
        else:
            bits = GpioLogic.build_bits("3","2","off")
    GpioLogic.send_code(tx_pwr, bits)
  
    

def restore_icon(icon):
    icon.visible=True
    icon.draw()


def create_home_screen():
    home_screen.name = "Home Screen"
    tx = 400
    ty = 150
    global uparrow, downarrow, temp_text, hw_butt, ch_butt, hw_text, ch_text, menu_butt, menu_text, clock, menu_gfx
    uparrow   = Triangle(tx-30,ty-50,70,red)
    uparrow.visible = False
    uparrow.start_hidden = True
    downarrow = Triangle(tx-30,ty+50,70,red, inverted=True)
    downarrow.visible = False
    downarrow.start_hidden = True
    temp_text = TextArea(tx,ty,150,black, BACKGROUND_COLOUR, str(int(STAT_TEMPERATURE)) + u'\N{DEGREE SIGN}')
    temp_text.clickable = True
    temp_text.visible = True
    temp_text.add_action("clicked",edit_stat_goal, [True])
    clock = TextArea(180,300,20, black, None, datetime.datetime.strftime(datetime.datetime.now(), "%H:%M  %d %b"), font="ubuntumono")
    clock.visible = True
    uparrow.add_action("clicked", adjust_therm_temp, (1, temp_text))
    downarrow.add_action("clicked",adjust_therm_temp, (-1, temp_text))
    hw_butt = Rectangle(290,250,60, dk_grey)
    hw_butt.borders = True
    ch_butt = Rectangle(390,250,60, dk_grey)
    hw_text = TextArea(330,280,30, black, None, "HW")
    ch_text = TextArea(430,280,30, black, None, "CH")
    ch_butt.borders = True
    hw_text.visible = ch_text.visible = True
    hw_butt.add_action("clicked", hw_text.draw)
    hw_butt.add_action("clicked", boiler_control, ["HW"])
    ch_butt.add_action("clicked", ch_text.draw)
    ch_butt.add_action("clicked", boiler_control, ["CH"])
    hw_butt.add_action("released", hw_text.draw)
    ch_butt.add_action("released", ch_text.draw)
    menu_gfx = svg_image("icons/nav_menu.svg",5,270,0.8, visible=True, clickable=True)
    menu_gfx.add_action("clicked", draw_menu_screen)
    home_screen.add(temp_text)
    home_screen.add(hw_butt)
    home_screen.add(ch_butt)
    home_screen.add(ch_text)
    home_screen.add(hw_text)
    home_screen.add(clock)
    home_screen.add(menu_gfx)
    home_screen.add(uparrow)
    home_screen.add(downarrow)


def clock_tick():
  if False == clock.visible: return
  #global CLOCK_STYLE
  #CLOCK_STYLE = not CLOCK_STYLE
  #if True == CLOCK_STYLE:
  clock.string = datetime.datetime.strftime(datetime.datetime.now(), "%H:%M %d %b")
  #else:
  #  clock.string = datetime.datetime.strftime(datetime.datetime.now(), "%H %M %d %b")
  clock.draw()

  
def draw_home_screen():
    WEATHER_VISIBLE=True
    menu_screen.hide()
    hwc_screen.hide()
    home_screen.draw()


def create_menu_screen():
    menu_screen.name = "Menu Screen"
    global show_hw_butt, show_hw_text, menu_back, lounge_light_on, lounge_light_off
    menu_back = svg_image('icons/nav_back.svg',20,260,0.5, visible=False, clickable=True)
    menu_back.add_action("clicked", draw_home_screen)
    menu_screen.add(menu_back)    

    show_hw_butt = Rectangle(20,20,70, dk_grey)
    show_hw_butt.visible = True
    show_hw_butt.borders = True
    show_hw_butt.add_action("clicked", draw_hwc_screen)
    menu_screen.add(show_hw_butt)    

    show_hw_text = TextArea(80,40,20,black,None, "Hot water")
    show_hw_text.visible = show_hw_text.clickable = False
    menu_screen.add(show_hw_text)
    show_hw_butt.add_action("released", show_hw_text.draw)    
    
    lounge_light_off = svg_image('icons/lightbulb.svg',20,100,1.5, visible=True, clickable=True)
    lounge_light_on  = svg_image('icons/lightbulb_on.svg',100,100,1.5, visible=True, clickable=True)    
    lounge_light_off.add_action("clicked",  switch_control, (lounge_light_off, False, "lounge"))
    lounge_light_off.add_action("released",  restore_icon, [lounge_light_off])
    lounge_light_on.add_action("clicked", switch_control, (lounge_light_on, True, "lounge"))
    lounge_light_on.add_action("released", restore_icon, [lounge_light_on])
    lounge_light_text = TextArea(100,200,32,black, None, "Lounge Lights")
    menu_screen.add(lounge_light_off)
    menu_screen.add(lounge_light_on)
    menu_screen.add(lounge_light_text)    
    
    sat_img_butt = Rectangle(150,20,70,dk_grey)
    sat_img_butt.visible = True
    sat_img_butt.borders = True
    sat_img_butt.add_action("clicked", draw_sat_image)
    menu_screen.add(sat_img_butt)
    

    


def create_hwc_screen():
    hwc_screen.name = "Hot Water Cylinder Screen"
    global hw_butt, ch_button, hw_text, ch_text, hwc, menu_back
    menu_back_hwc = copy.copy(menu_back)
    hwc_screen.add(hw_butt)
    hwc_screen.add(ch_butt)
    hwc_screen.add(hw_text)
    hwc_screen.add(ch_text)
    hwc_screen.add(hwc)
    hwc_screen.add(menu_back_hwc)
    
    
    
def draw_menu_screen():
    global WEATHER_VISIBLE
    WEATHER_VISIBLE=False
    # Also need to hide the weather
    home_screen.hide()
    hwc_screen.hide()
    menu_screen.draw()
    
def draw_hwc_screen():
    menu_screen.hide()
    hwc_screen.draw()


#set up the fixed items on the menu
screen.fill(BACKGROUND_COLOUR)
pygame.display.flip()
pygame.event.pump()
home_screen = MenuScreen()
menu_screen = MenuScreen()
hwc_screen = MenuScreen()
create_home_screen()
create_menu_screen()
create_hwc_screen()



michael_fish = Bitmap('michael_fish.png', (0,255,0))
michael_fish.visible = False
michael_fish.x = 75
michael_fish.y = 65



home_screen.draw()
update_daily_weather()
for each in wdict[:8]:
  home_screen.add(each.image)
  for x in each.subicons:
    home_screen.add(x)
home_screen.add(outttext)

update_sat_image()
    


# Create a once a minute tick for background updates to happen
pygame.time.set_timer(TICK1M, 60000)
pygame.time.set_timer(TICK15M, 900000)
#pygame.time.set_timer(TICK10SEC, 1000)
#pygame.time.set_timer(TICK15M, 6000)

backlight_control=GpioLogic.backlight(18)
tx_pwr = GpioLogic.txPower(22)
signal.signal(signal.SIGINT, exit_handler)

update_hw()
update_hwchstatus()

avg_counter = 0
avg_temp = 0
hour_counter = 0
very_idle_counter = 0
very_idle = False

grid()

while 1:
    try:
        event = pygame.event.wait()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if very_idle == True:
                backlight_control.full()
                very_idle = False
            very_idle_counter = 0
            pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
            mouse_rect = pygame.Rect((pos), (2,2))
            print pos
            on_click(pos)         
        #if event.type == TICK10SEC:
        #    clock_tick()
        if event.type == TICK1M:
            # Background update tasks go here
            clock_tick()
            update_hwchstatus()
            old_temp = STAT_TEMPERATURE
            STAT_TEMPERATURE = GpioLogic.get_room_temp("28-00000558ff02")
            if STAT_TEMPERATURE == False or STAT_TEMPERATURE > 40 or STAT_TEMPERATURE < -10:
                STAT_TEMPERATURE = old_temp
            temp_text.string = str(int(STAT_TEMPERATURE)) + u'\N{DEGREE SIGN}'
            temp_text.draw()
            avg_temp += STAT_TEMPERATURE
            avg_counter +=1
            log("Counter: "+str(avg_counter))
            log("Goal: "+str(MAIN_STAT_GOAL))
            log("Current: "+str(STAT_TEMPERATURE))
            log("Average: "+str(avg_temp/avg_counter))
            if avg_counter > 4: # 5 minute jobs in here
                avg_temp = avg_temp/avg_counter
                log("Average: "+str(avg_temp))
                if avg_temp >= MAIN_STAT_GOAL:
                    thermostat_relay.off()
                    log("Should be up to temp.  Turned off the stat relay")
                if avg_temp < MAIN_STAT_GOAL:
                    log("Brrr.  It's a bit chilly.  Turning on the stat relay")
                    thermostat_relay.on()
                avg_counter = 0
                avg_temp = 0
            very_idle_counter +=1
            if very_idle_counter > 1: # There might be some problems here, because once it's > 1 then this will get called every minute
              if False == home_screen.visible:  draw_home_screen()
            if very_idle_counter > 30:
                if very_idle != True:
                    very_idle = True       
                    backlight_control.low()
                    log("Very idle now set to True")
            log("1m tick!")
        if event.type == TICK15M:
            hour_counter += 1
            log("15m tick!")
            update_hw()
            if hour_counter > 3:
                # Hourly jobs
                log("Hourly tick!")
                hour_counter = 0
                michael_fish.visible = True
                michael_fish.draw()
                pygame.time.wait(5000)
                michael_fish.hide()
                update_daily_weather()
                update_sat_image()
                
              
        if event.type == BUTTONHIGHLIGHT:
            # urgh.  I cant see a way of passing this information around, so I stuck it on a list
            for i in xrange(len(BUTTON_ACTION_LIST)-1,-1,-1):
                element = BUTTON_ACTION_LIST[i]
                element.released()
                del BUTTON_ACTION_LIST[i]
        if event.type == IDLETIMEOUT:
            start_idle_timer(0)
            log("I have been doing nothing for some time, so running idle list")
            for i in xrange(len(IDLE_LIST)-1,-1,-1):
                element,args = IDLE_LIST[i]
                if None != type(element):
                    element(*args)
                del IDLE_LIST[i]
        if event.type == pygame.QUIT:
            log("QUITTING WITH EVENT OF QUIT")
            exit_handler()
    except KeyboardInterrupt:
        exit_handler()
    except:
        #print "Unexpected error:", sys.exc_info()[0]
        raise


