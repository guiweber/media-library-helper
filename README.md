# media-library-helper
A collection of scripts to help me manage my media library and maintain the file structure required by Jellyfin (and possibly also Emby/Plex).

:warning: Some of these scripts can modify and potentially remove files. As of now, they are not thoroughly tested. 
Make sure you have backups and understand the code before using it, and do so at your own risks.

## Requirements
In addition to the modules in _requirements.txt_, these should be installed and added to your PATH:
- ffmpeg
- flac

Some scripts use spacy for natural language processing and models need to be downloaded separately for each language
https://spacy.io/models
```bash
python -m spacy download en-core-web-trf
```
Note that transformer (trf) models are highly recommended to get acceptable results. Those models require PyTorch, 
which may take a while to be available on the latest version of Python. In case of installation issues, 
revert to a previous version of Python. 

## Structure
The scripts are sorted into folder depending on the type of files they act on
- __audio__
  - ```reencode_flac```: Reencodes Flac files in place if they have been encoded with older versions of FLAC


- __fs__ (file system)
  - ```FileSet```: Class for quick, reusable, in-memory name-based file search, and folder comparison using set operations.  
  - ```find_empty_dirs```: Finds directories that are empty and optionally removes them. Can also ignore small or hidden files.


- __video__
  - ```clean_subs```: Removes common advertisement strings as well as formatting tags from subtitle files. Also attempts to detect ALL-CAPS subtitles and to apply grammatically correct capitalization.
  - ```extract_subs```: Extracts text based subtitles from video files and saves them as .srt.
  - ```match_subs```: Renames and relocate subtitles to match their associated video file and comply with tagging standards. Also finds dangling subtitle files. 


- __shared__: functions meant to be used by other scripts and not by the end user

## Importing
The modules can be imported as follows:

```python
from video.extract_subs import extract_subs
```

## To run from CLI under windows
Add the path to media-library-helper to a `PYTHONPATH` environment variable in Windows, and then you can run with, for example:

```bash
python -m audio.reencode_flac arguments
```
