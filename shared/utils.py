""" Shared functions for the other modules """

import time
from datetime import datetime


def print_progress(msg, *args, show_time=True, init=False, final=False):
    """ Throttles printing and updates the progress of a process on a single line
    Note: When running in an IDE, the terminal must be emulated in the output console to allow flushing of the output
    :param msg: String message to format with the arguments
    :param args: Positional arguments to insert into the message string
    :param show_time: If true, elapsed time will be shown before the message
    :param init: If true, resets elapsed time
    :param final: If true, throttling is ignored and the message is ended with a new line character
    """
    if final or time.time() > print_progress.prev_call + 1 or print_progress.prev_call_final or init:
        end = "\n" if final else "\r"
        msg = time_brackets(init=init) + msg if show_time else msg
        msg = msg.format(*args)
        if len(msg) > print_progress.pad_len:
            print_progress.pad_len = len(msg)
        print(msg.ljust(print_progress.pad_len), end=end, flush=True)
        print_progress.prev_call = time.time()
        if final:
            print_progress.prev_call_final = True
            print_progress.pad_len = 0
        else:
            print_progress.prev_call_final = False
print_progress.prev_call_final = False
print_progress.prev_call = 0
print_progress.pad_len = 0


def time_elapsed(init=False, text=True):
    """ Returns the time elapsed since initialization, either in timedelta or in readable text format (default) """

    if init or not hasattr(time_elapsed, 'start'):
        time_elapsed.start = datetime.now()
        elapsed = time_elapsed.start - time_elapsed.start
    else:
        elapsed = datetime.now() - time_elapsed.start

    if text:
        return str(elapsed).split('.')[0]
    else:
        return elapsed

def time_brackets(init=False):
    """ Wraps time_elapsed in brackets [] """
    return "[{}] ".format(time_elapsed(init=init))
