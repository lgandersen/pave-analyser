import pickle
import pandas as pd
import numpy as np

from .utils import split_temperature_data, merge_temperature_data
from .road_identification import trim_temperature, estimate_road_length
from .gradient_detection import detect_high_gradient_pixels


def _read_TF(filename):
    temperatures = ['T{}'.format(n) for n in range(141)]
    columns = ['distance'] + temperatures + ['distance_again']
    df = pd.read_csv(filename, skiprows=7, delimiter=',', names=columns)
    del df['distance_again']
    del df['T140'] # This is the last column of the dataset which is empty
    return df


temperatures_voegele = ['T{}'.format(n) for n in range(52)]
VOEGELE_BASE_COLUMNS = ['time', 'distance', 'latitude', 'longitude']


def _convert_vogele_timestamps(df, formatting):
    df['time'] = pd.to_datetime(df.time, format=formatting)


def _read_vogele_example(filename):
    """ Old example code. This is probably not going to be used. """
    columns = VOEGELE_BASE_COLUMNS + temperatures_voegele
    df = pd.read_csv(filename, skiprows=2, delimiter=';', names=columns, decimal=',')
    _convert_vogele_timestamps(df, "%d.%m.%Y %H:%M:%S")
    return df


def _read_vogele_M119(filename):
    """
    Data similar to the example file.
    NOTE removed last line in the file as it only contained 'Keine Daten vorhanden'.
    """
    columns = VOEGELE_BASE_COLUMNS + ['signal_quality'] + temperatures_voegele
    df = pd.read_csv(filename, skiprows=2, delimiter=';', names=columns, decimal=',')
    _convert_vogele_timestamps(df, "%d.%m.%Y %H:%M:%S")
    return df


def _read_vogele_taulov(filename):
    """
    NOTE removed last line in the file as it only contained 'No data to display'.
    """
    import csv
    columns = VOEGELE_BASE_COLUMNS + ['signal_quality'] + temperatures_voegele
    df = pd.read_csv(filename, skiprows=3, delimiter=',', names=columns, quoting=csv.QUOTE_NONE, quotechar='"', doublequote=True)
    for col in df.columns:
        if col == 'time':
            df[col] = df[col].apply(lambda x:x.strip('"'))
        if col in set(temperatures_voegele) | {'distance', 'latitude', 'longitude'}:
            df[col] = df[col].astype('str').apply(lambda x:x.strip('"')).astype('float')
    _convert_vogele_timestamps(df, "%d/%m/%Y %H:%M:%S")
    return df


_readers = {
        'TF':_read_TF,
        'voegele_example':_read_vogele_example,
        'voegele_M119':_read_vogele_M119,
        'voegele_taulov':_read_vogele_taulov
        }


def _cache_path(self, filepath):
    *_, fname = filepath.split('/')
    return self.cache_path.format(fname)


class PavementIRDataRaw:
    cache_path = './.cache/{}_raw.pickle'

    def __init__(self, title, filepath, reader, pixel_width, cache=True):
        self.title = title
        self.filepath = filepath
        self.reader = reader
        self.pixel_width = pixel_width
        self.df = _readers[reader](filepath)
        if cache:
            self.cache()

    @classmethod
    def from_cache(cls, title, filepath):
        try:
            with open(_cache_path(cls, filepath), 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def cache(self):
        with open(_cache_path(self, self.filepath), 'wb') as f:
            pickle.dump(self, f)

    @property
    def temperatures(self):
        df_temperature, _ = split_temperature_data(self.df)
        return df_temperature

    def resize(self, start, end):
        self.df = self.df[start:end]

    @property
    def pixel_height(self):
        t = self.df.distance.diff().describe()
        pixel_height = t['50%']
        return pixel_height


class PavementIRData(PavementIRDataRaw):
    cache_path = './.cache/{}.pickle'

    def __init__(self, data, roadwidth_threshold, adjust_npixel, gradient_tolerance, trim_threshold, percentage_above, cache=True):
        ### Copy attributes from PavementIRDataRaw instance
        self.title = data.title
        self.filepath = data.filepath
        self.reader = data.reader
        self.pixel_width = data.pixel_width

        ### Load the data and perform initial trimming
        self.df = self._trim_data(data.df, trim_threshold, percentage_above)
        self.offsets, self.road_pixels = estimate_road_length(self.temperatures.values, roadwidth_threshold, adjust_npixel)

        ### Perform gradient detection
        self.gradient_pixels, self.clusters = detect_high_gradient_pixels(
                self.temperatures.values, self.offsets, gradient_tolerance, diagonal_adjacency=True)
        if cache:
            self.cache()

    def _trim_data(self, df, trim_threshold, percentage_above):
        df = df.copy(deep=True)
        df_temperature, df_rest = split_temperature_data(df)
        df_temperature = trim_temperature(df_temperature, trim_threshold, percentage_above)
        return merge_temperature_data(df_temperature, df_rest)

    def resize(self, start, end):
        self.df = self.df[start:end]
        self.offsets = self.offsets[start:end]
        self.road_pixels = self.road_pixels[start:end]
        self.gradient_pixels = self.gradient_pixels[start:end]

    @property
    def nroad_pixels(self):
        return self.road_pixels.sum()