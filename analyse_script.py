import matplotlib.pyplot as plt

from data import import_TF, import_vogele_data
from utils import estimate_road_length, trim_temperature_columns, plot_data, split_temperature_data, merge_temperature_data
from gradient_detection import detect_high_gradient_pixels
import config as cfg

if __name__ == '__main__':
    data = [import_vogele_data()] + list(import_TF())
    for n, df in enumerate(data):
        print('Processing data file #', n)
        df_temperature, df_rest = split_temperature_data(df)
        df_temperature = trim_temperature_columns(df_temperature, cfg.trim_threshold, cfg.percentage_above)
        df_temperature = trim_temperature_columns(df_temperature.T, cfg.trim_threshold, cfg.percentage_above).T
        offsets, non_road_pixels = estimate_road_length(df_temperature, cfg.roadlength_threshold)
        high_temperature_gradients = detect_high_gradient_pixels(df_temperature, offsets)
        df_temperature.values[high_temperature_gradients] = 40
        df_temperature.values[non_road_pixels] = 190
        df = merge_temperature_data(df_temperature, df_rest)
        snsplot = plot_data(df)
        plt.show()
        #plt.savefig("trimmed_data{}.png".format(n), dpi=800)
