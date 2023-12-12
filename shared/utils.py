""" Shared functions for the other modules """

import time
from datetime import datetime


def print_progress(msg, *args):
    """ Throttles printing the progress of a process """
    if time.time() > print_progress.last_call + 1:
        print(msg.format(*args), end="\r", flush=True)
        print_progress.last_call = time.time()
print_progress.last_call = 0


def time_elapsed(init=False, text=True):
    """ Returns the time elapsed since initialization, either in timedelta format or in a readable text format (default) """

    if init or not hasattr(time_elapsed, 'start'):
        time_elapsed.start = datetime.now()
        elapsed = time_elapsed.start - time_elapsed.start
    else:
        elapsed = datetime.now() - time_elapsed.start

    if text:
        return str(elapsed).split('.')[0]
    else:
        return elapsed
