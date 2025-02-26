#!/usr/bin/env python
""" Convert images files of the specified types to png """
import argparse
import os
import sys
from PIL import Image

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress
from fs.FileList import FileList


def convert_to_png(path: str, recursive: bool, ext: str, force: bool = False) -> int:
    """ Converts image files of the specified types to png
    :param path: Base directory to look for input files
    :param recursive: If True, directories will be searched recursively
    :param ext: List of image file extensions that you want to include in the search
    :param force: If True, any existing png files with conflicting names will be overwritten during conversion

    """
    files = FileList.build(root_dirs=path, recursive=recursive, ext_filter=ext, disp=True)
    ex = _convert(files, force)

    while ex:
        print("\n{} files were not converted because corresponding png files already existed. "
              "Press 'l' to list the files, 'o' to convert and overwrite, or 'x' to exit without overwriting. "
              "You can also use launch the program with the -f or --force argument to force overwriting "
              "by default".format(len(ex)))
        action = input("Action:")
        if action == 'l':
            _ = [print(f) for f in ex]
        elif action == 'o':
            ex = _convert(ex, force=True)
        elif action == 'x':
            break


def _convert(files, force):
    msg = "converting file {}/" + str(len(files)) + "..."
    converted = 0
    errors = []
    exists = []

    print_progress("Starting conversion...", final=True)
    for i, infile in enumerate(files):
        print_progress(msg, i + 1)
        f, e = os.path.splitext(infile)
        outfile = f + ".png"
        if not force and os.path.exists(outfile):
            exists += [infile]
        else:
            try:
                with Image.open(infile) as im:
                    im.save(outfile, "PNG", optimize=True)
                    converted += 1
            except OSError as e:
                errors += [e]

    print_progress(msg, len(files), final=True)
    print_progress("Conversion of {} files completed.", converted, final=True)

    if errors:
        for e in errors:
            print(e)
        print("There were {} errors, scroll up for details".format(len(e)))

    return exists


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract subtitles from video files recursively')
    parser.add_argument('path', type=str, help='Base directory')
    parser.add_argument('-e', '--ext', type=str, required=True, help='Extension of input files')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Search the file system recursively')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Existing conflicting png files will be overwritten')
    args = parser.parse_args()
    sys.exit(convert_to_png(**vars(args)))
