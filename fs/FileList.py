import os
from pathlib import Path

class MutablePath():
    def __init__(self, path):
        path = Path(path)
        self.parent = path.parent
        self.stem : str = path.stem
        self._suffix : str = path.suffix

    def __str__(self):
        return str(self.full_path())

    @property
    def name(self):
        return self.stem + self.suffix

    @property
    def suffix(self):
        return self._suffix

    @suffix.setter
    def suffix(self, value : str):
        if len(value) and not value.startswith("."):
            self._suffix = "." + value
        else:
            self._suffix = value

    def full_path(self):
        return self.parent / (self.stem + self.suffix)


class FileList:
    """ Simple class to collect and filter files from the file system """

    def __init__(self, paths, root_dirs):
        """ Internal constructor, use the class method FileSet.build() to instantiate. """
        self._paths = paths
        self._root_dirs = root_dirs

    @classmethod
    def build(cls, root_dirs, recursive=True, ext_filter=[], disp=False):
        """ Builds a FileList object from the provided parameters.

        :param recursive: Bool, search fo files recursively if True
        :param root_dirs: List, Set or Str. Path(s) to directories from which to build the file list.
        :param ext_filter: List of file extensions to accept
        :param disp: Bool, if True, prints the list when done.
        :return: FileList representing the content of the root directories.
        """

        if isinstance(root_dirs, list):
            root_dirs = set([Path(p) for p in root_dirs])
        if isinstance(root_dirs, str):
            root_dirs = set([Path(root_dirs)])

        # sanitize extension filter
        for i in range(len(ext_filter)):
            ext_filter[i] = ext_filter[i].lower()
            ext_filter[i] = ext_filter[i] if ext_filter[i].startswith(".") else "." + ext_filter[i]

        # Collect the filepaths
        paths = []
        for root in root_dirs:
            for (dirpath, dirnames, filenames) in root.walk():
                #path = dirpath[1:] if dirpath.startswith(".") else dirpath  # Happens at the root directory with os.walk

                for filename in filenames:
                    if not ext_filter or os.path.splitext(filename)[1].lower() in ext_filter:
                        paths.append(dirpath / filename)

                if not recursive:
                    break

        if disp:
            print("{} files found.".format(len(paths)))

        return cls(paths=paths, root_dirs=root_dirs)

    def __len__(self):
        return len(self._paths)

    def __getitem__(self, i):
        return self._paths[i]

    def __iter__(self):
        return iter(self._paths)


class MutableFileList(FileList):
    """ Class allowing manipulation of file names and paths. If modifications are not needed, use the lighter FileList class instead. """

    def __init__(self, paths, root_dirs, staging):
        """ Internal constructor, use the class method FileSet.build() to instantiate. """
        super().__init__(paths, root_dirs)
        self.staging = staging

    @classmethod
    def build(cls, root_dirs, recursive=True, ext_filter=[], disp=False):
        return cls.from_filelist(FileList.build(root_dirs=root_dirs, recursive=recursive, ext_filter=ext_filter, disp=disp))

    @classmethod
    def from_filelist(cls, filelist : FileList):
        return cls(filelist._paths, filelist._root_dirs, [MutablePath(p) for p in filelist._paths])

    def apply(self, force=False):
        """
        Apply the stages changes. Will prompt the user before overwriting files unless force is set to True.
        :param force: Bool, if True overwrite files without asking
        :return:
        """

        if not force:
            existing = []
            for i, p in enumerate(self._paths):
                if p != self.staging[i].full_path() and self.staging[i].full_path().exists():
                    existing.append(self.staging[i].full_path())

            if existing:
                answer = ""
                while answer != 'y':
                    answer = input("{} target files already exist and will be overwritten, continue (y/n/show)".format(len(existing))).lower()

                    if answer == 'show':
                        [print(i) for i in existing]

                    if answer == 'n':
                        print("Action cancelled, changes were not applied.")
                        return

        changes = 0
        for i, p in enumerate(self._paths):
            if p != self.staging[i].full_path():
                p.rename(self.staging[i].full_path())
                changes += 1

        print("{} files moved/renamed.".format(changes))
    
    def lower(self, stem=True, suffix=True):
        """ Changes file names to lowercase 
        
        :param stem: Bool, if True the stem is converted to lowercase
        :param suffix: Bool, if True the suffix is converted to lowercase
        """
        if suffix or stem:
            for i, p in enumerate(self.staging):
                if stem:
                    self.staging[i].stem = p.stem.lower()
                if suffix:
                    self.staging[i].suffix = p.suffix.lower()

    def reset(self):
        """ Resets the list to its initial state, removing any pending changes """
        self.staging = [MutablePath(p) for p in self._paths]

    def review(self):
        """ Prints the changes to be applied """
        changes = []
        existing = []
        for i, p in enumerate(self._paths):
            change = ""
            if p.parent != self.staging[i].parent:
                change = str(p) + "  ===>>  " + str(self.staging[i])
            elif p.name != self.staging[i].name:
                change = p.name + "  ===>>  " + self.staging[i].name

            if change:
                if self.staging[i].full_path().exists():
                    existing.append(change)
                else:
                    changes.append(change)

        if changes:
            print("\n{} changes staged:".format(len(changes)))
            [print(c) for c in changes]
        if existing:
            print("\nWARNING!!! {} targets already exist and will be overwritten when applying the following staged changes:".format(len(existing)))
            [print(c) for c in existing]
            print("\nWARNING!!! {} targets already exist and will be overwritten when applying the above staged changes".format(len(existing)))

        if not (changes or existing):
            print("No changes staged.")

    def trim(self, n, trim_end=True):
        """
        Trims file names (stems), removing n characters
        :param n: integer number of characters to trim
        :param trim_end: bool, if True removes the characters from the end, else from the begining
        """

        for i, p in enumerate(self.staging):
            self.staging[i].stem = p.stem[:-n] if trim_end else p.stem[n:]

    def truncate(self, n, trim_end=True):
        """
        Truncate file names (stems), keeping the first or last n characters
        :param n: integer number of characters to keep
        :param trim_end: bool, if True removes the extra characters from the end, else from the begining
        """
        for i, p in enumerate(self.staging):
            self.staging[i].stem = p.stem[:n] if trim_end else p.stem[-n:]

    def upper(self, stem=True, suffix=True):
        """ Changes file names to uppercase

        :param stem: Bool, if True the stem is converted to uppercase
        :param suffix: Bool, if True the suffix is converted to uppercase
        """
        if suffix or stem:
            for i, p in enumerate(self.staging):
                if stem:
                    self.staging[i].stem = p.stem.upper()
                if suffix:
                    self.staging[i].suffix = p.suffix.upper()
