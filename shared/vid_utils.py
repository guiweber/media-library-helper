""" Shared video related functions for the other modules """

import langcodes
import os
import re


def get_vids_extra_tags():
    """ Returns a list of tags which indicate that a video file is "extra" when at the end of the file name """
    return ["trailer", "sample", "-scene", "-clip", "-interview", "-behindthescenes", "-deleted",
            "-deletedscene", "-featurette", "-short", "-other", "-extra"]


def get_sub_tags_from_file_name(filename):
    """ Determines the tags from the name of a subtitle file, assuming language is the first tag and a maximum of 4 tags
    :param filename: The name of the file
    :return: A list of tags or an empty list if the language wasn't found. The language is always the first tag in the list.
    """
    lang = ''
    tags = []
    full_text_tags = []
    parts = os.path.splitext(filename)[0].split(".")
    for i, part in enumerate(reversed(parts)):
        # Check the supported tags first as there are collisions with languages (such as sdh)
        part = part.lower()
        if part in get_supported_sub_tags():
            if part not in tags:
                tags += [part]
        elif not lang:
            if len(part) <= 3:
                try:
                    if langcodes.Language.get(part).is_valid():
                        lang = langcodes.standardize_tag(part)
                except langcodes.tag_parser.LanguageTagError:
                    pass
            else:
                # Is a full language name used?
                try:
                    lang = langcodes.find(part).to_tag()
                    # In this case full text tags may also be in the same tag
                    if "-forced" in part:
                        full_text_tags += ["forced"]
                    if "-foreign" in part:
                        full_text_tags += ["foreign"]
                    if re.search("hearing.?impaired", part) or "-sdh" in part:
                        full_text_tags += ["sdh"]
                except LookupError:
                    pass

        # Max of 4 tags
        if i >= 3:
            break

    if lang:
        for t in full_text_tags:
            if t not in tags:
                tags += [t]
        return [lang] + tags
    else:
        return []


def get_supported_sub_tags():
    """ Returns a list of the supported sub tags """
    return ["sdh", "cc", "forced", "foreign", "default"]


def get_supported_sub_extensions():
    """ Returns a list of all """
    return ["srt", "ass", "ssa", "vtt", "sub"]


def get_supported_video_extensions():
    """ Returns a list of all video file extensions """
    return ["mkv", "mk3d", "mka", "mks", "webm",
            "mp4", "m4a", "m4p", "m4b", "m4r", "m4v",
            "mpg", "mp2", "mpeg", "mpe", "mpv", "m2v",
            "mov", "movie", "qt",
            "avi", "divx", "wmv",
            "ogv", "ogg", "vob"]
