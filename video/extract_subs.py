#!/usr/bin/env python
""" Extracts subtitles from video files recursively starting from the specified directory """
import argparse
import json
import os
import sys
import langcodes

from ffmpeg import FFmpeg, Progress

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress

supported_video_formats = ["mkv", "mk3d", "mka", "mks", "webm",
                           "mp4", "m4a", "m4p", "m4b", "m4r", "m4v",
                           "mov", "movie", "qt"]

supported_sub_formats = ["srt", "ass", "ssa", "vtt"]


def extract_subs(lib_path: str, languages: list, sub_format='srt', force: bool = False, force_extras: bool = False,
                 force_undefined: bool = False) -> int:
    """ Extracts subtitles from video files recursively starting from the specified directory
    :param lib_path: Base directory from which subtitles will be extracted recursively
    :param languages: list of iso language codes representing languages that should be extracted
    :param sub_format: file extension format of the extracted sub file
    :param force: If True, will overwrite existing subtitle files
    :param force_extras: If True, subtitles of the same language without differentiating tags are extracted as "extra"
    :param force_undefined: If True, subtitles with undefined languages are extracted as "und"
    :return: 0 if the process ran successfully
    """

    # Check the input variables
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1
    sub_format = sub_format.lower() if sub_format.startswith('.') else '.' + sub_format.lower()
    if sub_format[1:] not in supported_sub_formats:
        print("Error - Subtitle format is not among the valid formats:" + str(supported_sub_formats))
        return 1

    for i in range(len(languages)):
        try:
            languages[i] = langcodes.standardize_tag(languages[i])
        except langcodes.tag_parser.LanguageTagError:
            print('Language code "{}" was not recognised. Use BCP 47 compliant codes.'.format(languages[i]))
            return 1

    # Find supported video files
    msg = "Scanning {} video files for subtitles to extract"
    video_files = []
    dir_count = 1  # Start at 1 for the base directory
    vid_count = 0
    ffprobe_errors = []
    for root, dirs, files in os.walk(lib_path, topdown=True):
        dirs[:] = [d for d in dirs if not d.endswith(".trickplay")]
        print_progress(msg, vid_count)
        for file in files:
            if _is_supported(file):
                vid_count += 1
                filepath = os.path.join(root, file)
                try:
                    extractables = _get_extractable_subs(filepath, languages, sub_format, force, force_extras, force_undefined)
                    if extractables:
                        video_files += [(filepath, extractables)]
                except Exception as e:
                    ffprobe_errors += [file + " " + str(e)]
        dir_count += len(dirs)
    print_progress(msg, vid_count, final=True)
    msg = "{} files needing subs extraction found among {} video files in {} directories"
    print_progress(msg, len(video_files), vid_count, dir_count, final=True)

    # Extract the subs
    errors = []
    to_review = []
    for file in video_files:
        base_file = os.path.splitext(file[0])[0]
        file_name = os.path.basename(file[0])
        ffmpeg = FFmpeg().option("y").input(file[0])
        msg = "Extracting subs from: {} "
        for sub in file[1]:
            output_file = base_file + sub[1]
            ffmpeg = ffmpeg.output(output_file, map=['0:{}'.format(sub[0])])
            if sub[2]:
                to_review +=[output_file]

        @ffmpeg.on("progress")
        def on_progress(progress: Progress):
            on_progress.count += 1
            if not on_progress.count % 5:
                print_progress(msg, file_name)
        on_progress.count = 0

        @ffmpeg.on("completed")
        def on_completed():
            print_progress(msg, file_name, final=True)

        try:
            ffmpeg.execute()
        except Exception as e:
            errors += [file_name + " " + str(e)]
            print_progress(errors[-1], final=True)

    print_progress("Subtitle extraction completed", final=True)

    if len(to_review):
        print("\nThe following subtitles have undefined properties and need to be reviewed:")
        [print(e) for e in to_review]

    if len(errors):
        print("\n{} errors encountered when running ffprobe".format(len(ffprobe_errors)))
        [print(e) for e in ffprobe_errors]
        print("\n{} errors occurred during extraction".format(len(errors)))
        [print(e) for e in errors]

    return 0


def _get_extractable_subs(file: str, languages: list, sub_format: str, force: bool, force_extras: bool, force_undefined: bool) -> list:
    """ Check for subtitles matching the desired languages in the video file and if they have already been extracted
    :param file: Path to the video file
    :param languages: list of iso language codes that should be extracted
    :param sub_format: file extension format for the extracted sub file
    :param force: If True, will overwrite existing subtitle files
    :param force_extras: If True, subtitles of the same language without differentiating tags are extracted as "extra"
    :param force_undefined: If True, subtitles with undefined languages are extracted as "und"
    :return: List of tuples [(stream_index, extension, user_review_needed)] representing extractable subs streams,
            the extension to use when writing the sub file and if user review is needed for special cases
    """
    base_file = os.path.splitext(file)[0]
    ffprobe = FFmpeg(executable="ffprobe").input(file, print_format="json", show_streams=None)
    meta = json.loads(ffprobe.execute())
    extractables = []
    extensions = []
    for stream_index, stream in enumerate(meta['streams']):
        if (stream['codec_type'].lower() == "subtitle"
                and 'dvd' not in stream['codec_name'].lower())\
                and 'hdvm' not in stream['codec_name'].lower()\
                and 'pgs' not in stream['codec_name'].lower():

            lang_code = "und"  # Standard code for undefined language
            if 'language' in stream['tags']:
                try:
                    if langcodes.Language.get(stream['tags']['language']).is_valid():
                        lang_code = langcodes.standardize_tag(stream['tags']['language'])
                except langcodes.tag_parser.LanguageTagError:
                    pass

            user_review_needed = True if lang_code == "und" else False

            if (force_undefined and lang_code == "und") or lang_code in languages:
                extension = "." + lang_code
                if 'title' in stream['tags']:
                    stream_title = stream['tags']['title'].lower()
                    if "sdh" in stream_title:
                        extension += '.sdh'
                    elif "cc" in stream_title:
                        extension += '.cc'
                    if "forced" in stream_title:
                        extension += '.forced'
                    if "foreign" in stream_title:
                        extension += '.foreign'
                extension += sub_format

                # If several subs of the same language exist, we can extract them as extras
                if force_extras and extension in extensions:
                    extension += '.extra{}'.format(stream_index)
                    user_review_needed = True

                if extension not in extensions:
                    if force or not os.path.exists(base_file + extension):
                        extractables += [(stream_index, extension, user_review_needed)]
                        extensions += [extension]

    return extractables


def _is_supported(file: str):
    """ Check if the file is of a supported format for subtitle extraction """
    return (file.split(".")[-1]).lower() in supported_video_formats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract subtitles from video files recursively')
    parser.add_argument('lib_path', type=str, help='Base directory')
    parser.add_argument('-l', '--languages', type=str, nargs='+', required=True,
                        help='list of iso language codes representing languages that should be extracted')
    parser.add_argument('-s', '--sub-format', type=str, default='srt',
                        help='File extension format for the extracted subtitles')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Existing subtitle files will be overwritten')
    parser.add_argument('-fe', '--force-extras', action='store_true',
                        help='Subtitles of the same language without differentiating tags are extracted as "extra"')
    parser.add_argument('-fu', '--force-undefined', action='store_true',
                        help='Subtitles with undefined languages are extracted as "und"')
    args = parser.parse_args()
    sys.exit(extract_subs(**vars(args)))
