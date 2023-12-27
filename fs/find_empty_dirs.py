#!/usr/bin/env python
import argparse
import os
import stat
import sys
from shutil import rmtree

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress


def find_empty_dirs(lib_path: str, ignore_hidden=False, ignore_size=0, remove='prompt'):
    """ Finds empty directories and optionally removes them. Small or hidden files can be ignored.

    :param lib_path: Base directory to search from
    :param ignore_hidden: If True, hidden files will be ignored
    :param ignore_size: Size in KB below which files will be ignored
    :param remove: String specifying how to handle removal of empty directories:
                    "yes" removes the empty directories without user interaction
                    "no" only prints the empty directories
                    "prompt_all" prints the empty directories and asks if they should all be removed
    :return: 0 if the process ran successfully
    """
    # Check the input variables
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1

    # Converts ignored file size to bytes
    ignore_size = ignore_size*1024

    # Check if directories are empty
    msg = "Scanned {} directories"
    empty_dirs = []
    count = 0
    for root, dirs, files in os.walk(lib_path):
        count += 1
        print_progress(msg, count)
        if len(dirs) == 0:
            if len(files) == 0:
                empty_dirs += [root]
            elif ignore_hidden or ignore_size:
                all_ignored = True
                for file in files:
                    file_path = os.path.join(root, file)
                    if not ((ignore_hidden and is_hidden(file, file_path))
                            or (ignore_size and (os.path.getsize(file_path) < ignore_size))):
                        all_ignored = False
                        break

                if all_ignored:
                    empty_dirs += [root]

    print_progress(msg, count, final=True)
    print()
    if len(empty_dirs):
        [print(d) for d in empty_dirs]
        print()
        if (remove == "yes" or
                (remove == "prompt_all" and input("The above directories are empty, remove? (Y/N)").lower() == "y")):
            [rmtree(d) for d in empty_dirs]
        else:
            print("The above directories are empty")
    else:
        print("No empty directories found")


def is_hidden(file_name, file_path):
    """ Returns True if the file is a hidden file, False otherwise """
    return file_name.startswith('.') or bool(os.stat(file_path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Reencodes flac files recursively from the specified directory')
    parser.add_argument('lib_path', type=str, help='Base directory')
    parser.add_argument('-ih', '--ignore-hidden', action='store_true', help='Hidden files to be ignored')
    parser.add_argument('-is', '--ignore-size', type=int, default=0, help='Size in KB below which files will be ignored')
    parser.add_argument('-r', '--remove', type=str, choices=["yes", "no", "prompt_all"], default="prompt_all",
                        help='String specifying how to handle removal of empty directories: '
                             '"yes" removes the empty directories without user interaction. '
                             '"no" only prints the empty directories. '
                             '"prompt_all" prints the empty directories and asks if they should all be removed.')

    args = parser.parse_args()
    sys.exit(find_empty_dirs(**vars(args)))
