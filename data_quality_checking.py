import pandas as pd
import os
import numpy as np
from scipy.stats import zscore

# Define constants
THRESHOLD = 3              # Threshold for sudden price changes
THRESHOLD_MS = 750         # Time difference threshold in milliseconds
WINDOW_SIZE = 20           # Rolling window size
MIN_STD = 1e-4             # Minimum standard deviation
MIN_CHANGE = 1000          # Minimum price change
Z_THRESHOLD = 4         # Z-score threshold for outliers

price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols
bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols


def detect_combined_outliers(data, csv_file, price_cols=None, z_threshold=Z_THRESHOLD, sudden_threshold=THRESHOLD,
                             min_change=MIN_CHANGE, window_size=WINDOW_SIZE, min_std=MIN_STD):
    total_outliers = 0  # Counter for all detected outliers (Z-score or sudden changes)

    if price_cols is None:
        price_cols = all_price_cols

    for price_col in price_cols:
        if price_col not in data.columns:
            print(f"Column {price_col} not found in data.")
            continue

        price_vals = data[price_col].values

        # Z-Score Outlier Detection
        z_scores = zscore(price_vals)
        z_outliers = np.abs(z_scores) > z_threshold
        z_outlier_count = z_outliers.sum()  # Count Z-score outliers
        total_outliers += z_outlier_count  # Add to total outlier count
        if z_outlier_count > 0:
            indices = np.where(z_outliers)[0]
            print(f"Z-score outliers detected in column {price_col} of {csv_file} at indices {indices.tolist()}.")

        # Sudden Price Change Detection
        if len(price_vals) >= window_size + 1:
            pct_changes = np.diff(price_vals) / price_vals[:-1]
            pct_changes_series = pd.Series(pct_changes)

            rolling_std = pct_changes_series.rolling(window=window_size, min_periods=1).std().shift(1)
            rolling_std[rolling_std < min_std] = np.nan
            standardized_pct_change = pct_changes_series / rolling_std
            sudden_changes = (np.abs(standardized_pct_change) > sudden_threshold) & (
                        np.abs(pct_changes_series) > min_change)

            sudden_change_count = sudden_changes.sum()  # Count sudden price changes
            total_outliers += sudden_change_count  # Add to total outlier count
            if sudden_change_count > 0:
                indices = sudden_changes[sudden_changes].index + 1  # Adjust for shift
                print(
                    f"Sudden price changes detected in column {price_col} of {csv_file} at indices {indices.tolist()}.")

    # Final summary
    if total_outliers == 0:
        print(f"No outliers or sudden price changes detected in {csv_file}.")
    else:
        print(f"{total_outliers} total outliers or sudden price changes detected in {csv_file}.")

    return total_outliers


def detect_time_based_outliers(data, timestamp_col):
    if timestamp_col not in data.columns:
        print(f"Timestamp column '{timestamp_col}' not found in the data.")
        return data, None

    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 100
    outliers = data[data['time_diff_ms'] >= THRESHOLD_MS]
    print(f"Found {len(outliers)} time-based outliers where time difference exceeds {THRESHOLD_MS} milliseconds.")

    return data, outliers


def interpolate_zeros(data, price_cols):
    for price_col in price_cols:
        if price_col in data.columns:
            data[price_col] = pd.to_numeric(data[price_col], errors='coerce')
            zero_rows = data[data[price_col] == 0]
            if not zero_rows.empty:
                print(f"Found zero values in column {price_col}.")
                data[price_col].replace(0, np.nan, inplace=True)
                data[price_col].interpolate(method='linear', inplace=True)
                data[price_col].fillna(method='ffill', inplace=True)
                data[price_col].fillna(method='bfill', inplace=True)
    return data


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
    return duplicate_count


def run_quality_checks(directory_path):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()
        print(f"Columns in {csv_file}: {data.columns.tolist()}")
        data.fillna(method='ffill', inplace=True)

        # Check for duplicates
        check_duplicates(data, csv_file)

        # Detect and interpolate zero entries
        zero_count = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
        interpolate_zeros(data, all_price_cols)

        # Convert date column for time-based checks
        if 'date' in data.columns:
            run_time_outlier_detection(directory_path, timestamp_col='date')
        else:
            print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")

        # Detect combined outliers and sudden price changes
        detect_combined_outliers(data, csv_file, price_cols=all_price_cols)

        print(f"Data quality check completed for {csv_file}.\n")

