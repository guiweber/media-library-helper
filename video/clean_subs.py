#!/usr/bin/env python
import argparse
import os
import re
import spacy
import srt
import sys
import langcodes

# Allow relative import from shared folder as per PEP 366
if __name__ == "__main__" and __package__ is None:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)
    __package__ = "media-library-helper"

from shared.utils import print_progress
from shared.vid_utils import get_sub_tags_from_file_name
from video.clean_subs_string_data import dirty_strings

supported_sub_formats = ["srt"]
_spacy_models = dict()


def clean_subs(lib_path: str, spacy_models, spacy_models_languages, force_cap=False, force_tags=False, ignore_parse_errors=False, keep_dirty=True):
    """ Clean common unwanted strings from subtitles recursively from the specified directory.
        For full functionality, subtitles files need to be named following the jellyfin external file tagging standard
        (https://jellyfin.org/docs/general/server/media/external-files/), with a 2 or 3 letter language code
        :param lib_path: Base directory from which the process will be started
        :param spacy_models: List of spacy models to use for language processing
        :param spacy_models_languages: List of language codes for the language models
        :param force_cap: If True, forces recapitalization of the text for all subs (very slow)
        :param force_tags: If True, forces tag removal for all subs (slow)
        :param ignore_parse_errors: If True, srt parse errors will be ignored.
                                    Note that this can delete data from your file if,
                                    for example, the wrong file encoding was used.
        :param keep_dirty: If True, dirty subs will be kept in addition to the cleaned subs, but their extension
                           will be changed to .dirty
        :return: 0 if the process ran successfully
        """

    # Check the input variables
    if not os.path.isdir(lib_path):
        print("Error - Not a valid directory: " + lib_path)
        return 1

    assert len(spacy_models) == len(spacy_models_languages), "Number of models and languages not the same"
    for i in range(len(spacy_models)):
        #  Store the model string for now, the model is loaded only if needed
        _spacy_models[langcodes.standardize_tag(spacy_models_languages[i])] = spacy_models[i]

    # Find subtitles and clean them
    msg = "Scanned {} subtitles files of which {} have been modified"
    sub_count = 0
    changed = []
    errors = []
    for root, dirs, files in os.walk(lib_path, topdown=True):
        dirs[:] = [d for d in dirs if not d.endswith(".trickplay")]
        print_progress(msg, sub_count, len(changed))
        for file in files:
            file_ext = os.path.splitext(file)[1][1:].lower()
            if file_ext in supported_sub_formats:
                sub_count += 1
                filepath = os.path.join(root, file)
                res = _clean(file, filepath, force_cap, force_tags, msg, [sub_count, len(changed)], ignore_parse_errors, keep_dirty)
                if res["modified"]:
                    changed += [filepath]
                if res["language_missing"]:
                    errors += ["Could not capitalize file due to missing language model or undetermined file language: "
                               + filepath]
                if res['file_error']:
                    errors += ["Could not find encoding needed to open file :" + filepath]
                if res['file_empty']:
                    errors += ["File seems empty :" + filepath]
                if res['parse_error']:
                    errors += ["Parse error in file while using encoding {}. "
                               "Try converting file to UTF-8 before ignoring parse errors. :".format(res['parse_error']) + filepath]

    print_progress(msg, sub_count, len(changed), final=True)
    print("All subtitles cleaned!")
    print()
    print("{} errors occurred:".format(len(errors)))
    [print(e) for e in errors]
    print("{} files cleaned:".format(len(changed)))
    [print(c) for c in changed]

    if keep_dirty and changed:
        print("Original dirty subs have been kept for review. Their extension have been changed to '.dirty'")

    return 0


def capitalize(sub, new_sentence, language):
    """ Capitalizes a subtitle according to grammatical rules
    :param sub: A subtitle object
    :param new_sentence: Bool indicating if the sub starts a new sentence, based on the punctuation of previous sub.
    :param language: Language code indicating which spacy model to use
    :return: A tuple (capitalized subtitle object, bool new sentence indicator)
    """

    # Punctuation marks that indicate the end of a sentence
    punctuation = ['.', '!', '?', ':', '(', ')', '[', ']']
    # Colons are most used to show who speaks while brackets may be used for identifying
    # characters or background sounds. Other punctuation may be missing before a new sentence starts.
    # "..." is not used as it is sometimes used to indicate that the sentence continues in the next subtitle

    tokens = _spacy_models[language](sub.content)
    sub.content = ""
    # Capitalize only proper nouns and the first word of sentences
    for i, token in enumerate(tokens):
        if (new_sentence or token.pos_ == 'PROPN') and (token.is_alpha or _is_alpha_like(token.text)):
            sub.content += token.text_with_ws.capitalize()
            new_sentence = False
        else:
            # Is the next word in a new sentence?
            if token.text in punctuation:
                sub.content += token.text_with_ws
                new_sentence = True
            # Capitalize I properly in english
            elif language == 'en' and (token.text.lower() == "i" or "i'" in token.text.lower()):
                sub.content += token.text_with_ws.capitalize()
            else:
                # Call lower() to be safe, some tokens containing letters may seep through the condition above
                sub.content += token.text_with_ws.lower()

    return sub, new_sentence


def _clean(file, filepath, force_cap, force_tags, progress_msg, msg_args, ignore_parse_errors, keep_dirty):

    # Init variables
    result = dict()
    result['capitalized'] = False
    result['file_error'] = False
    result['file_empty'] = False
    result['language_missing'] = False
    result['modified'] = False
    result['removed_tags'] = False
    result['parse_error'] = False

    encodings = ['utf-8-sig', 'utf-16', 'cp1252', 'ISO-8859-1']
    subs = ""

    # Try the most common file encoding to open the file
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                subs = f.read()
            break
        except Exception:
            pass

    if not subs:
        result['file_error'] = True
        return result

    # Try to parse the subtitle file, if it fails parse with ignore_errors flags and mark the file as modified
    try:
        subs = list(srt.parse(subs))
    except srt.SRTParseError:
        if ignore_parse_errors:
            subs = list(srt.parse(subs, ignore_errors=True))
            result['modified'] = True
        else:
            result['parse_error'] = enc
            return result

    # Initial quick clean only checks the first and last two subs for forbidden strings
    start_index = 0
    end_index = len(subs)
    if end_index == 0:
        result['file_empty'] = True
    else:
        if end_index > 3 and _is_dirty(subs[2].content):
            start_index = 3
        elif end_index > 2 and _is_dirty(subs[1].content):
            start_index = 2
        elif end_index > 1 and _is_dirty(subs[0].content):
            start_index = 1

        if end_index > 5 and _is_dirty(subs[-3].content):
            end_index = -3
        elif end_index > 4 and _is_dirty(subs[-2].content):
            end_index = -2
        elif end_index > 3 and _is_dirty(subs[-1].content):
            end_index = -1

    if start_index != 0 or end_index != len(subs):
        subs = subs[start_index:end_index]
        result['modified'] = True

    # Check the first 40 subs with a more limited range of strings, as sometimes ads are inserted there too...
    dirty_subs = []
    for i in range(min(40, len(subs))):
        if _is_dirty(subs[i].content, late=True):
            dirty_subs += [i]
    if dirty_subs:
        subs = [sub for i, sub in enumerate(subs) if i not in dirty_subs]
        result['modified'] = True

    # Check the first subs to see if they are all-caps or all contain font tags,
    # Sometimes, only a portion of subs are affected so check many
    all_caps = 0
    unwanted_tags = 0
    for i in range(min(30, len(subs))):
        if _is_all_caps(subs[i].content):
            all_caps += 1
        if not unwanted_tags and _has_unwanted_tags(subs[i].content):
            unwanted_tags += 1

    if all_caps > 10 or force_cap:
        long_process = " - {} needs deep cleaning {}/{}"
        new_sentence = True
        tags = get_sub_tags_from_file_name(file)
        if tags and _load_spacy_model(tags[0]):
            total = len(subs)
            for i, sub in enumerate(subs):
                print_progress(progress_msg + long_process.ljust(45), *msg_args, file, i, total)
                subs[i], new_sentence = capitalize(sub, new_sentence, tags[0])
            result['modified'] = True
            result['capitalized'] = True
        else:
            result['language_missing'] = True
    if unwanted_tags or force_tags:
        subs = [_remove_unwanted_tags(sub) for sub in subs]
        result['modified'] = True
        result['removed_tags'] = True

    # Write the new subtitle file
    if result['modified']:
        if keep_dirty:
            os.replace(filepath, filepath + ".dirty")
        with open(filepath, "w", encoding='utf-8-sig') as f:
            f.write(srt.compose(subs, reindex=True))

    return result


def _get_dirty_strings(late):
    """ Returns a list of dirty strings to compare against subs content """
    if not _get_dirty_strings.dirty_strings:
        global dirty_strings
        for lang, subdict in dirty_strings.items():
            for type, dirtlist in subdict.items():
                _get_dirty_strings.dirty_strings += dirtlist
                if type == 'late':
                    _get_dirty_strings.dirty_strings_late += dirtlist
    if late:
        return _get_dirty_strings.dirty_strings_late
    else:
        return _get_dirty_strings.dirty_strings
_get_dirty_strings.dirty_strings = []
_get_dirty_strings.dirty_strings_late = []


def _has_unwanted_tags(content):
    """ Checks if a subtitle has unwanted formatting tags """
    return re.match(r'</?font.*?>', content) or re.match(r'</?b>', content)


def _is_all_caps(content):
    """ Checks if a subtitle is all caps, excluding any potential formatting tag
    :param content: Content of a subtitle
    :return: True if the content is all caps
    """
    # Remove any possible HTML tags
    content = re.sub(r'<.*?>', '', content)
    return content.isupper()


def _is_alpha_like(text):
    """ Checks if a string is composed of only apostrophes and letters, with at least one letter """
    return all(char.isalpha() or char == "'" for char in text) and len(text) > 1


def _is_dirty(content, late=False):
    """ Checks that none of the disallowed "dirty" strings are found in a subtitle
    :param content: Content of a subtitle
    :param late: Only use the more limited 'late' set of dirty strings
    :return: True if a dirty string was found in the content
    """

    # Sometimes dirt may be hidden - split by some tags, so remove them
    content = re.sub(r'<.*?>', '', content).lower()

    # Check if the content is dirty
    for dirt in _get_dirty_strings(late=late):
        if type(dirt) == tuple:
            if (dirt[0] == 'surround'
                    and len(content) > 2*len(dirt[0])
                    and content.startswith(dirt[0])
                    and content.endswith(dirt[0])):
                return True
        elif dirt in content:
            return True
    return False


def _load_spacy_model(lang):
    """Try loading a Spacy model for the specified language.
    :param lang: language code
    :return: Returns True if a model is present and loaded or False otherwise
    """
    if lang in _spacy_models:
        # Load the model on first use
        if type(_spacy_models[lang]) is str:
            _spacy_models[lang] = spacy.load(_spacy_models[lang])
        return True
    else:
        return False


def _remove_unwanted_tags(sub):
    """ Remove unwanted tags from a subtitle """
    content = sub.content
    content = re.sub(r'</?font.*?>', '', content)
    content = re.sub(r'</?b>', '', content)

    sub.content = content
    return sub


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reencodes flac files recursively from the specified directory')
    parser.add_argument('lib_path', type=str, help='Base directory')
    parser.add_argument('-m', '--models', type=str, nargs='+', help='list of spacy language models')
    parser.add_argument('-l', '--languages', type=str, nargs='+', help='language codes of the models')
    parser.add_argument('-fc', '--force_cap', action='store_true', help='Forces capitalizing the text (very slow)')
    parser.add_argument('-ft', '--force_tag', action='store_true', help='Forces tag removal (slow)')
    parser.add_argument('-i', '--ignore_parse_errors', action='store_true',
                        help='Ignore parsing errors when reading the srt file. Note that this can delete data from '
                             'your file if, for example, the wrong file encoding was used.')
    args = parser.parse_args()
    sys.exit(clean_subs(**vars(args)))
