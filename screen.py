#!/usr/bin/python

import os
import pygame
import time
import random
import array
import math
import cairo
import rsvg

class pyscope :
    screen = None;
    
    def __init__(self):
        # Check which frame buffer drivers are available
        # Start with fbcon since directfb hangs with composite output
        #drivers = ['fbcon', 'directfb', 'svgalib']
        drivers = ['fbcon']
        found = False
        for driver in drivers:
            # Make sure that SDL_VIDEODRIVER is set
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pygame.display.init()
            except pygame.error:
                print 'Driver: {0} failed.'.format(driver)
                continue
            found = True
            break
    
        if not found:
            raise Exception('No suitable video driver found!')
        
        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.s = size
        print "Framebuffer size: %d x %d" % (size[0], size[1])
        self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
        # Clear the screen to start
        self.screen.fill((0, 0, 0))        
        # Initialise font support
        pygame.font.init()
        # Render the screen
        pygame.display.update()

    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    def test(self):
        # Fill the screen with red (255, 0, 0)
        red = (255, 0, 0)
        self.screen.fill(red)
        # Update the display
        pygame.display.update()

# Create an instance of the PyScope class
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.putenv('SDL_MOUSEDRV', 'TSLIB')
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')


scope = pyscope()
scope.test()
time.sleep(2)

WIDTH, HEIGHT = scope.s[0], scope.s[1]
data = array.array('c', chr(0) * WIDTH * HEIGHT * 4)
surface = cairo.ImageSurface.create_for_data(
    data, cairo.FORMAT_ARGB32, WIDTH, HEIGHT, WIDTH * 4)
#window = pygame.display.set_mode((WIDTH, HEIGHT))
svg = rsvg.Handle(file="hwc.svg")
ctx = cairo.Context(surface)
svg.render_cairo(ctx)
print svg
print ctx


screen = scope.screen

image = pygame.image.frombuffer(data.tostring(), (WIDTH, HEIGHT),"ARGB")
screen.blit(image, (0, 0)) 
#pygame.display.flip() 
pygame.display.update()
time.sleep(2)
img = pygame.image.load('ocr_pi.png')
screen.blit(img, (0,0))
#pygame.display.flip()
pygame.display.update()

time.sleep(3)

