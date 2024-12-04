""" Contains unwanted strings used by clean_subs.py.
    Each entry of the dictionary is a dictionary with two parts, 'early' and 'late'.
    'early' entries are only added to the 'late' entries at the very beginning and end of a sub file.
    'late' entries are checked in for a larger number of subs, but should be more restrictive to avoid detecting
     wanted subtitles as unwanted. """


dirty_strings = dict()

# English
dirty_strings["en"] = dict()
dirty_strings["en"]["early"] = [
    "captioning sponsored",
    "captioned by",
    "clearway law",
    "downloaded from",
    "encoded by",
    "encoded vid",
    "english - us",
    "movies site",
    " release",
    "ripped by",
    " sdh",
    "subtitle",
    "subs by",
    "upped by",
    "uploaded by",
    "www.",
    ".com",
    ".org",
    ".net",
    "@",
    "-=",
    "==",
    "--",
    "**"
]

dirty_strings["en"]["late"] = [
    "opensubtitles",
    "subtitle by",
    "subtitles by"
]

# French
dirty_strings["fr"] = dict()
dirty_strings["fr"]["early"] = [
    "traduit par",
    "traduction",
    "corrections"
]

dirty_strings["fr"]["late"] = [
    "sous-titre par",
    "sous-titres par",
    "sous-titre de",
    "sous-titres de",
    "sous-titrage",
    "vostfr"
]

# Swedish
dirty_strings["sv"] = dict()
dirty_strings["sv"]["early"] = [
    "översättning"
]

dirty_strings["sv"]["late"] = []


