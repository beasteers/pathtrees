from __future__ import annotations
import os
import glob
import pathlib
from typing import Dict, Iterable, List, Union, TypeVar
# import itertools
from functools import wraps
# import inspect
from parse import parse as parse_
from pformat import *
from .util import *

Ps = TypeVar('Ps', bound='Paths')
P = TypeVar('P', bound='Path')

_TREE_DEF_TYPE = Dict[str, Union[str, Dict]]

def tree(root: Union[str, _TREE_DEF_TYPE]=None, paths: Union[str, _TREE_DEF_TYPE]=None, data: Dict=None):
    '''Build paths from a directory spec.

    Arguments:
        root (str): the root directory.
        paths (dict): the directory structure.

    Returns:
        The initialized Paths object

    .. code-block:: python

        import pathtrees

        # define the file structure

        path = pathtrees.tree('{project}', {
            'data': {
                '{sensor_id}': {
                    '': 'sensor',
                    'audio': { '{file_id:04d}.flac': 'audio' },
                    'spl': { 'spl_{file_id:04d}.csv': 'spl' },
                    'embeddings': { 'emb_{file_id:04d}.csv': 'embeddings' },
                },
            },
        })

    .. note::

        use empty strings to reference the directory. This works because
        ``os.path.join(path, '') == path``
    '''
    if root is not None and not isinstance(root, (str, os.PathLike)):
        root, paths = paths, root
    paths = paths or {}
    if isinstance(paths, Paths):
        return paths.rjoinpath(root) if root else paths
    root = root or '.'
    if isinstance(paths, (list, tuple, set)):
        paths = {k: k for k in paths}
    # if isinstance():
    #     pass
    return Paths(
        {v: Path(*k) for k, v in _get_keys({str(root or ''): paths})},
        data or {})


def _get_keys(data: _TREE_DEF_TYPE, keys: tuple=None, iters_as_keys: bool=False):
    '''Recursively traverse a nested dict and return the trail of keys, and the final value'''
    keys = tuple(keys or ())
    for key, value in data.items():
        ks = keys + (key,)
        if isinstance(value, dict):
            for ksi, val in _get_keys(value, ks, iters_as_keys):
                yield ksi, val
        elif iters_as_keys and isinstance(value, (tuple, list, set)):
            for val in value:
                yield ks, val
        else:
            yield ks, value


class Underspecified(KeyError):
    '''Raised when you try to format a Path without enough data.
    
    It's basically a KeyError with more information.
    '''




class Paths:
    '''A hierarchy of paths in your project.

    You can arbitrarily nest them and it will join all of the keys 
    leading down to that path. The value is the name that you 
    can refer to it by.

    .. code-block:: python

        # define your file structure.

        # a common ML experiment structure (for me anyways)
        paths = Paths.define('./logs', {
            '{log_id}': {
                'model.h5': 'model',
                'model_spec.pkl': 'model_spec',
                'plots': {
                    'epoch_{step_name}': {
                        '{plot_name}.png': 'plot',
                        '': 'plot_dir'
                    }
                },
                # a path join hack that gives you: log_dir > ./logs/{log_id}
                '', 'log_dir',
            }
        })
        paths.update(log_id='test1', step_name='epoch_100')

        # get paths by name
        paths.model  # logs/test1/model.h5
        paths.model_spec  # logs/test1/model_spec.pkl
        paths.plot  # logs/test1/plots/{step_name}/{plot_name}.png

        # for example, a keras callback that saves a matplotlib plot every epoch
        class MyCallback(Callback):
            def on_epoch_end(self, epoch, logs):
                # creates a copy of the path tree that has step_name=epoch
                epoch_paths = paths.specify(step_name=epoch)

                ...
                # save one plot
                plt.imsave(epoch_paths.plot.specify(plot_name='confusion_matrix'))
                ...
                # save another plot
                plt.imsave(epoch_paths.plot.specify(plot_name='auc'))

        # you can glob over any missing data (e.g. step_name => '*')
        # equivalent to: glob("logs/test1/plots/{step_name}/auc.png")
        for path in paths.plot.specify(plot_name='auc').glob():
            print(path)

    '''
    def __init__(self, paths: Dict[str, 'Path'], data: dict=None):
        self.paths = paths
        for path in paths.values():
            path._tree = self
        self.data = {} if data is None else data

    def __repr__(self) -> str:
        return '<Paths data={} \n{}\n>'.format(self.data, '\n'.join([
            '\t{} : {}'.format(name, p.partial_format())
            for name, p in self.paths.items()
        ]))

    @classmethod
    def define(cls, paths: _TREE_DEF_TYPE=None, root: P=None, data: dict=None) -> 'Paths':
        return tree(paths, root, data)
    define.__doc__ = tree.__doc__

    def __contains__(self, name: str) -> bool:
        '''Check if a label is in the tree.'''
        return name in self.paths

    def __iter__(self) -> Iterable['Path']:
        '''Iterate over paths in the tree.'''
        return iter(self.paths.values())

    # def __call__(self, **kw):
    #     return self.specify(**kw)

    def keys(self) -> Iterable[str]:
        '''Iterate over path names in the tree.'''
        return self.paths.keys()

    def __getattr__(self, name) -> 'Path':
        '''Get a path by name.'''
        if name in self.paths:
            return self.paths[name]
        raise AttributeError(name)

    def __getitem__(self, name) -> 'Path':
        '''Get a path by name.'''
        if isinstance(name, tuple):
            return Paths({n: self._paths[n] for n in name}, data=dict(self.data))
        return self.paths[name]

    def add(self: Ps, root=None, paths=None) -> Ps:
        '''Build paths from a directory spec.

        Arguments:
            root (str): the root directory.
            paths (dict): the directory structure.

        Returns:
            The initialized Paths object
        '''
        paths = tree(root, paths)
        children = {k: p.copy for k, p in paths.paths.items()}
        self.paths.update(**children)
        for path in children.values():
            path._tree = self
        return self

    def rjoinpath(self: Ps, path) -> Ps:
        """Give these paths a new root! Basically doing root / path for all paths in this tree.
        This is useful if you want to nest a folder inside another.py
        """
        return Paths({name: p.rjoinpath(path) for name, p in self.paths.items()}, dict(self.data))

    def relative_to(self: Ps, path) -> Ps:
        """Make these paths relative to another path! Basically doing path.relative_to(root) for all paths in this tree.
        Use this with ``with_root`` to change the root directory of the paths.
        """
        return Paths({name: p.relative_to(path) for name, p in self.paths.items()}, dict(self.data))

    def parse(self, path, name) -> dict:
        '''Parse data from a formatted string (reverse of string format)

        Arguments:
            path (str): the string to parse
            name (str): the name of the path pattern to use.
        '''
        return self[name].parse(path)

    def translate(self, file, name, to, **kw) -> 'Path':
        ''''''
        return self.paths[to].specify(**self.paths[name].parse(file, **kw))

    @property
    def copy(self: Ps) -> Ps:
        """Create a copy of a path tree and its paths."""
        return Paths({name: path.copy for name, path in self.paths.items()}, dict(self.data))

    def update(self: Ps, **kw) -> Ps:
        '''Update specified data in place.
        
        .. code-block:: python

            paths = pathtrees.tree({'{a}': aaa})
            assert not paths.fully_specified
            paths.update(a=5)
            assert paths.fully_specified
            assert paths.data['a'] == 5
        '''
        self.data.update(kw)
        return self

    def specify(self: Ps, **kw) -> Ps:
        '''Creates a copy of the path tree then updates the copy's data.
        
        .. code-block:: python

            paths = pathtrees.tree({'{a}': aaa})
            paths2 = paths.specify(a=5)

            assert not paths.fully_specified
            assert paths2.fully_specified

            assert 'a' not in paths.data
            assert paths2.data['a'] == 5

        Equivalent to:

        .. code-block:: python

            paths.copy.update(**kw)
        '''
        return self.copy.update(**kw)

    def unspecify(self: Ps, *keys, inplace=False, children=True) -> Ps:
        '''Remove keys from paths dictionary.
        
        .. code-block:: python

            paths = pathtrees.tree({'{a}': aaa})
            paths.update(a=5)
            assert paths.fully_specified
            assert paths.data['a'] == 5

            paths.unspecify('a')
            assert not paths.fully_specified
            assert 'a' not in paths.data

        '''
        p = self if inplace else self.copy
        for key in keys:
            p.data.pop(key, None)
        if children:
            for p in self:
                p.unspecify(*keys, parent=False)
        return p

    @property
    def fully_specified(self) -> bool:
        '''Are all paths fully specified?
        
        .. code-block:: python

            paths = pathtrees.tree({'{a}': aaa})
            assert not paths.fully_specified
            paths.update(a=5)
            assert paths.fully_specified
        '''
        return all(p.fully_specified for p in self.paths.values())

    def format(self, **kw) -> Dict[str, str]:
        '''Try to format all paths as strings. Raises Underspecified if data is missing.

        Arguments:
            **kw: additional data specified for formatting.

        Returns:
            dict: key is the name of the path, and the value is the formatted ``pathlib.Path``.
        '''
        return {name: self[name]._format(**kw) for name in self.paths}

    def maybe_format(self, **kw) -> Dict[str, Union[str, 'Path']]:
        '''Return a dictionary where all fully specified paths are converted to strings
        and underspecified strings are left as Path objects.

        Arguments:
            **kw: additional data specified for formatting.
        '''
        return {name: self[name].maybe_format(**kw) for name in self.paths}

    def partial_format(self, **kw) -> Dict[str, str]:
        '''Return a dictionary where all paths are converted to strings
        and underspecified fields are left in for later formatting.

        Arguments:
            **kw: additional data specified for formatting.
        '''
        return {name: self[name]._partial_format(**kw) for name in self.paths}



BuiltinPath = type(pathlib.Path())
class Path(BuiltinPath):
    '''Represents a ``pathlib.Path`` with placeholders for bits of data.
    It uses python string formatting to let you fill in the 
    missing bits at a later date. 

    .. code-block::

        path = pathtrees.Path('projects/{name}/images/frame_{frame_id:04d}.jpg')
        path.update(name='my_project')

        # loop over all frames
        for f in path.glob():
            # print out some info about each frame
            data = path.parse(f)
            print("frame ID:", data['frame_id'])
            print("path:", f)
            ...  # do something - load an image idk

    There are quite a few methods that had to be wrapped from the original path 
    object so that if we manipulate the path in any way that it can copy the extra
    attributes needed to manage the data.

    '''
    __slots__ = ['data', '_tree']  #, '_tree_root'
    def __new__(cls, *args, data: dict=None, tree: Paths=None):  # , root=None
        p = super().__new__(cls, *args)
        p.data = {} if data is None else data
        p._tree = tree
        # p._tree_root = root
        return p

    # str representations

    def _add_extra_parts(self, p: 'Path', copy_data: bool=False) -> 'Path':
        p.data = dict(self.data) if copy_data else self.data
        p._tree = self._tree
        # p._tree_root = self._tree_root
        return p

    def __repr__(self) -> str:
        return 'Path({}, data={}, parent_data={})'.format(super().__str__(), self.data, self._tree.data if self._tree else None)

    def __fspath__(self) -> str:
        return self._format()

    def __str__(self) -> str:
        return self._partial_format()

    def __hash__(self):
        return hash(self._partial_format())

    def __call__(self, **kw) -> BuiltinPath:
        return self.format(**kw)

    def __eq__(self, __o) -> bool:
        if isinstance(__o, str):
            return self._partial_format() == __o
        return super().__eq__(__o)

    @property
    def raw(self) -> str:
        return super().__str__()

    def rjoinpath(self, root: BuiltinPath) -> 'Path':
        '''Return an absolute form of the path.
        TODO: is there a better way?
        '''
        return Path(root / self, data=self.data, tree=self._tree)


    # data management

    @property
    def copy(self: P) -> P:
        '''Creates a copy of the path object so that data can be altered without affecting
        the original object.'''
        return self._add_extra_parts(
            self._from_parsed_parts(self._drv, self._root, self._parts), 
            copy_data=True)

    def update(self: P, **kw) -> P:
        '''Update specified data in place'''
        self.data.update(kw)
        return self

    def specify(self: P, **kw) -> P:
        '''Update specified data and return a new object.'''
        return self.copy.update(**kw)

    def unspecify(self: P, *keys, inplace: bool=True, parent: bool=True) -> P:
        '''Remove keys from path dictionary'''
        p = self if inplace else self.copy
        if parent and p._tree:
            p._tree = p._tree.unspecify(*keys, children=False)
        for key in keys:
            p.data.pop(key, None)
        return p

    @property
    def fully_specified(self) -> bool:
        '''Check if the path is fully specified (if True, it can be 
        formatted without raising an Underspecified error.).'''
        try:
            self._format()
            return True
        except KeyError:
            return False



    # formatting

    def _get_data(self, **kw) -> dict:
        return {**(self._tree.data if self._tree else {}), **self.data, **kw}

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        if self._tree:
            return self._tree.data.get(key, default)
        return default

    def _format(self, **kw) -> str:
        return fformat(super().__str__(), **self._get_data(**kw))
    def _partial_format(self, **kw) -> str:
        return pformat(super().__str__(), **self._get_data(**kw))
    def _glob_format(self, **kw) -> str:
        return gformat(super().__str__(), **self._get_data(**kw))
    def _format_path(self, **kw) -> BuiltinPath:
        return BuiltinPath(self._format(**kw))
    def _partial_format_path(self: P, **kw) -> P:
        return Path(self._partial_format(**kw), data=self.data, tree=self._tree)
    def _glob_format_path(self, **kw) -> BuiltinPath:
        return BuiltinPath(self._glob_format(**kw))

    def format(self, **kw) -> str:
        '''Insert data into the path string. (Works like string format.)

        Raises:
            KeyError if the format string is underspecified.
        '''
        return self._format(**kw)
    def partial_format(self, **kw) -> str:
        '''Format a field, leaving all unspecified fields to be filled later.'''
        return self._partial_format(**kw)
    def glob_format(self, **kw) -> str:
        '''Format a field, setting all unspecified fields as a wildcard (asterisk).'''
        return self._glob_format(**kw)

    def format_path(self, **kw) -> BuiltinPath:
        '''Insert data into the path string. (Works like string format.)

        Raises:
            KeyError if the format string is underspecified.
        '''
        return self._format_path(**kw)
    def partial_format_path(self: P, **kw) -> P:
        '''Format a field, setting all unspecified fields as a wildcard (asterisk).'''
        return self._partial_format_path(**kw)
    def glob_format_path(self, **kw) -> BuiltinPath:
        '''Format a field, setting all unspecified fields as a wildcard (asterisk).'''
        return self._glob_format_path(**kw)

    def maybe_format(self: p, **kw) -> Union[str, P]:
        '''Try to format a field. If it fails, return as a Path object.'''
        p = self.specify(**kw) if kw else self
        try:
            return p.format()
        except KeyError:
            return p



    # glob

    def glob(self, *fs) -> List[str]:
        '''Glob over all unspecified variables.
        
        Arguments:
            *path (str): additional paths to join. e.g. for a directory
                you can use ``"*.txt"`` to get all .txt files.

        Returns:
            list: The paths matching the glob pattern.
        '''
        return glob.glob(os.path.join(self._glob_format(), *fs))

    def iglob(self, *fs) -> Iterable[str]:
        '''Iterable glob over all unspecified variables. See :func:`glob` for signature.'''
        return glob.iglob(os.path.join(self._glob_format(), *fs))

    def rglob(self, *fs) -> List[str]:
        '''Recursive glob over all unspecified variables. See :func:`glob` for signature.'''
        return glob.glob(os.path.join(self._glob_format(), *fs), recursive=True)

    def irglob(self, *fs) -> Iterable[str]:
        '''Iterable, recursive glob over all unspecified variables. See :func:`glob` for signature.'''
        return glob.iglob(os.path.join(self._glob_format(), *fs), recursive=True)


    def parse(self, path: str, use_data: bool=True) -> dict:
        '''Extract variables from a compiled path.

        See ``parse`` to understand the amazing witchery that
        makes this possible! 

        https://pypi.org/project/parse/
        
        Arguments:
            path (str): The path containing data to parse.
            use_data (bool): Should we fill in the data we already 
                have before parsing? This means fewer variables that 
                need to be parsed. Set False if you do not wish to use 
                the data.
        '''
        path = str(path)
        pattern = self._partial_format() if use_data else super().__str__()
        r = parse_(pattern, path)
        if r is None:
            raise ValueError('''Could not parse path using pattern.
    path: {}
    pattern: {}

`path.parse(path)` will call self.partial_format() by default before parsing
so any specified keys will be fixed. This is helpful to dodge ambiguous parsing
cases. To disable this pass `use_data=False` to parse.'''.format(path, pattern))
        return self._get_data(**r.named)

    def translate(self: P, path: str, to: str, **kw) -> P:
        '''Translate the paths to another pattern'''
        return self._tree[to].specify(**self.parse(path, **kw))

    # fixes

    @property
    def parents(self) -> _PathParents:
        return _PathParents(self)


def fformat(x: str, **kw) -> str:
    try:
        return x.format(**kw)
    except KeyError as e:
        raise Underspecified(
            f'Path "{pformat(x, **kw)}" is missing a value for "{str(e)[1:-1]}" in data {set(kw)}.')


# hot fix for copying over data

def _fix_parts(func):
    @wraps(func)
    def inner(self, *a, **kw):
        return self._add_extra_parts(func(self, *a, **kw))
    return inner

_uses_parsed_parts = ['_make_child', '_make_child_relpath', 'with_name', 'with_suffix', 'relative_to']
_uses_parts = ['__rtruediv__', 'absolute', 'resolve', 'readlink', 'expanduser']
for _method in _uses_parsed_parts + _uses_parts:
    try:
        setattr(Path, _method, _fix_parts(getattr(BuiltinPath, _method)))
    except AttributeError:
        pass
Path.parent = property(_fix_parts(BuiltinPath.parent.fget))


class _PathParents(pathlib._PathParents):
    __slots__ = ['data', 'parent']
    def __init__(self, path):
        super().__init__(path)
        self.data = path.data
        self.parent = path.parents

    _add_extra_parts = Path._add_extra_parts

    def __getitem__(self, i):
        x = super().__getitem__(i)
        return x if isinstance(i, slice) else self._add_extra_parts(x)


if __name__ == '__main__':
    def main():
        p = Path("path/{hello}/{hi}.txt")

    import fire
    fire.Fire(main)