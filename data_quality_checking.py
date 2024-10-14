import pandas as pd
import os
import numpy as np
from scipy.stats import zscore

price_levels = range(1, 21)  # Levels from 1 to 20

bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols

bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols


def detect_sudden_price_changes_multiple(data, csv_file, price_cols=None, window_size=20, threshold=3, min_std=1e-4, min_change=1e-4):
    if price_cols is None:
        price_cols = all_price_cols

    sudden_changes_detected = False

    for price_col in price_cols:
        print(f"Processing price column: {price_col} in {csv_file}")

        price_vals = data[price_col].values

        # Check if there are enough data points
        if len(price_vals) < window_size + 1:
            print(f"Not enough data points in column {price_col} for the rolling window.")
            continue

        # Compute percentage price changes
        pct_changes = np.diff(price_vals) / price_vals[:-1]

        # Convert to pandas Series for rolling calculations
        pct_changes_series = pd.Series(pct_changes)

        # Calculate rolling standard deviation excluding the current observation
        rolling_std = pct_changes_series.rolling(window=window_size, min_periods=1).std().shift(1)

        # Set rolling_std to NaN where it's below the minimum standard deviation
        rolling_std[rolling_std < min_std] = np.nan

        # Standardize percentage changes, ignoring divisions by NaN
        standardized_pct_change = pct_changes_series / rolling_std

        # Detect sudden changes where standardized percentage change exceeds threshold
        sudden_changes = (np.abs(standardized_pct_change) > threshold) & (np.abs(pct_changes_series) > min_change)

        if sudden_changes.any():
            sudden_change_indices = sudden_changes[sudden_changes].index + 1  # +1 to align with original data indices
            print(f"Sudden price changes detected in column {price_col} of {csv_file} at indices {sudden_change_indices.tolist()}.")
            sudden_changes_detected = True
        else:
            print(f"No sudden price changes detected in column {price_col} of {csv_file}.")

    return not sudden_changes_detected  # Return True if no sudden changes are found, False otherwise

def interpolate_zeros(data, price_cols):
    for price_col in price_cols:
        if price_col in data.columns:
            # Convert the column to a numeric type (if it isn't already)
            data[price_col] = pd.to_numeric(data[price_col], errors='coerce')

            # Print rows with zero values for debugging
            zero_rows = data[data[price_col] == 0]
            if not zero_rows.empty:
                print(f"Found zero values in column {price_col}:")
                print(zero_rows)

                # Replace zero values with NaN and then interpolate
                data[price_col].replace(0, np.nan, inplace=True)

                # Perform the interpolation
                data[price_col].interpolate(method='linear', inplace=True)

                # Optionally fill remaining NaN values (if any zeros were at the start or end)
                data[price_col].fillna(method='ffill', inplace=True)
                data[price_col].fillna(method='bfill', inplace=True)

    return data
def calculate_exp_smooth_volatility(price_diffs, alpha=0.2, init_vol=0):
    smooth_vol = np.zeros_like(price_diffs)
    previous_vol = init_vol
    for i in range(len(price_diffs)):
        # Use previous_vol as the volatility estimate for standardization
        smooth_vol[i] = previous_vol
        # Update previous_vol with the current squared difference
        squared_diff = price_diffs[i] ** 2
        smoothed_var = alpha * squared_diff + (1 - alpha) * previous_vol
        previous_vol = smoothed_var
    return smooth_vol

# Function to check for z-score outliers
def check_z_score_outliers(column_data, csv_file, col_name, threshold=3000):
    z_scores = zscore(column_data)
    outliers = (abs(z_scores) > threshold)
    if outliers.any():
        print(f"Outliers detected in column {col_name} of CSV file {csv_file}")
        return False
    return True


def detect_time_based_outliers(data, timestamp_col, threshold_ms=600):
    if timestamp_col not in data.columns:
        print(f"Timestamp column '{timestamp_col}' not found in the data.")
        return data, None
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 1000  # Convert to milliseconds
    outliers = data[data['time_diff_ms'] > threshold_ms]
    print(f"Found {len(outliers)} time-based outliers where time difference exceeds {threshold_ms} milliseconds.")

    return data, outliers

def run_time_outlier_detection(directory_path, timestamp_col='date', threshold_ms=600):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()
        data, outliers = detect_time_based_outliers(data, timestamp_col, threshold_ms)

        if outliers is not None and not outliers.empty:
            print(f"Time-based outliers found in {csv_file}:")
            print(outliers[['time_diff_ms', timestamp_col]])
        else:
            print(f"No time-based outliers found in {csv_file}.")


def convert_date_col(data, timestamp_column):
    if timestamp_column not in data.columns:
        print(f"Column '{timestamp_column}' not found in the data.")
        return False

    if not pd.api.types.is_datetime64_any_dtype(data[timestamp_column]):
        data[timestamp_column] = pd.to_datetime(data[timestamp_column], errors='coerce')

    return True

# Function to remove zero entries from price-volume pairs
def detect_zero_entries_multiple(data, price_cols, volume_cols):
    zero_entries = pd.Series(False, index=data.index)

    for price_col, volume_col in zip(price_cols, volume_cols):
        # Check if both price and volume columns exist in the data
        if price_col not in data.columns or volume_col not in data.columns:
            print(f"Skipping {price_col} and {volume_col} as they are not present in the data.")
            continue

        # Check if both price and volume are zero
        zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
        zero_entries = zero_entries | zero_condition

    zero_count = zero_entries.sum()
    print(f"Number of entries where both price and volume are zero in any pair: {zero_count}")

    return  zero_count


# Main function to run data quality checks
def run_quality_checks(directory_path):

    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)

        # Normalize column names to avoid issues with inconsistent formatting
        data.columns = data.columns.str.strip().str.lower()

        # Print column names for debugging
        print(f"Columns in {csv_file}: {data.columns.tolist()}")

        # Forward fill missing values
        data.fillna(method='ffill', inplace=True)

        price_cols = [col for col in data.columns if 'bid_prc' in col or 'ask_prc' in col]  # Example column filtering

        zero_count = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)

        data = interpolate_zeros(data, price_cols)
        data.to_csv(file_path, index=False)
        print(f"Interpolated values saved back to {csv_file}.")


        # Convert timestamp column before applying time outlier checks
        timestamp_col = 'date'  # Ensure this column exists or set it accordingly
        if convert_date_col(data, timestamp_col):
            # Run time outliers check only if timestamp conversion is successful
            if not run_time_outlier_detection(directory_path):
                print(f"Time-based outliers detected in {csv_file}.")
        else:
            print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")

        # Run detection of sudden price changes on all price columns
        if not detect_sudden_price_changes_multiple(data, csv_file, price_cols=all_price_cols):
            print(f"Sudden price changes detected in {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")
