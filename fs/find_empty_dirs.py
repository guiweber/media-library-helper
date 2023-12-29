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

_scan_count = 0

def find_empty_dirs(lib_path: str, ignore_hidden=False, ignore_size=0, remove='prompt'):
    """ Finds empty directories and optionally removes them. A directory is considered empty if it contains no or only
        empty directories, symbolic links and ignored files. The root directory is never removed.
        Small or hidden files can be ignored. Symbolic links are always ignored.

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
    remove = remove.lower()
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1

    # Converts ignored file size to bytes
    ignore_size = ignore_size*1024

    # Check if directories are empty
    msg = "Scanned {} directories"
    empty_dirs = []
    if _is_empty_recursive(lib_path, msg, empty_dirs, ignore_hidden, ignore_size):
        empty_dirs = [entry.path for entry in os.scandir(lib_path) if entry.is_dir(follow_symlinks=False)]

    print_progress(msg, _scan_count, final=True)
    print()
    if len(empty_dirs):
        if (remove == "yes" or
                (remove == "prompt_all" and input("The above directories are empty, remove? (Y/N)").lower() == "y")):
            errors = []
            for d in empty_dirs:
                try:
                    rmtree(d)
                    print(d)
                except Exception as e:
                    errors += [str(e)]
            if len(errors) < len(empty_dirs):
                print()
                print("The above directories were empty and have been removed")
            if errors:
                print()
                print("Some errors occurred:")
                [print(e) for e in errors]
        else:
            [print(d) for d in empty_dirs]
            print()
            print("The above directories are empty")
    else:
        print("No empty directories found")


def _is_empty_recursive(path, msg, empty_dirs, ignore_hidden, ignore_size):

    global _scan_count
    _scan_count += 1
    print_progress(msg, _scan_count)

    local_empty_dirs = []
    has_files = False
    has_non_empty_dirs = False

    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False) and not has_files:
            if not ((ignore_hidden and is_hidden(entry))
                    or (ignore_size and (entry.stat(follow_symlinks=False).st_size < ignore_size))):
                has_files = True
        elif entry.is_dir(follow_symlinks=False):
            if _is_empty_recursive(entry.path, msg, empty_dirs, ignore_hidden, ignore_size):
                local_empty_dirs += [entry.path]
            else:
                has_non_empty_dirs = True

    if has_non_empty_dirs or has_files:
        empty_dirs += local_empty_dirs
        return False
    else:
        return True


def is_hidden(entry):
    """ Returns True if the file is a hidden file, False otherwise """
    return entry.name.startswith('.') or bool(entry.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)


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
