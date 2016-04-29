import argparse
import datetime
import zipfile
import time

from show_image import show_image

parser = argparse.ArgumentParser(description="Webcam zipped image viewer.")
parser.add_argument("input_file", help="log .zip file containing the webcam images")
parser.add_argument("--start", default="2016-01-01 00:00:00", help="(YYYY-MM-DD HH:MM:SS) start time")
args = parser.parse_args()

filename = args.input_file
time_start = datetime.datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")


zf = zipfile.ZipFile(filename)
time_current = time_start
real_time_current = datetime.datetime.now()
while True:
    try:
        show_image(zf, time_current)
    except:
        print "Can't show image at time {}.".format(time_current)
    while datetime.datetime.now().second == real_time_current.second:
        time.sleep(0.01)
    real_time_current = datetime.datetime.now()
    time_current += datetime.timedelta(seconds=1.0)

