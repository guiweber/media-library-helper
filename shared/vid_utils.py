""" Shared video related functions for the other modules """

import langcodes
import os


def get_sub_language_from_file_name(filename):
    """ Determines the language of a sub file based on standard language tags in the file name
    :param filename: The name of the file
    :return: The language code or an empty string if the code wasn't found
    """
    parts = os.path.splitext(filename)[0].split(".")
    for p in reversed(parts):
        if len(p) <= 3:
            try:
                return langcodes.standardize_tag(p)
            except langcodes.tag_parser.LanguageTagError:
                pass
    return ''
