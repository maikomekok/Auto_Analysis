import pandas as pd
import os
import numpy as np
from scipy.stats import zscore

# Define constants
THRESHOLD = 6              # Threshold for sudden price changes
THRESHOLD_MS = 750         # Time difference threshold in milliseconds
WINDOW_SIZE = 200           # Rolling window size
MIN_STD = 1e-4             # Minimum standard deviation
MIN_CHANGE = 50000          # Minimum price change
Z_THRESHOLD = 4            # Z-score threshold for outliers

price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols
bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols

def detect_combined_outliers(data, csv_file, price_cols=None, z_threshold=Z_THRESHOLD, sudden_threshold=THRESHOLD,
                             min_change=MIN_CHANGE, window_size=WINDOW_SIZE, min_std=MIN_STD):
    z_outlier_details = {}
    sudden_change_details = {}

    if price_cols is None:
        price_cols = all_price_cols

    for price_col in price_cols:
        if price_col not in data.columns:
            continue

        price_vals = data[price_col].values

        # Z-Score Outlier Detection
        z_scores = zscore(price_vals)
        z_outliers = np.abs(z_scores) > z_threshold
        z_indices = np.where(z_outliers)[0].tolist()
        if z_indices:
            z_outlier_details[price_col] = z_indices

        # Sudden Price Change Detection
        if len(price_vals) >= window_size + 1:
            pct_changes = np.diff(price_vals) / price_vals[:-1]
            pct_changes_series = pd.Series(pct_changes)

            rolling_std = pct_changes_series.rolling(window=window_size, min_periods=1).std().shift(1)
            rolling_std[rolling_std < min_std] = np.nan
            standardized_pct_change = pct_changes_series / rolling_std
            sudden_changes = (np.abs(standardized_pct_change) > sudden_threshold) & (np.abs(pct_changes_series) > min_change)

            sudden_indices = (np.where(sudden_changes)[0] + 1).tolist()
            if sudden_indices:
                sudden_change_details[price_col] = sudden_indices

    total_outliers = sum(len(indices) for indices in z_outlier_details.values()) + \
                     sum(len(indices) for indices in sudden_change_details.values())

    return total_outliers, z_outlier_details, sudden_change_details

def detect_time_based_outliers(data, timestamp_col):
    if timestamp_col not in data.columns:
        return 0, []

    data[timestamp_col] = pd.to_datetime(data[timestamp_col], format='%H:%M:%S.%fZ', errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 100
    time_outliers = data[data['time_diff_ms'] >= THRESHOLD_MS]
    print(time_outliers)
    return len(time_outliers), time_outliers.index.tolist()




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
    zero_entries_details = {}

    # Check for zero entries in the specified columns
    for price_col, volume_col in zip(price_cols, volume_cols):
        if price_col not in data.columns or volume_col not in data.columns:
            print(f"Skipping {price_col} and {volume_col} as they are not present in the data.")
            continue

        # Identify rows where both price and volume are zero
        zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
        if zero_condition.any():
            zero_indices = data[zero_condition].index.tolist()
            zero_entries_details[f"{price_col} & {volume_col}"] = zero_indices

    # Count total zero entries
    total_zero_count = sum(len(indices) for indices in zero_entries_details.values())

    return total_zero_count, zero_entries_details

def check_duplicates(data, csv_file):
    data_for_dup_check = data
    duplicates = data_for_dup_check.duplicated(keep=False)
    duplicate_count = duplicates.sum()
    duplicate_indices = data[duplicates].index.tolist()
    return duplicate_count, duplicate_indices


# def aggregate_data_quality_summary(detection_results):
#     total_rows = sum(result['total_rows'] for result in detection_results)
#     total_duplicates = sum(result['duplicates'] for result in detection_results)
#     total_zero_entries = sum(result['zero_entries'] for result in detection_results)
#     total_outliers_and_changes = sum(result['outliers_and_sudden_changes'] for result in detection_results)
#     total_time_outliers = sum(result['time_outliers'] for result in detection_results)
#
#     total_issues = total_duplicates + total_zero_entries + total_outliers_and_changes + total_time_outliers
#     good_data_percentage = ((total_rows - total_issues) / total_rows) * 100 if total_rows > 0 else 0
#     bad_data_percentage = (total_issues / total_rows) * 100 if total_rows > 0 else 0
#
#     summary = {
#         'total_rows': total_rows,
#         'duplicates': total_duplicates,
#         'zero_entries': total_zero_entries,
#         'outliers_and_sudden_changes': total_outliers_and_changes,
#         'time_outliers': total_time_outliers,
#         'total_issues': total_issues,
#         'good_data_percentage': good_data_percentage,
#         'bad_data_percentage': bad_data_percentage
#     }
#    # i decided csv file, but it can be anything
#     summary_df = pd.DataFrame([summary])
#     print("Data quality summary saved to data_quality_summary.csv")
#
#     return summary


# def run_quality_checks(directory_path):
#     csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
#
#     for csv_file in csv_files:
#         file_path = os.path.join(directory_path, csv_file)
#         data = pd.read_csv(file_path)
#         data.columns = data.columns.str.strip().str.lower()
#         print(f"Columns in {csv_file}: {data.columns.tolist()}")
#         data.fillna(method='ffill', inplace=True)
#
#         # Check for duplicates
#         check_duplicates(data, csv_file)
#
#         # Detect and interpolate zero entries
#         zero_count = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
#         interpolate_zeros(data, all_price_cols)
#
#         # Convert date column for time-based checks
#         if 'date' in data.columns:
#             run_time_outlier_detection(directory_path, timestamp_col='date')
#         else:
#             print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")
#
#         # Detect combined outliers and sudden price changes
#         detect_combined_outliers(data, csv_file, price_cols=all_price_cols)
#
#         print(f"Data quality check completed for {csv_file}.\n")
def run_quality_checks(directory_path, summary_file='data_quality_summary.csv'):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    summary_data = []
    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()
        data.fillna(method='ffill', inplace=True)

        duplicates_count, duplicates_indices = check_duplicates(data, csv_file)

        zero_count, zero_details = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
        interpolate_zeros(data, all_price_cols)

        outliers_count, z_outliers, sudden_changes = detect_combined_outliers(data, csv_file, price_cols=all_price_cols)

        if 'date' in data.columns:
            time_outliers_count, time_outliers_indices = detect_time_based_outliers(data, 'date')
        else:
            time_outliers_count, time_outliers_indices = 0, []

        total_issues = duplicates_count + zero_count + outliers_count + time_outliers_count

        summary_data.append({
            'file': csv_file,
            'total_rows': len(data),
            'duplicates': duplicates_count,
            'duplicates_indices': duplicates_indices,
            'zero_entries': zero_count,
            'zero_entries_details': zero_details,
            'outliers_and_sudden_changes': outliers_count,
            'z_outliers_details': z_outliers,
            'sudden_changes_details': sudden_changes,
            'time_outliers': time_outliers_count,
            'time_outliers_indices': time_outliers_indices,
            'total_issues': total_issues
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    print(f"Data quality summary saved to {summary_file}")
