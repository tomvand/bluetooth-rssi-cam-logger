import argparse
import zipfile
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as pltdates
import numpy
import sys

from filters import filter_table
from show_image import show_image

# Read command line arguments
parser = argparse.ArgumentParser(description="View bluetooth rssi log.")

parser.add_argument("input_file", help="log .zip file containing the RSSI data and webcam images")
parser.add_argument("--skip", type=int, default=1, help="number of samples to skip while plotting")
parser.add_argument("--start", default="2016-01-01 00:00:00", help="skip entries before this time ('YYYY-MM-DD HH:MM:SS')")
parser.add_argument("--end", default="2050-01-01 00:00:00", help="skip entries after this time ('YYYY-MM-DD HH:MM:SS')")
parser.add_argument("--filter", default=None, help="filter to post-process data, see filters.py")
parser.add_argument("--filterdata", default="", help="additional data for the filter")
parser.add_argument("--device", default=None, help="only show results for this device address")
parser.add_argument("--event", action="store_true", help="highglight events when the filtered value is larger than 0")
args = parser.parse_args()

input_name = args.input_file
skip = args.skip
start_time = datetime.datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
end_time = datetime.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
device_filter = args.device
show_events = args.event

filter_data = args.filterdata
filter_fn = None
if args.filter:
    if args.filter in filter_table:
        filter_fn = filter_table[args.filter]
    else:
        print "Can find filter function '{}'!".format(args.filter)


# Open the log file
print "Reading from {}...".format(input_name)
zf = zipfile.ZipFile(input_name)

# Get the .rssi filenames
rssi_filenames = [name for name in zf.namelist() if name.endswith(".rssi")]
rssi_filenames.sort()
print "RSSI logs found:"
for name in rssi_filenames:
    print name

# Import RSSI data
print "Importing data, this can take a while..."
rssi_log = {"addresses": set()}
for name in rssi_filenames:
    for line in zf.read(name).splitlines():
        field = line.split('\t')
        if device_filter and field[1].lower() != device_filter.lower():
            continue
        try:
            time = datetime.datetime.strptime(field[0], "%Y-%m-%d %H:%M:%S.%f")
        except:
            time = datetime.datetime.strptime(field[0], "%Y-%m-%d %H:%M:%S")
            print "(Found incomplete timestamp at {})".format(time)
        if time >= start_time and time <= end_time:
            if not field[1] in rssi_log["addresses"]:
                rssi_log["addresses"].add(field[1])
                rssi_log[field[1]] = {"timestamp": [], "rssi": []}
            rssi_log[field[1]]["timestamp"].append(time)
            rssi_log[field[1]]["rssi"].append(int(field[2]))
        elif time > end_time:
            break

print "The following addresses were detected:"
for address in rssi_log["addresses"]:
    print address
if len(rssi_log["addresses"]) == 0:
    print "No devices were found."
    sys.exit(0)

# Show raw RSSI values
print "Plotting..."
fig = plt.figure()
plt.xlabel("Time")
plt.ylabel("RSSI [dBm]")

for address in rssi_log["addresses"]:
    plt.plot(rssi_log[address]["timestamp"][::skip], rssi_log[address]["rssi"][::skip], ".", alpha=0.5)
    plt.hold(True)
    print '{} median: {}, mean: {} dBm, variance: {} dB^2.'.format(address, numpy.median(rssi_log[address]["rssi"]), numpy.mean(rssi_log[address]["rssi"]), numpy.var(rssi_log[address]["rssi"]))
plt.grid()
plt.legend(rssi_log["addresses"])
ax = plt.gca()
ax.xaxis.set_major_formatter(pltdates.DateFormatter("%H:%M:%S"))
plt.draw()


# Apply filter if required
if filter_fn:
    print "Applying filter..."
    plt.gca().set_color_cycle(None) # Reset color cycle so filtered data appears in the correct color
    for address in rssi_log["addresses"]:
        rssi_log[address]["filtered"] = filter_fn(rssi_log[address]["timestamp"], rssi_log[address]["rssi"], filter_data)
        plt.plot(rssi_log[address]["timestamp"][::skip], rssi_log[address]["filtered"][::skip])
    plt.draw()

# Show detected events if required
if show_events:
    for address in rssi_log["addresses"]:
        event_start = -1
        for k in xrange(len(rssi_log[address]["filtered"])):
            if rssi_log[address]["filtered"][k] > 0 and event_start == -1:
                event_start = k
            elif rssi_log[address]["filtered"][k] <= 0 and event_start != -1:
                # Event found
                plt.axvspan(rssi_log[address]["timestamp"][event_start], rssi_log[address]["timestamp"][k], color='r', alpha=0.5, lw=0)
                event_start = -1


# Add a click event handler which will show the webcam image from a specified time
def onclick(event):
    if event.xdata:
        time = pltdates.num2date(event.xdata)
        print "Retrieve image from {}...".format(time)
        show_image(zf, time)

fig.canvas.mpl_connect("motion_notify_event", onclick)

# Wait until the user closes the window
print "Done. Click on the plot to retrieve webcam images. Close the plot to end"
plt.show()





