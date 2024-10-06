import pandas as pd
import os
from statistics import median
from scipy.stats import zscore


def check_price_outliers(data, csv_file, price_col='price', volatility_factor=1.5, base_threshold=3):
    """
    Adjust the Z-score threshold dynamically based on recent volatility.
    """
    # Calculate rolling volatility (standard deviation over the last N points)
    rolling_volatility = data[price_col].rolling(window=30).std()

    # Adjust the Z-score threshold based on volatility
    z_scores = zscore(data[price_col])
    dynamic_threshold = base_threshold + (volatility_factor * rolling_volatility / rolling_volatility.mean())

    outliers = (abs(z_scores) > dynamic_threshold.fillna(base_threshold))

    if outliers.any():
        print(f"Price outliers detected in column {price_col} of {csv_file}.")
        return False

    return True

def exponential_moving_average(alpha, previous_ema, current_val):

    return alpha * current_val + (1 - alpha) * previous_ema

def calculate_exp_smooth_volatility(price_vals, alpha=0.2, init_vol=0):
    # should I define initial volatility value as 0?

    smooth_vol = []
    for i in range(len(price_vals)):
        if i == 0:
            smooth_vol.append(init_vol)  # Initialize with the first volatility value
        else:
            # Calculate the squared price difference and apply the exponential moving average
            price_diff_squared = (price_vals[i] - price_vals[i - 1]) ** 2
            smooth_vol.append(round(exponential_moving_average(alpha, smooth_vol[-1], price_diff_squared), 6))

    return smooth_vol


def quality_check(data, csv_file):
    """Check for missing values, duplicates, and outliers."""

    # Check for missing values
    if data.isnull().values.any():
        print(f"Missing data detected in {csv_file}.")
        return False

    # Check for duplicate rows
    if data.duplicated().any():
        print(f"Duplicate data detected in {csv_file}.")
        return False

    # Check for outliers
    numerical_cols = data.select_dtypes(include=['float64', 'int64']).columns
    for col in numerical_cols:
        if not check_outliers(data[col], csv_file, col):
            return False

    return True


def check_z_score_outliers(column_data,csv_file,col_name,threshold = 3): #default threshold is 3 for the experiment
    z_scores = zscore(column_data)
    outliers = (abs(z_scores) > threshold)
    if outliers.any():
        print(f"Outliers detected in column {col_name} of csv file {csv_file}")
        return False
    return True

def time_outliers(data,csv_file,timestamp_col = "date"):
    data = data.sort_values(by=timestamp_col)
    timediff = data[timestamp_col].diff().dt.total_seconds().dropna()

    if not check_outliers(timediff, csv_file, 'time_since_last_update'):
        return False

    if not check_z_score_outliers(timediff, csv_file, 'time_since_last_update'):
        return False

    return True


def convert_date_col(data,timestamp_column):
    if timestamp_column not in data.columns:
        print(f"Column '{timestamp_column}' not found in the data.")
        return False

    if not pd.api.types.is_datetime64_any_dtype(data[timestamp_column]):
        data[timestamp_column] = pd.to_datetime(data[timestamp_column], errors='coerce')

    return True
def run_quality_checks(directory_path):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)

        # Print column names for debugging
        print(f"Columns in {csv_file}: {data.columns.tolist()}")

        # Convert timestamp column before applying time outlier checks
        timestamp_col = 'date'  # Ensure this column exists, or dynamically set it
        if convert_date_col(data, timestamp_col):
            # Run time outliers check only if timestamp conversion is successful
            if not time_outliers(data, csv_file, timestamp_col):
                print(f"Time-based outliers detected in {csv_file}.")
        else:
            print(f"Skipping time outliers check for {csv_file} due to missing timestamp column.")

        # Run general quality checks on the data
        if not quality_check(data, csv_file):
            print(f"Data quality check failed for {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")
