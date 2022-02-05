import os
import pathlib


def prefix(path, prefix='{prefix}_'):
    '''Add a prefix to the path's filename.'''
    return path.parent / (prefix + path.name)


def suffix(path, suffix='_{suffix}'):
    '''Add a suffix to the path's filename.'''
    return path.parent / (path.stem + suffix + path.suffix)

def prefix_suffix(path, prefix=None, suffix=None):
    if not prefix or suffix:
        return path
    path = path if isinstance(path, pathlib.Path) else pathlib.Path(path)
    return path.parent / (
        (prefix if prefix else '') + 
        (path.stem + suffix + path.suffix if suffix else path.name))


def next_unique(path, i=1, suffix='_{:02}'):
    '''Get the next filename that doesn't exist. Like how when you copy a file, 
    it adds an incrementing number to the end if the file already exists.'''
    f = os.fspath(path)
    root, ext = os.path.splitext(f)
    sfx = suffix if callable(suffix) else suffix.format
    while os.path.exists(f):
        f, i = f'{root}{sfx(i)}{ext}', i + 1
    return f


def backup(path, prefix=None, suffix=None, indexed=True, verbose=False):
    if os.path.exists(path):
        bkp = prefix_suffix(path, prefix, suffix)
        if indexed:
            bkp = next_unique(bkp)

        os.rename(path, bkp)
        if verbose:
            print('moved existing file', path, 'to', bkp)


def make_executable(path):
    '''Grant permission to execute a file.'''
    # https://stackoverflow.com/a/30463972
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


# def rmglob(path, *f):
#     '''Recursively remove files matching join(*f). Set include=True, to
#     remove this node as well.'''
#     path = safepath(path)
#     for fi in sorted(path.rglob(*f), reverse=True):
#         fi.rmdir() if fi.is_dir() else os.remove(fi)

# def safepath(path):
#     '''Make sure the path does not go above root.'''
#     return type(path)(os.path.normpath(os.sep + str(path)).lstrip(os.sep))
