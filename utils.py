import pandas as pd
import seaborn as sns
import re

is_temperature = re.compile('T\d+')

def split_temperature_data(df):
    temperature = temperature_columns(df)
    df_temperature = df[temperature]
    not_temperature = set(df.columns) - set(temperature)
    df_rest = df[list(not_temperature)]
    return df_temperature, df_rest

def merge_temperature_data(df_temp, df_rest):
    return pd.merge(df_temp, df_rest, how='inner', copy=True, left_index=True, right_index=True)


def temperature_columns(df):
    temperature_columns = []
    for column in df.columns:
        if is_temperature.match(column) is not None:
            temperature_columns.append(column)
    return temperature_columns


def trim_temperature_columns(df, threshold, percentage_above):
    for column_name in df.columns:
        if not trim(df, column_name, threshold, percentage_above):
            break

    for column_name in reversed(df.columns):
        if not trim(df, column_name, threshold, percentage_above):
            break
    return df


def trim(df, column, threshold_temp, percentage_above):
    above_threshold = sum(df[column] > threshold_temp)
    above_threshold_pct = 100 * (above_threshold / len(df))
    if above_threshold_pct > percentage_above:
        return False
    else:
        del df[column]
        return True


def estimate_road_edge_right(line, threshold):
    cond = line < threshold
    count = 0
    while True:
        if any(cond[count:count + 3]):
            count += 1
        else:
            break
    return count

def estimate_road_edge_left(line, threshold):
    cond = line < threshold
    count = len(line)
    while True:
        if any(cond[count - 3:count]):
            count -= 1
        else:
            break
    return count


def estimate_road_length(df, threshold):
    values = df.values
    for distance_idx in range(values.shape[0]):
        offset = estimate_road_edge_right(values[distance_idx, :], threshold)
        values[distance_idx, :offset] = 190

        offset = estimate_road_edge_left(values[distance_idx, :], threshold)
        values[distance_idx, offset:] = 190


def plot_data(df):
    columns = temperature_columns(df)
    snsplot = sns.heatmap(df[columns], cmap='RdYlGn_r', vmin=60)#, square=True)
    return snsplot
