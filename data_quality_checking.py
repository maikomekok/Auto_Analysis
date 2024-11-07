import pandas as pd
import os
import numpy as np
from scipy.stats import zscore

# Define constants
THRESHOLD = 300          # Threshold for sudden price changes and outliers
THRESHOLD_MS = 600        # Time difference threshold in milliseconds
WINDOW_SIZE = 20          # Rolling window size
MIN_STD = 1e-4            # Minimum standard deviation
MIN_CHANGE = 1e-4         # Minimum price change


price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols
bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols

def detect_sudden_price_changes_multiple(data, csv_file, price_cols=None):
    if price_cols is None:
        price_cols = all_price_cols

    sudden_changes_detected = False

    for price_col in price_cols:
        price_vals = data[price_col].values

        if len(price_vals) < WINDOW_SIZE + 1:
            print(f"Not enough data points in column {price_col} for the rolling window.")
            continue

        pct_changes = np.diff(price_vals) / price_vals[:-1]
        pct_changes_series = pd.Series(pct_changes)
        rolling_std = pct_changes_series.rolling(window=WINDOW_SIZE, min_periods=1).std().shift(1)
        rolling_std[rolling_std < MIN_STD] = np.nan
        standardized_pct_change = pct_changes_series / rolling_std
        sudden_changes = (np.abs(standardized_pct_change) > THRESHOLD) & (np.abs(pct_changes_series) > MIN_CHANGE)

        if sudden_changes.any():
            indices = sudden_changes[sudden_changes].index + 1
            print(f"Sudden price changes detected in column {price_col} of {csv_file} at indices {indices.tolist()}.")
            sudden_changes_detected = True

    return not sudden_changes_detected

def detect_time_based_outliers(data, timestamp_col):
    if timestamp_col not in data.columns:
        print(f"Timestamp column '{timestamp_col}' not found in the data.")
        return data, None

    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() *100
    outliers = data[data['time_diff_ms'] >= THRESHOLD_MS]
    print(f"Found {len(outliers)} time-based outliers where time difference exceeds {THRESHOLD_MS} milliseconds.")

    return data, outliers

# Interpolate zeros
def interpolate_zeros(data, price_cols):
    for price_col in price_cols:
        if price_col in data.columns:
            data[price_col] = pd.to_numeric(data[price_col], errors='coerce')
            zero_rows = data[data[price_col] == 0]
            if not zero_rows.empty:
                print(f"Found zero values in column {price_col}.")
                data[price_col].replace(0, np.nan)
                data[price_col].interpolate(method='linear')
                data[price_col].fillna(method='ffill')
                data[price_col].fillna(method='bfill')
    return data


def calculate_exp_smooth_volatility(price_diffs, alpha=0.2, init_vol=0):
    smooth_vol = np.zeros_like(price_diffs)
    previous_vol = init_vol
    for i in range(len(price_diffs)):
        smooth_vol[i] = previous_vol
        squared_diff = price_diffs[i] ** 2
        smoothed_var = alpha * squared_diff + (1 - alpha) * previous_vol
        previous_vol = smoothed_var
    return smooth_vol


def check_z_score_outliers(column_data, csv_file, col_name, threshold=THRESHOLD):
    z_scores = zscore(column_data)
    outliers = (abs(z_scores) > threshold)
    if outliers.any():
        print(f"Outliers detected in column {col_name} of CSV file {csv_file}")
        return False
    return True

def run_time_outlier_detection(directory_path, timestamp_col='date'):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()
        data, outliers = detect_time_based_outliers(data, timestamp_col)

        if outliers is not None and not outliers.empty:
            print(f"Time-based outliers found in {csv_file}:")
            print(outliers[['time_diff_ms', timestamp_col]])

def convert_date_col(data, timestamp_column):
    if timestamp_column not in data.columns:
        print(f"Column '{timestamp_column}' not found in the data.")
        return False

    if not pd.api.types.is_datetime64_any_dtype(data[timestamp_column]):
        data[timestamp_column] = pd.to_datetime(data[timestamp_column], errors='coerce')

    return True


def detect_zero_entries_multiple(data, price_cols, volume_cols):
    zero_entries = pd.Series(False, index=data.index)

    for price_col, volume_col in zip(price_cols, volume_cols):
        if price_col not in data.columns or volume_col not in data.columns:
            print(f"Skipping {price_col} and {volume_col} as they are not present in the data.")
            continue

        zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
        zero_entries = zero_entries | zero_condition

    zero_count = zero_entries.sum()
    print(f"Number of entries where both price and volume are zero in any pair: {zero_count}")
    return zero_count


def check_duplicates(data, csv_file):
    data_for_dup_check = data.iloc[:, 1:]  # Select all rows, and all columns except the first one

    duplicates = data_for_dup_check.duplicated(keep=False)
    duplicate_count = duplicates.sum()

    if duplicate_count > 0:
        print(f"{duplicate_count} duplicate rows found in {csv_file} (excluding the first column).")
        print("Duplicate rows:")
        print(data[duplicates])
    return duplicate_count


def run_quality_checks(directory_path):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()
        print(f"Columns in {csv_file}: {data.columns.tolist()}")
        data.fillna(method='ffill', inplace=True)

        check_duplicates(data, csv_file)

        zero_count = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
        interpolate_zeros(data, all_price_cols)

        if convert_date_col(data, 'date'):
            run_time_outlier_detection(directory_path, timestamp_col='date')
        else:
            print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")

        if not detect_sudden_price_changes_multiple(data, csv_file, price_cols=all_price_cols):
            print(f"Sudden price changes detected in {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")
