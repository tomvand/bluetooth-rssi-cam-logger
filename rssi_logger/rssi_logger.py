#!/usr/bin/python

import blescan
import sys
import bluetooth._bluetooth as bluez
import numpy

import matplotlib.pyplot as plt

# Read command line input
dev_id = 0
address = ""
number_of_samples = -1

if len(sys.argv) < 3:
	print "Usage: rssi_logger.py <device id> <address> [<samples>]"
	sys.exit(1)

try:
	dev_id = int(sys.argv[1])
except:
	print "Invalid device id: '{}', should be an integer.".format(sys.argv[1])
	sys.exit(1)

address = sys.argv[2]
	
if len(sys.argv) >= 4:
	try:
		number_of_samples = int(sys.argv[3])
	except:
		print "Invalid number of samples: '{}'.".format(sys.argv[3])
		sys.exit(1)

# Scan and collect data
print "Scanning for '{}'...".format(address)

try:
	sock = bluez.hci_open_dev(dev_id)
except:
	print "Error accessing bluetooth device."
	sys.exit(1)

blescan.hci_le_set_scan_parameters(sock)
blescan.hci_enable_le_scan(sock)

average = 0.0
remaining = number_of_samples

rssi_list = []

while remaining != 0:
	adv_list = blescan.parse_events(sock, 10)
	for entry in adv_list:
		data = entry.split(',')
		if data[0].lower() == address.lower():
			print(data[5])
			rssi_list.append(int(data[5]))
			if remaining > 0:
				remaining -= 1


print "Average: {} dBm, std {} over {} samples.".format(numpy.mean(rssi_list), numpy.std(rssi_list),  number_of_samples)

print "Done."

# Plot a graph of the RSSIs
plt.plot(range(number_of_samples), rssi_list, 'bo')
plt.axis([0, number_of_samples, -100, 0])
plt.ylabel('RSSI [dBm]')
plt.show()
