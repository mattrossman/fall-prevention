import os
import re
import pickle
import numpy as np
import pandas as pd
import smartfloor as sf
directory = 'data/08-07-2019'

""" OVERVIEW

The main items of interest are the batch of all gait cycles and the results table.

If they have not yet been pickled you should do so with:

    batch = pickle_batch()
    df = pickle_df_results(batch)

You can access them later with:

    batch = unpickle_batch()
    df = unpickle_df_results()

You can then look at some simple analytics of the results with:

    res_style_accuracy(df)
    res_participant_accuracy(df)
    res_overall_accuracy(df)
"""


def pickle_batch(path='cycle_batch.p') -> sf.GaitCycleBatch:
    """ Make a batch of all data and save to binary """
    paths = [f'{directory}/{filename}' for filename in os.listdir(directory)]
    floor_batch = sf.FloorRecordingBatch.from_csv(paths, trimmed=True)
    cycle_batch = floor_batch.gait_cycle_batch
    with open(path, 'wb') as f:
        pickle.dump(cycle_batch, f)
        print(f'Cycles successfully pickled to {path}')
    return cycle_batch


def unpickle_batch(path='cycle_batch.p') -> sf.GaitCycleBatch:
    """ Load the saved data batch """
    with open(path, 'rb') as f:
        return pickle.load(f)


@np.vectorize
def cycle_style(cycle) -> str:
    """Extract the gait style string (e.g 'normal', 'lhob') from a data file path"""
    return re.match(r'^\d_([^_]*)_.*', cycle.name).groups()[0]


def cycles_with_style(cycles: sf.GaitCycleBatch, style: str) -> sf.GaitCycleBatch:
    """Filter a batch of cycles by a gait style string (e.g 'normal', 'lhob')"""
    return sf.GaitCycleBatch([cycle for cycle in cycles if cycle_style(cycle) == style])


def result_entries_generator(batch):
    """
    Generate dictionaries representing the results of one style of cycles of one participant against all styles of
    cycles of all other participant

    Parameters
    ----------
    batch : sf.GaitCycleBatch
        All cycles for the experiment

    Yields
    ----------
    entry : dict
    """
    for pid in range(7):
        train, test = batch.partition_names(rf'{pid + 1}_.*', reverse=True)
        for style in ['normal', 'slow', 'hunch', 'stppg', 'lhob', 'rhob']:
            test_cycles = cycles_with_style(test, style)
            dist, neighbors = train.query_batch(test_cycles)
            best_match_style = cycle_style(neighbors[:, 0])  # Style of the top match for each cycle
            num_correct = np.count_nonzero(best_match_style == style)
            print(f'Participant {pid + 1} {style}: {num_correct} / {len(test_cycles)} = {num_correct / len(test_cycles) * 100:.0f}%')
            yield {'pid': pid + 1, 'style': style, 'correct': num_correct, 'total': len(test_cycles)}


def pickle_df_results(batch=None, df=None, path='df_results.p') -> pd.DataFrame:
    """ Build a DataFrame of results if one is not provided and serialize it to a file"""
    if batch is None and df is None:
        raise ValueError('You must provide either a GaitCycleBatch to generate from, or a DataFrame to serialize')
    df = pd.DataFrame(result_entries_generator(batch),
                      columns=['pid', 'style', 'correct', 'total']) if df is None else df
    with open(path, 'wb') as f:
        pickle.dump(df, f)
        print(f'Results successfully pickled to {path}')
    return df


def unpickle_df_results(path='df_results.p') -> pd.DataFrame:
    """ Retrieve a serialized results DataFrame"""
    with open(path, 'rb') as f:
        return pickle.load(f)


def res_style_accuracy(df) -> pd.Series:
    """ Overall accuracy measures for each gait style"""
    grouped = df.groupby('style')
    return grouped.correct.sum() / grouped.total.sum()


def res_participant_accuracy(df) -> pd.Series:
    """ Overall accuracy measures for each participant"""
    grouped = df.groupby('pid')
    return grouped.correct.sum() / grouped.total.sum()


def res_overall_accuracy(df) -> float:
    """ Overall accuracy for the entire experiment"""
    return df.correct.sum() / df.total.sum()
