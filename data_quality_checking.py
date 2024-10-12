import pandas as pd
import os
import numpy as np
from scipy.stats import zscore



def detect_sudden_price_changes(data, csv_file, price_cols=None, window_size=20, threshold=70000):

    if price_cols is None:
        # Automatically detect price columns (bid and ask prices)
        price_cols = [col for col in data.columns if 'bid_prc' in col or 'ask_prc' in col]

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

        # Avoid division by zero or very small numbers
        epsilon = 1e-8
        rolling_std[rolling_std < epsilon] = epsilon

        # Standardize percentage changes
        standardized_pct_change = pct_changes_series / rolling_std

        # Detect sudden changes where standardized percentage change exceeds threshold
        sudden_changes = (np.abs(standardized_pct_change) > threshold) & (pct_changes_series != 0)



        if sudden_changes.any():
            sudden_change_indices = sudden_changes[sudden_changes].index + 1  # +1 to align with original data indices
            print(f"Sudden price changes detected in column {price_col} of {csv_file} at indices {sudden_change_indices.tolist()}.")
            sudden_changes_detected = True
        else:
            print(f"No sudden price changes detected in column {price_col} of {csv_file}.")

    return not sudden_changes_detected  # Return True if no sudden changes are found, False otherwise


def exponential_moving_average(alpha, previous_ema, current_val):
    return alpha * current_val + (1 - alpha) * previous_ema

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
def quality_check(data, csv_file):
    # Check for missing values
    if data.isnull().values.any():
        print(f"Missing data detected in {csv_file}.")
        return False

    # Check for duplicate rows
    if data.duplicated().any():
        print(f"Duplicate data detected in {csv_file}.")
        return False

    return True

def check_z_score_outliers(column_data, csv_file, col_name, threshold=70000):
    z_scores = zscore(column_data)
    outliers = (abs(z_scores) > threshold)
    if outliers.any():
        print(f"Outliers detected in column {col_name} of CSV file {csv_file}")
        return False
    return True

def time_outliers(data, csv_file, timestamp_col="date"):
    data = data.sort_values(by=timestamp_col)
    timediff = data[timestamp_col].diff().dt.total_seconds().dropna()

    if not check_z_score_outliers(timediff, csv_file, 'time_since_last_update'):
        return False

    return True

def convert_date_col(data, timestamp_column):

    if timestamp_column not in data.columns:
        print(f"Column '{timestamp_column}' not found in the data.")
        return False

    if not pd.api.types.is_datetime64_any_dtype(data[timestamp_column]):
        data[timestamp_column] = pd.to_datetime(data[timestamp_column], errors='coerce')

    return True

def check_price_outliers(data, csv_file, price_cols=None, base_alpha=0.2, init_vol=0, threshold=7000):
    """
    Detect price outliers by standardizing price differences using exponentially smoothed volatility.

    Args:
    - data: DataFrame containing price columns.
    - csv_file: Name of the CSV file (for error reporting).
    - price_cols: List of price columns to check for outliers.
    - base_alpha: Smoothing factor for exponential moving average.
    - init_vol: Initial volatility value for the first observation.
    - threshold: Threshold for detecting outliers.

    Returns:
    - True if no outliers are detected, False if outliers are found.

    """

    if price_cols is None:
        # Automatically detect price columns (bid and ask prices)
        price_cols = [col for col in data.columns if 'bid_prc' in col or 'ask_prc' in col]

    outliers_detected = False

    for price_col in price_cols:
        print(f"Processing price column: {price_col} in {csv_file}")

        price_vals = data[price_col].values

        # Check if there are enough data points
        if len(price_vals) < 2:
            print(f"Not enough data points in column {price_col} to compute price differences.")
            continue

        # Compute price differences
        price_diffs = np.diff(price_vals)

        # Calculate the exponentially smoothed volatility of price differences,
        # excluding the current squared difference
        smooth_vol = calculate_exp_smooth_volatility(price_diffs, base_alpha, init_vol)

        # Avoid division by zero or very small numbers to prevent inflated standardized scores
        epsilon = 1e-8
        smooth_vol[smooth_vol < epsilon] = epsilon

        # Standardize price differences
        standardized_price_diff = price_diffs / np.sqrt(smooth_vol)

        # Detect outliers where standardized price differences exceed threshold
        outliers = np.abs(standardized_price_diff) > threshold

        np.z


        if np.any(outliers):
            outlier_indices = np.where(outliers)[0] + 1  # +1 to align with original data indices
            print(f"Price outliers detected in column {price_col} of {csv_file} at indices {outlier_indices.tolist()}.")
            outliers_detected = True
        else:
            print(f"No price outliers detected in column {price_col} of {csv_file}.")

    return not outliers_detected  # Return True if no outliers are found, False otherwise


def remove_zero_entries(data, price_col, volume_col):
    # Identify rows where both price and volume are zero
    zero_entries = (data[price_col] == 0) & (data[volume_col] == 0)

    # Count how many zero entries there are
    zero_count = zero_entries.sum()
    print(f"Number of entries where both price and volume are zero: {zero_count}")

    # Remove those entries from the data
    data = data[~zero_entries].reset_index(drop=True)

    return data, zero_count


def run_quality_checks(directory_path):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)

        # Forward fill missing values
        data.fillna(method='ffill', inplace=True)

        # Print column names for debugging
        print(f"Columns in {csv_file}: {data.columns.tolist()}")
        price_col = 'price'
        volume_col = 'volume'
        data, zero_count = remove_zero_entries(data, price_col, volume_col)
        print(f"After removing zero entries, data has {len(data)} rows.")

        # Convert timestamp column before applying time outlier checks
        timestamp_col = 'date'  # Ensure this column exists or set it accordingly
        if convert_date_col(data, timestamp_col):
            # Run time outliers check only if timestamp conversion is successful
            if not time_outliers(data, csv_file, timestamp_col):
                print(f"Time-based outliers detected in {csv_file}.")
        else:
            print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")

        # Run price outliers detection on all price columns
        if not detect_sudden_price_changes(data, csv_file):
            print(f"Price outliers detected in {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")
