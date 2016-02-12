# This file contains filters to post-process RSSI data.
# Filter functions get called with a list of datetime timestamps, a list of integer RSSI values and a string with
# optional input. The functions return a list of data points corresponding to the input timestamps.

import numpy
import datetime
import sys

def template_function(time, rssi, data):
    return rssi


def difference(time, rssi, data):
    return [0.0] + numpy.diff(rssi).tolist()


def window_filter(time, rssi, window, filter_fn, data=None):
    window_start = 0
    window_end = 0

    result = []
    for t in time:
        while time[window_start] < t - window/2:
            window_start += 1
        while time[window_end] < t + window/2 and window_end < len(time)-1:
            window_end += 1
        filtered_value = filter_fn(time, rssi, data, window_start, window_end)
        result.append(filtered_value)
    return result


def moving_average(time, rssi, data):
    window = datetime.timedelta(seconds=float(data)) # Window in seconds
    cumsum = numpy.cumsum(rssi) # Precalculate cumulative sum
    return window_filter(time, rssi, window, moving_average_fn, cumsum)

def moving_average_fn(time, rssi, cumsum, window_start, window_end):
    # Data contains a cumsum list of rssi values
    return float(cumsum[window_end]-cumsum[window_start]) / (window_end-window_start)
    # return numpy.mean(rssi[window_start:window_end]) # Slower because it needs to sum every time step


def moving_variance(time, rssi, data):
    window = datetime.timedelta(seconds=float(data)) # Window in seconds
    return window_filter(time, rssi, window, moving_variance_fn)

def moving_variance_fn(time, rssi, unused, window_start, window_end):
    return numpy.var(rssi[window_start:window_end])


def moving_minimum(time, rssi, data):
    window = datetime.timedelta(seconds=float(data)) # Window in seconds
    return window_filter(time, rssi, window, moving_minimum_fn)

def moving_minimum_fn(time, rssi, unused, window_start, window_end):
    return min(rssi[window_start:window_end])


def moving_envelope(time, rssi, data):
    window = datetime.timedelta(seconds=float(data)) # Window in seconds
    return window_filter(time, rssi, window, moving_envelope_fn)

def moving_envelope_fn(time, rssi, unused, window_start, window_end):
    return max(rssi[window_start:window_end]) - min(rssi[window_start:window_end])

def moving_average_event(time, rssi, data):
    data_fields = data.split(',')
    window_background = datetime.timedelta(seconds=float(data_fields[0]))
    window_event = datetime.timedelta(seconds=float(data_fields[1]))
    background = window_filter(time, rssi, window_background, moving_average_fn)
    event = window_filter(time, rssi, window_event, moving_average_fn)
    return [ev - back for ev, back in zip(event, background)]


def causal_ma_event(time, rssi, data):
    data_fields = data.split(',')
    window_background = datetime.timedelta(seconds=float(data_fields[0]))
    window_event = datetime.timedelta(seconds=float(data_fields[1]))
    window_end = 0
    window_background_start = 0
    window_event_start = 0

    result = []
    for t in time:
        while time[window_event_start] < t - window_event:
            window_event_start += 1
        while time[window_background_start] < time[window_event_start] - window_background:
            window_background_start += 1
        if window_end > window_event_start and window_event_start > window_background_start:
            diff = min(0, numpy.mean(rssi[window_event_start:window_end]) - numpy.mean(rssi[window_background_start:window_event_start]))
        else:
            diff = 0
        result.append(diff)
        window_end += 1
    return result


def wang2013(time, rssi, data):
    sigma = float(data)
    return [diff < -2*sigma for diff in difference(time, rssi, data)]


def youssef2007a(time, rssi, data):
    data_fields = data.split(',')
    wl = int(data_fields[0])
    ws = int(data_fields[1])
    tau = float(data_fields[2])
    print "Youssef2007a moving average filter. wl = {}, ws = {}, tau = {}.".format(wl, ws, tau)

    cumsum = numpy.cumsum(rssi)

    result = []
    for k in xrange(-ws-wl+1, len(rssi)-ws-wl+1):
        if k >= 0:
            alk = 1/float(wl) * (cumsum[k+wl-1] - cumsum[k])
            ask = 1/float(ws) * (cumsum[k+wl+ws-1] - cumsum[k-wl])
            result.append(abs((alk-ask)/alk) > tau)
        else:
            result.append(False)
    return result


def youssef2007b(time, rssi, data):
    data_fields = data.split(',')
    w = int(data_fields[0])
    vtbar = float(data_fields[1])
    sigmav = float(data_fields[2])
    r = float(data_fields[3])

    result = []
    for k in xrange(-w+1, len(rssi)-w+1):
        if k >= 0:
            vt = youssef2007b_vt(rssi[k:k+w-1])
            result.append(vt > vtbar + r*sigmav)
        else:
            result.append(False)
    return result

def youssef2007b_vt(qi):
    return numpy.var(qi)

def youssef2007b_training(time, rssi, data):
    w = int(data)

    vt = []
    for k in xrange(0,len(rssi)-w+1):
        vt.append(youssef2007b_vt(rssi[k:k+w-1]))
    print "Training results:\n vtbar = {}, sigmav = {}.".format(numpy.mean(vt), numpy.std(vt))
    return rssi


filter_table = {
    "default": template_function,
    "difference": difference,
    "moving_average": moving_average,
    "moving_minimum": moving_minimum,
    "moving_envelope": moving_envelope,
    "moving_variance": moving_variance,
    "moving_average_event": moving_average_event,
    "causal_ma_event": causal_ma_event,
    "wang2013": wang2013,
    "youssef2007a": youssef2007a,
    "youssef2007b": youssef2007b,
    "youssef2007b_training": youssef2007b_training
}