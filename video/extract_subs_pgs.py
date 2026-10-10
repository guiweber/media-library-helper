import os
import pgsrip
import re
import srt
import sys
from babelfish import Language

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress
from fs.FileList import FileList
from shared.vid_utils import read_srt_file, get_sub_tags_from_file_name

def extract_pgs_subs(path, languages: list, clean_OCR: bool = True, force: bool = False):
    """ Extracts PGS subtitles, converting them to SRT, from video files recursively starting from the specified directory
    :param path: Base directory from which subtitles will be extracted recursively
    :param languages: list of two-letter language codes (ISO 639-1) that should be extracted
    :param clean_OCR: performs post-extraction cleanup to correct common OCR specific errors
    :param force: If True, will overwrite existing subtitle files
    :return: 0 if the process ran successfully
    """

    languages = [Language.fromalpha2(l) for l in languages]
    options = pgsrip.Options(languages=languages, force=force)
    subtitles = [
        subtitle
        for media in pgsrip.scan(path, options).media
        for subtitle in pgsrip.pending(media.subtitles(options), options)
    ]
    pgsrip.prepare(subtitles, options, reporter=print)
    for subtitle in subtitles:
        try:
            print(f"Extracting PGS {str(subtitle)}")
            pgsrip.rip(subtitle, options)
        except Exception as e:
            print(f"Error extracting PGS ({str(subtitle)}): {str(e)}")

    if clean_OCR:
        clean_subs_pgs(path)

def clean_subs_pgs(path):
    """Cleans common OCR specific errors from the srt files found in path"""
    files = FileList.build(path, recursive=True, ext_filter=['srt'], )
    res = []
    for i in files:
        try:
            res += _clean(i, False)
        except Exception as e:
            print(f"Error cleaning str file (PGS sub clean): {str(e)}")

def _clean(filepath, ignore_parse_errors):
    """Cleans common OCR specific errors from the specified srt file"""
    subs, result = read_srt_file(filepath, ignore_parse_errors)
    if not subs:
        return result

    remove = []
    tags = get_sub_tags_from_file_name(filepath)
    if len(tags):
        lang = tags[0]
    else:
        lang = ''
        print(f"Error: Could not identify language tag for file: {filepath}")

    for i, sub in enumerate(subs):
        if re.match(r'^\s*$', sub.content) is not None:
            # Removes empty strings
            remove += i
        else:

            # Add a space after initial dash
            sub.content = re.sub(r'^-([^\s].*)$', r"- \1", sub.content, flags=re.MULTILINE)

            # Musical note character replacements - unspecific
            sub.content = re.sub(r'[JIT&7]»', r'♪', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^[JIT»&7iy]{2,3}$', r'♪♪', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^[»>]$', r'♪♪', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^(-\s)?[JIT»&7](\s.*\s)[JIT»&7]$', r'\1♪\2♪', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^(-\s)?[JT»&](\s.*)$', r'\1♪\2', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^(.*\s)[JIT»&]$', r'\1♪', sub.content, flags=re.MULTILINE)

            # Musical note character replacements - specific expressions
            expressions = r'&\'|Ji'
            sub.content = re.sub(r'^(-\s)?(?:{})(\s.*)$'.format(expressions), r'\1♪\2', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'^(.*\s)(?:{})$'.format(expressions), r'\1♪', sub.content, flags=re.MULTILINE)

            # Make sure notes have spaces before and after them
            sub.content = re.sub(r'([^\s♪])♪', r'\1 ♪', sub.content, flags=re.MULTILINE)
            sub.content = re.sub(r'♪([^ \s♪])(?!$)', r'♪ \1', sub.content, flags=re.MULTILINE)

            # Remove empty dialogue lines
            sub.content = re.sub(r'^[-]$', r'', sub.content, flags=re.MULTILINE)

            if lang == "fr":
                sub.content = re.sub(r'(?:(?<=^)|(?<=\s))[I\|\[\]\/!1]\s?[l\|\[\]\/!1]', r'Il', sub.content, flags=re.MULTILINE)

            # removes remaining unwanted characters
            sub.content = sub.content.replace(';', '')

    # Remove any entries flagged for removal
    if remove:
        subs = [s for i, s in enumerate(subs) if i not in remove]

    with open(filepath, "w", encoding='utf-8-sig') as f:
        f.write(srt.compose(subs, reindex=True))

    # Modifications are not tracked for PGS cleanups so all files are assumed modified
    result['modified'] = True

    return result

