#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pigpio
import pyaudio
from struct import unpack
import numpy as np
import audioop
import wave
import os
import sys
import cgitb; cgitb.enable()
from random import shuffle

RED_PIN   = 24
GREEN_PIN = 22
BLUE_PIN  = 17

BRIGHTNESS_MULT = 1.0
TRANSITION_BRIGHTNESS = 1.0
LAST_DIR = "up"
UPDATE_BRIGHT = 0
COLOR_EFFECT = 3
LOWEST_BRIGHTNESS = 0.3
CHANGE_SPEED = 3.0

LEVEL_HISTORY = []
LAST_LEVEL = 0.5

r = 255.0
g = 0.0
b = 0.0

scale = 30
exponent = 5

CHUNK = 1024

p = pyaudio.PyAudio()

pi = pigpio.pi()

path = "/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/muzik/playlists/"

def updateLights():
        global r, g, b, BRIGHTNESS_MULT

        pi.set_PWM_dutycycle(RED_PIN, r * BRIGHTNESS_MULT)
        pi.set_PWM_dutycycle(GREEN_PIN, g * BRIGHTNESS_MULT)
        pi.set_PWM_dutycycle(BLUE_PIN, b * BRIGHTNESS_MULT)
   
def clearLights():
        global r, g, b
        r = 0.0
        g = 0.0
        b = 0.0
        updateLights()

def updateColors(level):
        global r, g, b, CHANGE_SPEED, COLOR_EFFECT

        amount = CHANGE_SPEED
        if level == 1.0:
                amount = amount + (amount*level)*COLOR_EFFECT
        elif level > 0.7:
                amount = amount + (amount*level)*2
        else:
                amount = amount - (amount*level)

        if r > 0 and b == 0:
                if r > amount:
                        r -= amount
                else:
                        r = 0.0
                if g < (255-amount):
                        g += amount
                else:
                                g = 255
        elif g > 0 and r == 0:
                if g > amount:
                        g -= amount
                else:
                        g = 0.0
                if b < (255-amount):
                        b += amount
                else:
                        b = 255
        else:
                if b > amount:
                        b -= amount
                else:
                        b = 0.0
                if r < (255-amount):
                        r += amount
                else:
                        r = 255

def updateBright(new_brightness):
        global BRIGHTNESS_MULT, TRANSITION_BRIGHTNESS, LAST_DIR, UPDATE_BRIGHT
        if new_brightness >= BRIGHTNESS_MULT:
                if LAST_DIR == "up" and UPDATE_BRIGHT == 0:
                        TRANSITION_BRIGHTNESS = new_brightness
                LAST_DIR = "up"
                BRIGHTNESS_MULT = min(BRIGHTNESS_MULT + ((TRANSITION_BRIGHTNESS - BRIGHTNESS_MULT) / 3.0), 1.0)
        else:
                if LAST_DIR == "down" and UPDATE_BRIGHT == 0:
                        TRANSITION_BRIGHTNESS = new_brightness
                LAST_DIR = "down"
                BRIGHTNESS_MULT = max(BRIGHTNESS_MULT - ((BRIGHTNESS_MULT - TRANSITION_BRIGHTNESS) / 3.0), 0.0)
        UPDATE_BRIGHT = UPDATE_BRIGHT - 1
        if UPDATE_BRIGHT < 0:
                UPDATE_BRIGHT = 3

def updateLevel(rms):
        global LEVEL_HISTORY, LAST_LEVEL, scale, exponent

        if len(LEVEL_HISTORY) < 50:
                LEVEL_HISTORY.append(rms)
                level = min(rms / (2.0 ** 16) * scale, 1.0)
                level = level**exponent
        else:
                avg = np.mean(LEVEL_HISTORY)
                if rms > avg:
                        diff = rms-avg
                        level = LAST_LEVEL + min(diff / (2.0 ** 16) * scale, (1.0-LAST_LEVEL))
                elif rms < avg:
                        diff = avg-rms
                        level = LAST_LEVEL - min(diff / (2.0 ** 16) * scale, (1.0-LAST_LEVEL))
                else:
                        level = LAST_LEVEL
                LEVEL_HISTORY.pop(0)
                LEVEL_HISTORY.append(rms)
        return level


def do_stuff(path_to_song):
	wf = wave.open(('/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/muzik/playlists/'+ path_to_song),'r')
	stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
			channels=2,
			rate=wf.getframerate(),
			output=True)

	data = wf.readframes(CHUNK)

	while data:
		if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt"):
			if stream.is_stopped():
				stream.start_stream()

			data = wf.readframes(CHUNK)
			stream.write(data)

			rms = audioop.rms(data, 2)
			level = updateLevel(rms)

			if level < LOWEST_BRIGHTNESS:
				level = LOWEST_BRIGHTNESS

			updateBright(level)
			updateColors(level)
			updateLights()

		else:
			clearLights()
			break
	if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt"):
		os.remove("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt")
		clearLights()
		stream.stop_stream()
		stream.close()

def radio_only(path_to_song):

	wf = wave.open(('/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/muzik/playlists/'+ path_to_song),'r')
	stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
			channels=2,
			rate=wf.getframerate(),
			output=True)

	data = wf.readframes(CHUNK)

	while data:
		if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt"):
			if stream.is_stopped():
				stream.start_stream()

			data = wf.readframes(CHUNK)
			stream.write(data)

		else:
			break
	if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt"):
		os.remove("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt")
		stream.stop_stream()
		stream.close()


if "/" in sys.argv[1]:
	file = open("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt", "w")
	file.close()
	if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/lights_toggle.txt"):
		do_stuff(sys.argv[1])
	else:
		radio_only(sys.argv[1])

else:
	file = open("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/playlist_running.txt", "w")
	file.close()
	playlist = []
	for dir in sys.argv[1:]:
		dirlist = os.listdir(path + dir)
		for file in dirlist:
			playlist.append(dir + "/" + file)
	shuffle(playlist)
	for i in playlist:
		if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/playlist_running.txt"):
			file = open("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/running.txt", "w")
			file.close()
			if os.path.isfile("/media/pi/049A2F279A2F1528/00CCB50CCCB4FD4A/lights_toggle.txt"):
				do_stuff(i)
			else:
				radio_only(i)
			#print(i)
