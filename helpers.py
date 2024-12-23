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
        while (e_idx < stats['total_qsos']) and (ts[e_idx] <= et):
            e_idx += 1
            counts[i] += 1
        if i < len(counts) - 1:
            counts[i+1] = counts[i] - 1
    return int(max(counts)), (counts == max(counts)).sum(), counts

def generate_stats(df):
    """ Generate statistics from DXLOG frame """
    stats = {}
    stats['total_qsos'] = len(df)
    if stats['total_qsos'] == 0:
        print('Empty data frame')
        return stats, None, None, None
    stats['name'] = df.ContestName.iloc[0]
    #del df['ContestName']
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
    stats['op_time'] = total_op_time

    # calculate rates
    stats['rate_ave'] = round(float(stats['total_qsos'])/total_op_time.total_seconds()*3600, 1)
    window = pd.Timedelta(minutes=10) # in minutes
    q_count, repeats, counts_10min = windowed_count(ts=ts, window=window, stats=stats)
    stats['rate_10min'] = q_count * 6
    stats['rate_10min_cnt'] = repeats

    window = pd.Timedelta(minutes=30) # in minutes
    q_count, repeats, counts_30min = windowed_count(ts=ts, window=window, stats=stats)
    stats['rate_30min'] = q_count * 2
    stats['rate_30min_cnt'] = repeats

    window = pd.Timedelta(minutes=60) # in minutes
    q_count, repeats, counts_60min = windowed_count(ts=ts, window=window, stats=stats)
    stats['rate_60min'] = q_count
    stats['rate_60min_cnt'] = repeats

    # calculate running 
    stats['run_percent'] = round(float(sum(df['IsRunQSO']))/stats['total_qsos']*100, 1)
    stats['continents'] = set(df.Continent.to_list())
    stats['countries'] = set(df.CountryPrefix.to_list())
    stats['sections'] = set(df.Sect.to_list())

    # radios
    stats['active_radios'] = {r: int((df['RadioNR'] == r).sum()) for r in set(df.RadioNR.to_list())}
    
    return stats, counts_10min, counts_30min, counts_60min
