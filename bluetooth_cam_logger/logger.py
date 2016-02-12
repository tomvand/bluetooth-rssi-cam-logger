#!/usr/bin/python

# bluetooth_cam_logger.py
#
# This script logs Bluetooth Low Energy RSSI from addresses listed in devices.list,
# which is a file that contains one address per line (case insensitive).
#
# Output is stored in a timestamped directory (e.g. log-2016-01-01).
# Zip the directory after completion to use it in log_viewer.

import os
import sys

import datetime
from time import strftime

import blescan
import bluetooth._bluetooth as bluez

import pygame
import pygame.camera

# Default settings
devices_file = "devices.list"

output_directory = strftime("log-%Y-%m-%d/")

bluetooth_device = 0

camera_device = "/dev/video0"
camera_resolution = (320,240)

# Process command line arguments	
if len(sys.argv) >= 2:
	devices_file = sys.argv[1]

if os.path.isdir(output_directory):
	print "Error: output directory '{}' already exists.".format(output_directory)
	sys.exit(1)

# Prepare Bluetooth
try:
	sock = bluez.hci_open_dev(bluetooth_device)
except:
	print "Error accessing bluetooth device id '{}'.".format(bluetooth_device)
	sys.exit(1)
blescan.hci_le_set_scan_parameters(sock)
blescan.hci_enable_le_scan(sock)

print "Reading devices from {}...".format(devices_file)
with open(devices_file) as f:
	devices_list = f.read().lower().splitlines()
for device in devices_list:
	print device

# Prepare camera
pygame.init()
pygame.camera.init()
cam = pygame.camera.Camera(camera_device, camera_resolution)
cam.start()
#screen = pygame.display.set_mode(camera_resolution)
#pygame.display.set_caption("Recording RSSI and webcam images...")

# Prepare output folder structure
os.mkdir(output_directory)
print "Logging to '{}'.".format(output_directory)

# Prepare for recording
rssi_file = open(os.path.join(output_directory, strftime("%Y%m%d-%H.rssi")), 'w')
rssi_last_time = datetime.datetime.now()

camera_last_time = datetime.datetime.now()

# Record
running = True
try:
	while running:
		# Get the current time
		current_time = datetime.datetime.now()
		# Record RSSI
		if current_time.hour != rssi_last_time.hour:
			rssi_last_time = current_time
			# Open a new file for logging
			rssi_file.close()
			rssi_file = open(os.path.join(output_directory, strftime("%Y%m%d-%H.rssi")), 'w')
		adv_list = blescan.parse_events(sock,10)
		for adv in adv_list:
			data = adv.split(',')
			if data[0] in devices_list:
				rssi_line = "{}\t{}\t{}\n".format(current_time, data[0], data[5])
				print rssi_line
				rssi_file.write(rssi_line)
		# Record a camera image each second
		image = cam.get_image()
		if current_time.second != camera_last_time.second:
			camera_last_time = current_time
			#screen.blit(image, (0,0))
			#pygame.display.flip()
			pygame.image.save(image, os.path.join(output_directory, strftime("%Y%m%d-%H.%M.%S.jpg")))
		# Quit if the main window is closed
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
finally:
	rssi_file.close()
	print "Done."
