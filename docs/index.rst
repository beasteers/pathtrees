.. pathtrees documentation master file, created by
   sphinx-quickstart on Tue Feb  1 16:31:36 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pathtrees
=====================================

Have you ever managed a project with a complex file structure where your paths encode a lot of information? 
Aren't you tired of sprinkling your code with tons of splits and joins and index counting? I am. It 
gets so confusing and hard to reason about sometimes. Instead, I want to define my file structure in one 
place and just fill it with variables.

Here's what we can do with a single path object.

.. code-block:: python

    import pathtrees

    path = pathtrees.Path('data/{sensor_id}/raw/{date}/temperature_{file_id:04d}.csv')
    path.update(sensor_id='asdf-123')  # assign the sensor ID to the path

    # format the path using some data
    path_13 = path.format(date='02022022', file_id=13)
    assert path_13 == 'data/asdf-123/raw/02022022/temperature_0013.csv'
    # now use the formatted string, along with the path format, to parse the data from the path
    assert path.parse(path_13) == {'sensor_id': 'asdf-123', 'date': '02022022', 'file_id': 13}

And it's pretty handy with glob too - you can glob over any variables that haven't been specified.

.. code-block:: python

    # list all files for asdf-123 on 02/02/2022
    for f in path.specify(date='02022022').glob():  # specify() ~~ copy.update()
        # parse the file ID out of the path
        print(path.parse(f)['file_id'])

    # list all dates
    date_path = path.parent.specify(sensor_id='asdf-123')
    for date_dir in date_path.glob():
        # parse the date out of each path
        print("Date": date_path.parse(date_dir)['date'])

Now let's see a whole directory tree. 

Here is an example where we're processing an audio dataset 
and want to save some outputs to disk.

By using ``pathtrees`` we can define the path structure at the top of a file and then 
the rest of your code can operate independent of that structure. Want to add a prefix or suffix
to your filename? Want to move a couple directories around? Feeling evil and want to nest the SPL
files under 15 extra directories? ``pathtrees`` D. G. A. F.. And neither will your code!
As long as the core pieces of information are still there (here: ``{sensor_id}`` and ``{file_id}``)
the rest of your code doesn't have to know about it!

First define the path structure.

.. code-block:: python

    import pathtrees
    import librosa

    paths = pathtrees.tree('{project}', {
        'data': {
            '{sensor_id}': {
                '': 'sensor',
                'audio': { '{file_id:04d}.flac': 'audio' },
                'spl': { 'spl_{file_id:04d}.csv': 'spl' },
                'embeddings': { 'emb_{file_id:04d}.csv': 'embeddings' },
            },
        },
    })
    # set some data to start with
    paths.update(project='some-project')


Let's try formatting some path objects.

.. code-block:: python

    # partial format

    # treating the path as a string will partially format it
    # meaning that only the keys that are defned will be replaced.
    assert paths.audio == 'some-project/data/{sensor_id}/audio/{file_id:04d}.flac'
    assert (
        paths.audio.partial_format(sensor_id='aaa') == 
        'some-project/data/aaa/audio/{file_id:04d}.flac')

    # format

    try:
        paths.audio.format(sensor_id='aaa')  # forgot file ID
    except KeyError:
        print("oops")

    # when you have all data specified, you can format it and get a complete path
    # and then you can take a formatted path and reverse it to get the data back out.
    p = paths.audio.format(sensor_id='aaa', file_id=0)
    assert p == 'some-project/data/aaa/audio/0000.flac'
    assert (
        paths.audio.parse(p) == 
        {'project': 'some-project', 'sensor_id': 'aaa', 'file_id': 0})
    
But don't worry, if the path is missing data and you try to use it as a path, it will throw an error.

.. code-block:: python

    try:
        with open(paths.spl, 'r') as f:  # some-project/data/{sensor_id}/audio/{file_id:04d}.flac
            ...
    except KeyError:
        print("I didn't provide all of the data, so this was bound to happen.")

    spl_path = paths.spl.specify(sensor_id='bbb', file_id=15)
    with open(spl_path, 'r') as f:  # some-project/data/bbb/audio/0015.flac
        print("Ah much better..")
        print(f.read())

Now let's use the paths to deal with some data.

.. code-block:: python

    # loop over sensors - {sensor_id} automatically turned to '*'
    for sensor_dir in path.sensor.glob():  # some-project/data/*
        sensor_id = path.sensor.parse(sensor_dir)['sensor_id']

        # loop over a sensors flac files - {file_id} automatically turned to '*'
        for audio_fname in path.audio.glob():  # some-project/data/{sensor_id}/audio/*.flac
            y, sr = librosa.load(audio_fname)

            # convert audio path to an spl path - some-project/data/{sensor_id}/spl/{file_id}.csv
            spl_fname = path.translate(audio_fname, 'audio', 'spl')
            # convert audio path to an embedding path - some-project/data/{sensor_id}/embedding/{file_id}.csv
            embedding_fname = path.translate(audio_fname, 'audio', 'embedding')

            # just make sure that everything is in order
            file_id = path.audio.parse(audio_fname)['file_id']
            assert sensor_id in spl_fname and file_id in spl_fname
            assert sensor_id in embedding_fname and file_id in embedding_fname

            # calculate some stuff and write to file
            write_csv(spl_fname, get_spl(y, sr))
            write_csv(embedding_fname, get_embedding(y, sr))

See how working with the paths is all independent of the actual folder structure? No path joins or 
weird splits and split counting to parse out the bits and pieces of a path.

As long as you preserve the basic data relationships, (here it's a many-to-one between data and sensors), 
then you can change the file structure at the top and not have to worry about it elsewhere.



Installation
---------------

.. code-block:: bash

   pip install pathtrees


.. toctree::
   :maxdepth: 2
   :titlesonly:
   :hidden:

   self


.. toctree::
   :maxdepth: 1
   :caption: Getting Started:

   api

.. note::

   This is a code redesign from ``path-tree``. I re-wrote it because that 
   was one of my very first public Pypi projects and I'm not exactly proud 
   of some of the design decisions I made. 

   On top of that! I found out that it breaks with Python 3.10. Which was the real reason.
   Crossing my fingers that I can get everything pushed out before I get a GitHub issue
   saying everything is broken!

   This is an effort to turn an old, fragile, and about-to-break project into something that 
   I might actually import into a new project!

   The rename from ``path-tree`` to ``pathtrees`` is because I've always hated that the pip 
   install name is not the same as the import name. That is a big pet peeve so I'll be glad 
   to be rid of that in at least my own projects.

   I threw this together (including docs) in a couple nights after work so it's still a WIP.
   
   The code is mostly together, but the docs and examples need work. And there's a couple 
   small quirks around things like: Should ``path.format()`` return a ``pathlib.Path`` or a ``str``?