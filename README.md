# pathtrees

[![pypi](https://badge.fury.io/py/pathtrees.svg)](https://pypi.python.org/pypi/pathtrees/)
[![tests](https://github.com/beasteers/pathtrees/actions/workflows/ci.yaml/badge.svg)](https://github.com/beasteers/pathtrees/actions/workflows/ci.yaml)
[![docs](https://readthedocs.org/projects/pathtrees/badge/?version=latest)](http://pathtrees.readthedocs.io/?badge=latest)
[![License](https://img.shields.io/pypi/l/pathtrees.svg)](https://github.com/beasteers/pathtrees/blob/main/LICENSE.md)


Define your path structure at the top, then just fill in the variables later.

## Install

```bash
pip install pathtrees
```

## Usage
```python
import pathtrees as pt



# define your file structure.

# a simple ML experiment structure
paths = Paths.define('./logs', {
    '{log_id}': {
        'model.h5': 'model',
        'model_spec.pkl': 'model_spec',
        'plots': {
            'epoch_{step:.4d}': {
                '{plot_name}.png': 'plot',
                '': 'plot_dir',
            }
        },
        # a path join hack that gives you: log_dir > ./logs/{log_id}
        '', 'log_dir',
    }
})
paths.update(log_id='test1', step=-1)



# for example, a keras callback that saves a matplotlib plot every epoch

class MyCallback(Callback):
    def on_epoch_end(self, epoch, logs):
        # creates a copy of the path tree that has step_name=epoch
        epoch_paths = paths.specify(step=epoch)
        ...
        # save one plot
        plt.imsave(epoch_paths.plot.specify(plot_name='confusion_matrix'))
        ...
        # save another plot
        plt.imsave(epoch_paths.plot.specify(plot_name='auc'))

# you can glob over any missing data (e.g. step => '*')
# equivalent to: glob("logs/test1/plots/{step}/auc.png")
for path in paths.plot.specify(plot_name='auc').glob():
    print(path)
```

### Path Formatting

```python
# create a Path object with some placeholders
# pathtrees.Path inherits from pathlib.Path
path = pathtrees.Path('data/{sensor_id}/raw/{date}/temperature_{file_id:04d}.csv')

# now let's specify some of the data - let's only look at sensor "aaa"
path.update(sensor_id='aaa')

# if we try to format the path, it will tell us that 
# we haven't provided enough data
try:
    path.format()
except KeyError: 
    print("oops gotta provide more data!")

# but if we don't mind that we can do a partial format
assert path.partial_format() == 'data/aaa/raw/{date}/temperature_{file_id:04d}.csv'
# or if we want to glob over the other fields, we can do that too!
assert path.glob_format() == 'data/aaa/raw/*/temperature_*.csv'

# you can also pass additional data directly to the format function
# Note: the data passed here does not modify the original Path object's 
#       attached data

# still missing the file_id field
try:
    path.format(date='111')
except KeyError: 
    print("oops gotta provide more data!")

# now date='111' is filled in
assert path.partial_format(date='111') == 'data/aaa/raw/111/temperature_{file_id:04d}.csv'
assert path.glob_format(date='111') == 'data/aaa/raw/111/temperature_*.csv'


# finally, we have a fully specified path - all data provided
assert path.format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'
assert path.partial_format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'
assert path.glob_format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'
```
To update the data, you have two options:
```python
# Path.specify(**data) - creates a copy with the new data
path2 = path.specify(date='111')
# Path.update(**data) - updates the Path object in-place
path2.update(date='222', fild_id=2)

# and now you don't need to pass that info to format()
```

`pathtrees.Path` is compatible with `os.fspath` which converts path-like objects to path strings. `str(path)` is equivalent to partial formatting, because if you want to print something out, typically it will be cast to a string first and we don't want that to require a full format.
```python
import os
assert os.fspath(path) == path.format()
assert str(path) == path.partial_format()
```

TODO:
 - re-write the docs and add examples
