import numpy as np
import pandas as pd
from datetime import datetime

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
    df = df.sort_index()
    stats['Claimed points'] = df['Points'].sum()
    stats['Claimed mults'] = df['IsMultiplier1'].sum() + df['IsMultiplier2'].sum()
    stats['Claimed score'] = stats['Claimed mults'] * stats['Claimed points']

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

def generate_pefromance_data(df, increment : int, increment_unit : str):
    """ Generate performance per hour and per band from DXLOG frame 
        return: {ts, 160, 80, 40, 20, 15, 10, interval count, percent per interval}"""
    stats = {}
    bands = df[['Band', 'IsRunQSO', 'IsMultiplier1', 'IsMultiplier2']].sort_index() # select ts and band and sort it by ts
    cnt = len(bands)
    if cnt == 0:
        print('Empty data frame')
        return stats
    # I need to count Qs for every round operating hour
    # verify round hour
    start_date = bands.index[0].floor("h") #roundinig ts
    end_date = bands.index[-1].ceil("h")
    
    #generate analysis interval list
    if increment_unit not in ['minutes', 'hours']:
        raise ValueError("Unit must be minute or hour")

    increment = pd.Timedelta(**{increment_unit: increment})
    intervals = list(zip(pd.date_range(start_date, end_date - increment, freq=increment), 
                    pd.date_range(start_date + increment, end_date, freq=increment)))
    
    ts = bands.index
    for s, e in intervals:
        mask = ((s <= ts) & (ts < e))
        cnt_total = int(mask.sum())
        mult_total = (bands[mask].IsMultiplier1 | bands[mask].IsMultiplier2).sum()
        sel = bands[mask]
        stats[s] = (((sel.Band == 1.8).sum(), ((sel.Band == 1.8) & sel.IsRunQSO).sum()),
                    ((sel.Band == 3.5).sum(), ((sel.Band == 3.5) & sel.IsRunQSO).sum()),
                    ((sel.Band == 7.0).sum(), ((sel.Band == 7.0) & sel.IsRunQSO).sum()),
                    ((sel.Band == 14.0).sum(), ((sel.Band == 14.0) & sel.IsRunQSO).sum()),
                    ((sel.Band == 21.0).sum(), ((sel.Band == 21.0) & sel.IsRunQSO).sum()),
                    ((sel.Band == 28.0).sum(), ((sel.Band == 28.0) & sel.IsRunQSO).sum()),
                    mult_total,
                    cnt_total, round(100.0*float(sel.IsRunQSO.sum())/(cnt_total + 0.001)),
                    round(100.0*float(cnt_total)/cnt, 1))
    
    return stats

def get_hours(ts : pd.Timestamp):
    return ts.strftime('%H%M')

def log(level, str):
    print(level, str)