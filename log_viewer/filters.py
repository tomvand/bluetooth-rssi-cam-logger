# This file contains filters to post-process RSSI data.
# Filter functions get called with a list of datetime timestamps, a list of integer RSSI values and a string with
# optional input. The functions return a list of data points corresponding to the input timestamps.

import numpy
import datetime
import math

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
    if window_end - window_start == 0:
        return float('NaN')
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
    if len(rssi[window_start:window_end]) <= 0:
        return float('NaN')
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
    # Data: sigma (try 1.6 (night measurement) or 4.75 (day measurement) for ef:36:...).
    # Result: obstacle detected when the signal is larger than 0.
    sigma = float(data)
    return [-2*sigma - diff for diff in difference(time, rssi, data)]


def youssef2007a(time, rssi, data):
    # Data: wl,ws,tau
    # Result: obstacle detected when signal is larger than 0.
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
            ask = 1/float(ws) * (cumsum[k+wl+ws-1] - cumsum[k+wl])
            result.append(abs((alk-ask)/alk) - tau)
            # print "{}: wl = {}, ws = {}, alk = {}, ask = {}. rel.diff = {}".format(k, wl, ws, alk, ask, abs((alk-ask)/alk))
        else:
            result.append(False)
    return result


def youssef2007b(time, rssi, data):
    # Data: w,vtbar,sigmav,r
    # Result: obstacle detected when the signal is larger than 0.
    data_fields = data.split(',')
    w = int(data_fields[0])
    vtbar = float(data_fields[1])
    sigmav = float(data_fields[2])
    r = float(data_fields[3])

    result = []
    for k in xrange(-w+1, len(rssi)-w+1):
        if k >= 0:
            vt = youssef2007b_vt(rssi[k:k+w-1])
            result.append(vt - vtbar - r*sigmav)
        else:
            result.append(0.0)
    return result

def youssef2007b_vt(qi):
    return numpy.var(qi)

def youssef2007b_training(time, rssi, data):
    # Data: w
    w = int(data)

    vt = []
    for k in xrange(0,len(rssi)-w+1):
        vt.append(youssef2007b_vt(rssi[k:k+w-1]))
    # print "Training results:\n vtbar = {}, sigmav = {}.".format(numpy.mean(vt), numpy.std(vt, ddof=len(vt)-w+1))
    print "Training results:\n vtbar = {}, sigmav = {}.".format(numpy.mean(vt), numpy.std(vt))
    return rssi


def windowed_variance_detector(time, rssi, data):
    data_fields = data.split(',')
    wbase = int(data_fields[0])
    winstant = int(data_fields[1])
    r = float(data_fields[2])
    std_min = float(data_fields[3])

    psa_base = 0
    sma_base = 0
    psa_var = 0
    sma_var = 0
    psa_event = 0
    sma_event = 0

    queue_base = [0] * winstant
    queue_var = [0] * wbase
    queue_event = [0] * winstant

    result = []
    for k in xrange(len(rssi)):
        # Update the moving variances of RSSI
        var_event, queue_event, psa_event, sma_event, shift = running_variance(queue_event, psa_event, sma_event, rssi[k])
        var_base, queue_base, psa_base, sma_base, unused = running_variance(queue_base, psa_base, sma_base, shift)
        # Update the variance of the base RSSI variance
        var_var, queue_var, psa_var, sma_var, unused = running_variance(queue_var, psa_var, sma_var, var_base)
        # Calculate the output of the filter
        result.append(var_event - sma_var - r*max(std_min, math.sqrt(var_var)))
    return result


def windowed_average_detector(time, rssi, data):
    data_fields = data.split(',')
    wbase = int(data_fields[0])
    winstant = int(data_fields[1])
    r = float(data_fields[2])

    psa_base = 0
    sma_base = 0
    psa_event = 0
    sma_event = 0

    queue_base = [0] * wbase
    queue_event = [0] * winstant

    var_base = 10000

    result = []
    for k in xrange(len(rssi)):
        # Update the moving variances of RSSI
        var_event, queue_event, psa_event, sma_event, shift = running_variance(queue_event, psa_event, sma_event, rssi[k])
        # Calculate the output of the filter
        diff = -(sma_event-sma_base) - r*math.sqrt(var_base)
        result.append(diff)
        # Update the baseline if no event occured
        if k < (wbase+winstant) or diff < 0:
            var_base, queue_base, psa_base, sma_base, unused = running_variance(queue_base, psa_base, sma_base, shift)
    return result



def running_variance(queue, psa, sma, new):
    # See http://stackoverflow.com/questions/5147378/rolling-variance-algorithm
    # Update the estimated variance
    old = queue[0]
    n = len(queue)
    psa += (new**2 - old**2) / float(n)
    sma += (new - old) / float(n)
    var = psa - sma**2
    # Shift the queue
    queue = queue[1:] + [new]
    # Return the results
    return max(0.0, var), queue, psa, sma, old


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
    "youssef2007b_training": youssef2007b_training,
    "windowed_variance": windowed_variance_detector,
    "windowed_average": windowed_average_detector
}