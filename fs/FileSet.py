"""
Class for quick, reusable, in-memory name-based file search and folder comparison.

Allows performing set operations (union, difference, intersection) on file paths, which can be done
using the |, - and & operators. Intersect and difference can also be done using filenames only using the
intersect_names() and subtract_names() functions.

Supports both full and relative paths. Relative paths are converted to full paths automatically for operations
where it is necessary.


Usage example:

fs1 = FileSet.build(r"C:\some\nested\folder\my_folder_1", relative=True)
fs2 = FileSet.build(r"C:\other_folder\my_folder_2", relative=True)

difference = fs1 - fs2      # Gives the files from fs1 not in fs2 considering the relative folder structure
union = fs1 | fs2           # Results in a union of the two file sets.
                            #The resulting FileSet will be full path since it now has more than one root directory
intersect = fs1 & fs2       # Results in a FileSet with the files from fs1 also present in fs2

fs3 = FileSet.build(r"C:\other_folder\my_folder_3", relative=False)  # This FileSet stores and compares full paths

test_location = fs3.find("test.jpg")  # Prints all locations where test.jpg can be found in fs3
test_location = fs3.find(fs2)  # Finds all places in fs3 where each filename in fs2 can be found

difference = fs3 - fs2  # Removes the fs3 files that match fs2 files and their relative filepaths
diff_names = fs3.subtract_names(fs2)  # Removes all fs3 files match fs2 filenames, irrespective of the folder structure

"""

import os


class FileSet:
    def __init__(self, paths, names, rootdirs, rel_paths, lower):
        """ Internal constructor, use the class method FileSet.build() to instantiate. """
        self.paths = paths
        self.names = names
        self.rootdirs = rootdirs
        self.rel_paths = rel_paths
        self.lower = lower

    @classmethod
    def build(cls, root_dirs, rel_paths=False, lower=False):
        """ Builds a FileSet object from the provided parameters.

        :param root_dirs: List, Set or Str. Path(s) to directories from which to build the file set.
        :param rel_paths: If True, only relative paths to a single root directory will be stored.
        :param lower: If True, files and paths will be stored in lower case.
        :return: FileSet representing the content of the root directories.
        """
        if isinstance(root_dirs, list):
            root_dirs = set(root_dirs)
        if isinstance(root_dirs, str):
            root_dirs = set([root_dirs])
        elif rel_paths and len(root_dirs) > 1:
            raise ValueError("Only a single root directory is allowed when using relative paths.")

        paths = set()
        names = set()

        for root in root_dirs:
            for (dirpath, dirnames, filenames) in os.walk(root):
                path = os.path.relpath(dirpath, root) if rel_paths else dirpath
                path = path[1:] if path.startswith(".") else path  # Happens at the root directory

                if lower:
                    path = path.lower()
                    for filename in filenames:
                        names.add(filename.lower())
                        paths.add(os.path.join(path, filename).lower())
                else:
                    for filename in filenames:
                        names.add(filename)
                        paths.add(os.path.join(path, filename))

        return cls(paths, names, root_dirs, rel_paths, lower)

    def __len__(self):
        return len(self.paths)

    def __add__(self, other):
        return self | other

    def __sub__(self, other):
        if self.rel_paths and not other.rel_paths:
            raise ValueError("Left operand cannot have relative paths if right operand does not.")
        elif not self.rel_paths and other.rel_paths:
            paths = []
            for i in self.paths:
                included = True
                for j in other.paths:
                    if j in i:
                        included = False
                        break
                if included:
                    paths += [i]
            paths = set(paths)
        else:
            paths = self.paths - other.paths

        names = set([os.path.basename(i) for i in paths])
        return FileSet(paths, names, self.rootdirs, self.rel_paths, self.lower)

    def __and__(self, other):
        if self.rel_paths ^ other.rel_paths:
            first_set = other.paths if self.rel_paths else self.paths
            second_set = self.paths if self.rel_paths else other.paths

            paths = []
            for i in first_set:
                included = False
                for j in second_set:
                    if j in i:
                        included = True
                        break
                if included:
                    paths += [i]
            paths = set(paths)
        else:
            paths = self.paths & other.paths

        names = set([os.path.basename(i) for i in paths])
        return FileSet(paths, names, self.rootdirs, self.rel_paths, self.lower)

    def __or__(self, other):
        if self.rel_paths or other.rel_paths:
            paths = self.get_full_paths() | other.get_full_paths()
        else:
            paths = self.paths | other.paths

        names = self.names | other.names
        return FileSet(paths, names, self.rootdirs | other.rootdirs, self.rel_paths, self.lower)

    def find(self, names, disp=True, lower=True):
        """ Finds the paths where one or more files are located

        :param names: Set, List or Str. Names of the files to find.
        :param disp: If True, results will be printed.
        :param lower: If True, names and paths will be converted to lowercase before comparison.
        :return: Set containing the paths where the files are can be found
        """
        if isinstance(names, FileSet):
            names = names.names
        elif isinstance(names, list):
            names = set(names)
        elif isinstance(names, str):
            names = set([names])

        final_res = set()
        if disp:
            names = sorted(names)
        for n in names:
            res = []
            if lower:
                res += [i for i in self.paths if i.lower().endswith(n.lower())]
            else:
                res += [i for i in self.paths if i.endswith(n)]
            if res:
                final_res.update(res)
            if disp:
                print("\n{}:".format(n))
                if res:
                    [print(i) for i in res]
                else:
                    print("No results")

        return final_res

    def get_full_paths(self):
        """ Returns the full paths no matter if the class was built with full or relative paths """
        if self.rel_paths:
            root = next(iter(self.rootdirs))
            return set([os.path.join(root, i) for i in self.paths])
        else:
            return self.paths

    def intersect_names(self, names):
        """ Returns a FileSet with only the files matching the provided names, irrespective of the folder structure.

        :param names: Set, List or Str. Names of the files to include.
        :return: FileSet
        """
        if isinstance(names, FileSet):
            names = names.names
        elif isinstance(names, list):
            names = set(names)

        names = self.names & names
        paths = [i for i in self.paths if os.path.basename(i) in names]
        return FileSet(paths, names, self.rootdirs, self.rel_paths, self.lower)

    def subtract_names(self, names):
        """ Returns a FileSet without files matching any of the provided names, irrespective of the folder structure.

        :param names: Set, List or Str. Names of the files to exclude.
        :return: FileSet
        """
        if isinstance(names, FileSet):
            names = names.names
        elif isinstance(names, list):
            names = set(names)

        names = self.names - names
        paths = [i for i in self.paths if os.path.basename(i) in names]
        return FileSet(paths, names, self.rootdirs, self.rel_paths, self.lower)
