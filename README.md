# media-library-helper
A collection of scripts to help me manage my media library

## Requirement
In addition to the modules in _requirements.txt_, these should be installed and added to your PATH:
- ffmpeg
- flac

Some scripts use spacy for natural language processing and models need to be downloaded separately for each language
https://spacy.io/models
```
python -m spacy download en-core-web-trf
```
Note that transformer (trf) models 

## Structure
The scripts are sorter into folder depending on the type of files they manipulate
- audio
- video
- shared (functions meant to be used by other scripts and not by the end user)

## To run from CLI under windows
Add the path to media-library-helper to a `PYTHONPATH` environment variable in Windows, and then you can run with, for example:

```
python -m audio.reencode_flac arguments
```
