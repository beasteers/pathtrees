import os
import pathtrees as pt
import pathlib
import pytest

ROOT = os.path.join(os.path.dirname(__file__), 'data')

@pytest.fixture
def base_paths():
    return pt.tree('logs', {
        '': 'root',
        '{log_id}': {
            'model.h5': 'model',
            'model_spec.pkl': 'model_spec',
            'plots': {
                '{step_name}': {
                    '{plot_name}.png': 'plot',
                    '{plot_name}.jpg': 'plot_jpg',
                }
            },
            'results': {'{step_name}.csv': 'result_step'},
            'models': {'{step_name}.h5': 'model_step'},
        },
        'meta.json': 'meta',
    })

@pytest.fixture
def paths(base_paths):
    yield base_paths.specify(log_id='a')

@pytest.fixture
def paths_rw(base_paths):
    paths_rw = base_paths.specify(root=ROOT, log_id='a')
    yield paths_rw

    # Cleanup: paths.root.rmglob

    for p in paths_rw:
        for f in p.glob():
            if os.path.isfile(f):
                print('deleting', f)
                os.remove(f)
            else:
                print("can't delete directory (TODO)", f)

    # assert list(paths_rw.root.rglob())
    # paths_rw.root.rmglob(include=True)
    # assert not list(paths_rw.root.rglob())



def test_init():
    paths = pt.tree('logs', {'': 'root', '{log_id}': {'model.h5': 'model'}})
    # assert paths.data['root'] == 'logs'
    assert set(paths.paths) == {'model', 'root'}

    paths = pt.tree({'plots', 'model.h5'})
    # assert paths.data['root'] == '.'
    assert set(paths.paths) == {'plots', 'model.h5'}
    assert set(paths.partial_format().values()) == {'plots', 'model.h5'}

    paths = pt.tree('logsss', ['plots', 'model.h5'])
    # assert paths.data['root'] == 'logsss'
    assert set(paths.paths) == {'plots', 'model.h5'}
    assert set(paths.partial_format().values()) == {'logsss/plots', 'logsss/model.h5'}

    # legacy
    paths = pt.Paths.define('logs', {'{log_id}': {'model.h5': 'model'}})
    # assert paths.data['root'] == 'logs'
    assert set(paths.paths) == {'model'}


def test_specify(base_paths):
    print(base_paths)
    # TODO: test Paths.add, Paths.get

    # Test: paths.get, getattr(paths, k)

    with pytest.raises(AttributeError):
        base_paths.log_id

    # Test: specify, unspecify

    paths = base_paths.specify(log_id='a')
    paths2 = paths.unspecify('log_id')
    print(paths.model)
    print(paths.model.raw)
    assert paths.model.raw == 'logs/{log_id}/model.h5'

    assert paths is not base_paths and paths2 is not paths
    assert 'log_id' in paths.data
    assert 'log_id' not in paths2.data
    assert not base_paths.fully_specified
    m = paths.specify(log_id=1, step_name=2, plot_name=3).model
    # print(m, type(m), repr(m))
    # print(paths.specify(log_id=1, step_name=2, plot_name=3).format())
    assert paths.specify(log_id=1, step_name=2, plot_name=3).fully_specified



def test_format(base_paths):
    # Test: format, partial_format, glob_pattern, glob

    paths = base_paths.specify(log_id='a')

    # convert to dict of strings
    pm = paths.model
    assert pm.fully_specified
    p = paths.maybe_format()

    # check Paths.format types
    assert not isinstance(p['model'], pt.Path)
    assert isinstance(p['plot'], pt.Path)
    assert all(isinstance(p_, (str, pt.Path)) for p_ in p.values())
    assert all(isinstance(p_, (str, pt.Path)) for p_ in paths.partial_format().values())

    # # check Paths.globs types
    # assert isinstance(paths.globs(), list)

    # test fully specified strings have been formatted
    assert str(pm) == str(p['model'])
    assert str(p['model']) == 'logs/a/model.h5'
    assert str(p['model_spec']) == 'logs/a/model_spec.pkl'

    pm_2 = pm.unspecify('log_id')
    assert not pm_2.fully_specified

    # test underspecified paths have not
    assert isinstance(p['plot'], pt.Path)
    assert str(p['plot'].partial_format()) == 'logs/a/plots/{step_name}/{plot_name}.png'
    assert str(p['plot'].glob_format()) == 'logs/a/plots/*/*.png'
    assert isinstance(p['plot'].glob(), list)
    assert tuple(sorted(list(p['plot'].iglob()))) == tuple(p['plot'].glob())

    # test that format kw are different
    p2 = paths.maybe_format(log_id='b')
    assert str(p['model']) == 'logs/a/model.h5'
    assert str(p2['model_spec']) == 'logs/b/model_spec.pkl'

    # test in a loop
    plot_f = p['plot'].specify(step_name='epoch_100')
    print(repr(plot_f))
    for n in 'abcde':
        f = plot_f.format(plot_name=n)
        print(n, f)
        assert str(f) == 'logs/a/plots/epoch_100/{}.png'.format(n)


def test_add(paths):
    # Test: Paths.add

    # when you don't have a pre-named node
    paths_add = paths.add(paths.model_step.parent.raw, {
        '': 'model_step_dir',
        '{step_name}-2.h5': 'model_step2',
    })
    print(paths_add)
    assert paths_add.model_step2.raw == 'logs/{log_id}/models/{step_name}-2.h5'

    # when you do have a pre-named node
    paths_add = paths.add(paths.model_step_dir.raw, {
        '{step_name}-3.h5': 'model_step3',
    })
    print(paths_add)
    assert paths_add.model_step3.raw == 'logs/{log_id}/models/{step_name}-3.h5'

    # when you want to add an existing path with a new root
    paths_node = pt.tree({
        '{step_name}-4.h5': 'model_step4',
    })
    paths_add = paths.add(paths.model_step_dir.raw, paths_node)
    print(paths_add)
    assert paths_add.model_step4.raw == 'logs/{log_id}/models/{step_name}-4.h5'


def test_parse(base_paths):
    paths = base_paths

    expected = {
        'log_id': '12345',
        'step_name': '0002',
        'plot_name': 'f1_score',
    }

    # Test: parse, translate

    png_file = 'logs/12345/plots/0002/f1_score.png'
    jpg_file = 'logs/12345/plots/0002/f1_score.jpg'
    assert set(paths.plot.parse(png_file).items()) == set(expected.items())
    assert set(paths.parse(png_file, 'plot').items()) == set(expected.items())
    # assert paths.translate(png_file, 'plot', 'plot_jpg').format() == jpg_file
    assert str(paths.plot.translate(png_file, 'plot_jpg').format()) == jpg_file
    assert str(paths.translate(png_file, 'plot', 'plot_jpg', use_data=False).format()) == jpg_file

    with pytest.raises(ValueError):
        paths.plot.parse('broken/some/logs/12345/plots/0002/f1_score.png')
    # TODO: More intensive parse tests


def test_path_data_preservation():
    data = {'a': 5}
    p = pt.Path("~/{a}/{b}/xx/{c}", data=dict(data))
    assert (p/'d').data == data
    assert (p.joinpath('d')).data == data
    assert p.expanduser().data == data