#!/usr/bin/env python
import argparse
import langcodes
import os
import re
import sys

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress
from shared.vid_utils import (get_sub_tags_from_file_name, get_supported_video_extensions,
                              get_supported_sub_extensions, get_vids_extra_tags)
from fs.find_empty_dirs import find_empty_dirs


def match_subs(lib_path: str, supported_languages=[], default_language='', apply_changes=False, remove_empty=True):
    """ Matches subtitle files to video files in the same or parent folders. If necessary, moves them to the video
        file folder, renames and tags them according to the jellyfin external file tagging standard.
        (https://jellyfin.org/docs/general/server/media/external-files/)

        Files where the language cannot be determined will be displayed as "unmatched" unless a default language is provided.

        If no subtitle name tags are already present, basic rules are used to determine SDH, Forced and Foreign subs,
        but the results should be reviewed as there is a high chance of misslabeling.

    :param lib_path: Base directory from which the process will be started
    :param supported_languages: List of BCP-47 languages codes, specifying the languages to process.
                                If the list is empty, all languages will be processed.
    :param default_language: If a BCP-47 language code is specified, it will be used when the language of a subtitle
                             file cannot be determined
    :param apply_changes: If True, files will be moved/renamed. If False, changes are only printed to the console
    :param remove_empty: If True and apply_changes is also true, empty directories will be removed
    :return: 0 if the process ran successfully
    """
    # Check the input variables
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1

    for i in range(len(supported_languages)):
        try:
            supported_languages[i] = langcodes.standardize_tag(supported_languages[i])
        except langcodes.tag_parser.LanguageTagError:
            print('Language code "{}" was not recognised. Use BCP 47 compliant codes.'.format(supported_languages[i]))
            return 1

    if default_language:
        try:
            if langcodes.Language.get(default_language).is_valid():
                default_language = langcodes.standardize_tag(default_language)
            else:
                print('Language code "{}" was not recognised. Use BCP 47 compliant codes.'.format(default_language))
                return 1
        except langcodes.tag_parser.LanguageTagError:
            print('Language code "{}" was not recognised. Use BCP 47 compliant codes.'.format(default_language))
            return 1

    msg = ("Scanned {} subtitles files of which {} need to be moved/renamed, and {} ambiguous files. "
           "A total of {} files could not be matched and were not modified.")
    sub_count = 0
    modified = []
    unmatched = []
    errors = []
    missing_lang = []
    ambiguous = []
    for sub_root, dirs, files in os.walk(lib_path):
        print_progress(msg, sub_count, len(modified), len(ambiguous), len(unmatched))
        for file in files:
            file_path = os.path.join(sub_root, file)
            file_base, file_ext = os.path.splitext(file)
            file_ext = file_ext[1:].lower()
            if file_ext in get_supported_sub_extensions():
                sub_count += 1

                # Find video files that can be matched to the sub file
                vid_root = find_vids(sub_root)
                match = match_vid(sub_root, vid_root, file_base)

                if not match:
                    unmatched += ["Unmatched : " + file_path]
                else:
                    # If a match exists, find the file language and other name tags
                    tags, ambiguous_sub = get_sub_tags(sub_root, file_base, file, match)
                    if not tags:
                        missing_lang += ["Missing language tag: " + os.path.join(sub_root, file)]
                    elif supported_languages and tags[0] not in supported_languages:
                        unmatched += ["Unmatched languages ({}): ".format(tags[0]) + file_path]
                    else:
                        # Use the match and tags to determine the target location of the file
                        move_to = os.path.join(vid_root, ".".join([match] + tags + [file_ext]))
                        if move_to != file_path:
                            if os.path.exists(move_to):
                                errors += ["Error: {} ==> New destination already exists: {}".format(file_path, move_to)]
                            else:
                                if ambiguous_sub:
                                    ambiguous += [(file_path, move_to)]
                                else:
                                    modified += [(file_path, move_to)]

    print_progress(msg, sub_count, len(modified), len(ambiguous), len(unmatched), final=True)

    [print("Modified: " + x[0] + "  ----->>>  " + x[1]) for x in modified]
    [print("Modified (ambiguous) : " + x[0] + "  ----->>>  " + x[1]) for x in ambiguous]
    if apply_changes:
        for x in modified:
            try:
                os.replace(x[0], x[1])
            except Exception as e:
                errors += [x[0] + " --> " + str(e)]

        for x in ambiguous:
            try:
                os.replace(x[0], x[1])
            except Exception as e:
                errors += [x[0] + " --> " + str(e)]

    for i in [unmatched, missing_lang, errors]:
        print()
        [print(x) for x in i]

    if modified or unmatched or ambiguous or errors or missing_lang:
        print_progress(msg, sub_count, len(modified), len(ambiguous), len(unmatched), final=True)

    if apply_changes and remove_empty:
        find_empty_dirs(lib_path, ignore_hidden=False, ignore_size=0, remove='yes')

    return 0


def contains_vids(path):
    """ Scans a directory for video files and returns True if any is found """
    for f in os.listdir(path):
        if is_vid(path, f):
            return True
    return False


def find_vids(root):
    """ Finds the closest folder with videos that are not extras, going one or two level above the root folder """

    if contains_vids(root):
        return root
    else:
        parent = os.path.dirname(root)
        # If we're in a subtitle folder, go one level above
        if parent.lower().endswith("subs"):
            parent = os.path.dirname(parent)

        if contains_vids(parent):
            return parent

    return ''


def get_sub_tags(sub_root, file_base, file, match):
    """ Returns a list of tags that should be appended to the sub file name, and the ambiguous marker i"""

    # Remove the video file name from the sub file name to prevent parts from being seen as tags
    if file.startswith(match):
        subs_specific_name = file[len(match):]
        split_name = subs_specific_name.split(".")
        # Is it more than an extension? Is the first part not empty or longer than 2 (in case it starts with a ".")
        if subs_specific_name.split(".")[0] or len(split_name) > 2:
            tags = get_sub_tags_from_file_name(subs_specific_name)
        else:
            tags = []
    else:
        tags = get_sub_tags_from_file_name(file)

    ambiguous = False
    # Check for an alternate common formatting for extracted subs
    if not tags and re.fullmatch('[0-9]*_[a-zA-Z]*', file_base):
        lang = file_base.split("_")[1]
        try:
            if langcodes.Language.get(lang).is_valid():
                tags = [langcodes.standardize_tag(lang)]
        except langcodes.tag_parser.LanguageTagError:
            pass

        # Check for a full language name
        if not tags:
            try:
                tags = [langcodes.find(lang).to_tag()]
            except LookupError:
                pass

        #  There may be multiples files with the same languages in this case, try to determine what they are
        if tags:
            subs = [f for f in os.listdir(sub_root)
                    if os.path.splitext(f)[1][1:].lower() in get_supported_sub_extensions()
                    and re.match('[0-9]*_{}*'.format(lang), f)]

            if len(subs) > 1:
                sizes = [os.path.getsize(os.path.join(sub_root, f)) for f in subs]
                files_and_sizes = sorted(list(zip(sizes, subs)), key=lambda x: x[0])
                for i in range(len(files_and_sizes)):
                    if file_base in files_and_sizes[i][1]:
                        current_sub_index = i
                        break

                max_size = max(sizes)
                n_large_subs = len([True for s in sizes if s > max_size/3])
                n_small_subs = len(sizes) - n_large_subs

                # Is the sub much smaller than the max, they are ambiguous but we try to determine the first two
                if n_small_subs and files_and_sizes[current_sub_index][0] <= max_size/3:
                    ambiguous = True
                    if current_sub_index == 0:
                        tags += ['forced']
                    elif current_sub_index == 1:
                        tags += ['foreign']
                    else:
                        tags = []
                else:
                    # Max size is sdh if there is more than one large sub
                    if n_large_subs > 1 and current_sub_index == len(files_and_sizes) - 1:
                        tags += ['sdh']
                    # Normal is first of second
                    elif current_sub_index <= len(files_and_sizes) - 2:
                        pass
                    # Any additional large subs are not processed
                    else:
                        tags = []

    return tags, ambiguous


def get_vids(path):
    """ Get a lit of supported video files without file extensions"""
    return [os.path.splitext(f)[0] for f in os.listdir(path) if is_vid(path, f)]


def is_vid(path, file):
    """ Returns true if the file is a full supported video """
    base, ext = os.path.splitext(file)
    return (os.path.isfile(os.path.join(path, file))
            and ext[1:].lower() in get_supported_video_extensions()
            and not any(base.endswith(x) for x in get_vids_extra_tags()))


def list_item_in_str(str_list, string):
    """ Returns the first element from the list that is present in the string, or an empty string if there is no match
    """
    for s in str_list:
        if s in string:
            return s

    return ''


def match_vid(sub_root, vid_root, file_base):
    """ Tries to match a subfile to a video file, returns the matching file name without extension if found"""
    match = ''
    if vid_root:
        vids = get_vids(vid_root)
        if vids:

            # Check for a perfect match
            match = list_item_in_str(vids, file_base)

            # If no perfect match, try to find a match and rename the sub file
            if not match:

                # If there is only one vid, we assume it's a match
                if len(vids) == 1:
                    match = vids[0]
                # If there are many vids, check if any match the subs top level directory
                else:
                    sub_dir = os.path.basename(sub_root)
                    match = list_item_in_str(vids, sub_dir)

                    # If there is still no match, try to match with season/episode markers
                    if not match:
                        lookup = re.search('([sS][0-9]{2})[.-_]?([eE][0-9]{2})', file_base + sub_dir)
                        if lookup:
                            lookup = '{}[.-_]?{}'.format(lookup.group(1), lookup.group(2))
                            for v in vids:
                                res = re.search(lookup, v)
                                if res:
                                    match = res.group()

    return match


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reencodes flac files recursively from the specified directory')
    parser.add_argument('lib_path', type=str, help='Base directory')
    args = parser.parse_args()
    sys.exit(match_subs(**vars(args)))
