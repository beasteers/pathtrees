# pathtrees

[![pypi](https://badge.fury.io/py/pathtrees.svg)](https://pypi.python.org/pypi/pathtrees/)
<!-- ![tests](https://github.com/beasteers/pathtrees/actions/workflows/ci.yaml/badge.svg) -->
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
path = pathtrees.Path('data/{sensor_id}/raw/{date}/temperature_{file_id:04d}.csv')
path.update(sensor_id='aaa')

try:
    path.format()
except KeyError: 
    print("oops gotta provide more data!")

assert path.partial_format() == 'data/aaa/raw/{date}/temperature_{file_id:04d}.csv'
assert path.glob_format() == 'data/aaa/raw/*/temperature_*.csv'

try:
    path.format(date='111')
except KeyError: 
    print("oops gotta provide more data!")

assert path.partial_format(date='111') == 'data/aaa/raw/111/temperature_{file_id:04d}.csv'
assert path.glob_format(date='111') == 'data/aaa/raw/111/temperature_*.csv'

# fully specified path - all data provided
assert path.format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'
assert path.partial_format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'
assert path.glob_format(date='111', fild_id=2) == 'data/aaa/raw/111/temperature_0002.csv'

# passing arguments to format() doesn't update the original object.

# you can either create a copy of the path and update it's data
path2 = path.specify(date='111')
# or you can update the data in place using update()
path2.update(date='222', fild_id=2)

# and now you don't need to pass that info to format()

import os

assert os.fspath(path) == path.format()
assert str(path) == path.partial_format()
```

TODO:
 - docstrings and examples !!!
 - decide what I want to do about `format_path`, `partial_format_path`, etc. (too verbose)
 - publish RTD