import numpy as np
import pandas as pd

def show_stats(dict):
    for key, val in dict.items():
        print(f'{key}: {val}')

def windowed_count(ts, window, stats):
    e_idx = 0
    counts = np.zeros(shape=ts.shape)
    for i, st in enumerate(ts):
        et = st + window
        while (e_idx < stats['Total QSOs']) and (ts[e_idx] <= et):
            e_idx += 1
            counts[i] += 1
        if i < len(counts) - 1:
            counts[i+1] = counts[i] - 1
    return int(max(counts)), (counts == max(counts)).sum(), counts

def generate_stats(df):
    """ Generate statistics from DXLOG frame """
    stats = {}
    stats['Total QSOs'] = len(df)
    if stats['Total QSOs'] == 0:
        print('Empty data frame')
        return stats, None, None, None
    stats['Contest'] = df.ContestName.iloc[0]
    df = df.sort_index()

    # calculate total operating time
    ts = np.array(df.index.to_list())
    dts = ts[1:] - ts[:-1]
    br_ts = []
    op_times = []
    start_time = ts[0]
    total_op_time = pd.Timedelta(minutes=1)
    for t, dt in zip(ts[1:], dts):
        if dt <= pd.Timedelta(minutes=30):
            prev = t
            continue
        br_ts.append((prev, t))
        op_times.append((start_time, prev))
        total_op_time += (prev - start_time)
        start_time = t
        prev = t
    op_times.append((start_time, ts[-1]))
    total_op_time += ts[-1] - start_time
    stats['Operating Time'] = total_op_time

    # calculate rates
    stats['Average Rate'] = round(float(stats['Total QSOs'])/total_op_time.total_seconds()*3600, 1)
    window = pd.Timedelta(minutes=10) # in minutes
    q_count, repeats, counts_10min = windowed_count(ts=ts, window=window, stats=stats)
    stats['10 min Rate'] = q_count * 6
    stats['10 min Rate repeats'] = repeats

    window = pd.Timedelta(minutes=30) # in minutes
    q_count, repeats, counts_30min = windowed_count(ts=ts, window=window, stats=stats)
    stats['30 min Rate'] = q_count * 2
    stats['30 min Rate repeats'] = repeats

    window = pd.Timedelta(minutes=60) # in minutes
    q_count, repeats, counts_60min = windowed_count(ts=ts, window=window, stats=stats)
    stats['60 min Rate'] = q_count
    stats['60 min Rate repeats'] = repeats

    # calculate running 
    stats['Run QSOs percent'] = round(float(sum(df['IsRunQSO']))/stats['Total QSOs']*100, 1)
    dummy = set(df.Continent.to_list())
    dummy.discard('')
    dummy.discard(' ')
    stats['Continents'] = len(dummy)
    dummy = set(df.CountryPrefix.to_list())
    dummy.discard('')
    dummy.discard(' ')
    stats['Countries'] = len(dummy)
    dummy = set(df.Sect.to_list())
    dummy.discard('')
    dummy.discard(' ')
    stats['Sections'] = len(dummy)
    # radios
    stats['QSOs per Radios'] = {r: int((df['RadioNR'] == r).sum()) for r in set(df.RadioNR.to_list())}
    
    return stats, counts_10min, counts_30min, counts_60min

def log(level, str):
    print(level, str)