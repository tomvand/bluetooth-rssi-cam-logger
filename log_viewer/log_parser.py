import zipfile
import sys
import datetime

def parseLog(filename, device_filter=None, start_time=datetime.datetime(2015,1,1), end_time=datetime.datetime(2050,1,1)):
    """
    :param filename: path to zipfile containing .rssi files
    :param device_filter: if specified, only parse results from this device
    :param start_time: (datetime) ignore entries before this time
    :param end_time: (datetime) ignore entries after this time
    :return: RSSI log: {
        ["addresses"]: set(address, address, ...)
        ["<address>"]:
            ["timestamp"]: [timestamp, timestamp, ...]
            ["rssi"]: [rssi, rssi, ...] }
    """
    # Open the log file
    print "Reading from {}...".format(filename)
    zf = zipfile.ZipFile(filename)

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

    return rssi_log