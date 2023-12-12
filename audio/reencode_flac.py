#!/usr/bin/env python
""" Reencodes flac files recursively from the specified directory, overwriting the old files """

import argparse
import os
import shlex
import subprocess
import sys
import time

from packaging import version

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress, time_elapsed


def reencode_flac(lib_path: str, force: bool = False, n_procs: int = 4, verbose: bool = False) -> int:
    """ Reencodes flac files recursively from the specified directory, overwriting the old files
    :param lib_path: Base directory from which files will reencoded recursively
    :param force: If False (default), files encoded with the reference flac encoder of equal or higher version will be skipped
    :param n_procs: Number of encoding tasks to run concurrently
    :param verbose: If True, additional subprocess output is displayed
    :return: 0 if the process ran successfully
    """

    # Check the input variables
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1
    if n_procs < 1:
        n_procs = 4
        print("n_procs should be >= 1, value reset to default {}".format(n_procs))

    # Check if flac is in the PATH variable and get the version
    try:
        flac_version = subprocess.check_output("flac -v").decode('utf-8').split()[-1]
    except Exception as e:
        print("Error - Could not find flac executable, make sure it is in your PATH variable")
        print(e)
        return 1
    
    print("Flac version " + flac_version + " found")
    flac_version = version.parse(flac_version)

    # Extracts the FLAC files from the file system and output number of files and total size
    flac_files = []
    dir_count = 1  # Start at 1 for the base directory

    for root, dirs, files in os.walk(lib_path):
        flac_files += [os.path.join(root, file) for file in files if is_flac(file)]
        dir_count += len(dirs)
    print(len(flac_files), " FLAC files found in ", dir_count, " directories")

    # Select the flac files that need to be reencoded
    if not force:
        flac_files = [file for file in flac_files if _needs_reencoding(file, flac_version)]
        print(len(flac_files), " FLAC files need reencoding. (Use the -f force flag to reencode all files)")

    file_size = int(sum(os.path.getsize(file) for file in flac_files)/(1000**2))
    print("Size of files is ", file_size, " MB")

    # Calls encoding tasks in parallel
    processes = set()
    flac_command = shlex.split('flac --best --verify --force --decode-through-errors')
    errors = []
    current_file = 0
    msg = "[{}] Encoding file {}/{}"
    output = None if verbose else subprocess.DEVNULL
    for file in flac_files:
        current_file += 1
        print_progress(msg, time_elapsed(), current_file, len(flac_files))
        processes.add(subprocess.Popen(flac_command + [file], stdout=output, stderr=output))
        while len(processes) >= n_procs:
            _wait_for_processes(processes, errors)

    # Wait for the remaining processes to finish
    while len(processes) > 0:
        _wait_for_processes(processes, errors)

    print(msg.format(time_elapsed(), current_file, len(flac_files)))
    print("Encoding completed!")

    # Check how much space was saved and show errors if any
    new_file_size = int(sum(os.path.getsize(file) for file in flac_files)/(1000**2))
    print("\nNew size of files is ", new_file_size, " MB")
    print(file_size - new_file_size, " MB saved!")

    print("\n", len(errors), " encoding errors occured")
    for e in errors:
        print("Error: (", e[0], ") ", e[1][-1])

    return 0


def get_flac_vendor_string(file: str) -> str:
    """ Attempts to read the vendor string from a flac file
        reference https://xiph.org/flac/format.html#stream
    """

    with open(file, "rb") as f:
        # Init
        result = ""
        block_type = 0

        # Read the flac identifier
        data = f.read(4).decode('utf-8', errors="ignore")
        if data != "fLaC":
            raise TypeError("File does not comply to flac format: {}".format(file))

        # Search the metadata blocks for the first vorbis_comment block
        # A type of more than 126 means its either invalid or the last metadata block
        while data and block_type < 126:
            data = f.read(4)
            block_type = int.from_bytes([data[0]], byteorder='big')
            block_length = int.from_bytes(data[1:], byteorder='big')

            # Read the string from the vorbis_comment data block (type 4)
            # https://www.xiph.org/vorbis/doc/v-comment.html
            if block_type == 4:
                # The vendor string is the first field in the block
                field_length = int.from_bytes(f.read(4), byteorder='little')
                data = f.read(field_length)
                result = data.decode('utf-8', errors="ignore")
                break
            else:
                f.seek(block_length, 1)
        
        return result


def is_flac(file: str) -> bool:
    """ Checks the extension of a file name to see if it's a FLAC file """
    ext = (file.split(".")[-1]).lower()
    return ext == 'flac' or ext == 'fla'


def _needs_reencoding(file: str, flac_version: version.Version) -> bool:
    """ Check if the file was encoded with an older version of FLAC"""
    try:
        vendor_string = get_flac_vendor_string(file).split()
    except Exception as e:
        print("File skipped: " + str(e))
        return False

    if len(vendor_string) >= 3 and vendor_string[0] == "reference" and vendor_string[1] == "libFLAC":
        if version.parse(vendor_string[2]) < flac_version:
            return True
        else:
            return False
    else:
        return True


def _wait_for_processes(processes, errors):
    """ Wait for processes to complete and updates the running process list and error list """
    time.sleep(.5)
    completed = [p for p in processes if p.poll() is not None]
    processes.difference_update(completed)
    for p in completed:
        if p.returncode != 0:
            errors += [[p.returncode, p.args]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reencodes flac files recursively from the specified directory')
    parser.add_argument('lib_path', type=str, help='Base directory')  
    parser.add_argument('-f', '--force', action='store_true', help='Forces reencoding all files even if they have been encoded with a higher or equal flac version')
    parser.add_argument('-n_procs', type=int, default=4, help='Number of files to encode in parallel')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    sys.exit(reencode_flac(**vars(args)))
