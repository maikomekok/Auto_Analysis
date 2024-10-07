import pandas as pd
import os
from statistics import median
from scipy.stats import zscore


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
    """Check for missing values, duplicates"""

    # Check for missing values
    if data.isnull().values.any():
        print(f"Missing data detected in {csv_file}.")
        return False

    # Check for duplicate rows
    if data.duplicated().any():
        print(f"Duplicate data detected in {csv_file}.")
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
def check_price_outliers(data, csv_file, price_cols=None, base_alpha=0.2, init_vol=0):
    """
    Detect price outliers by dynamically adjusting the Z-score threshold based on exponentially smoothed volatility.

    Args:
    - data: DataFrame containing price columns.
    - csv_file: Name of the CSV file (for error reporting).
    - price_cols: List of price columns to check for outliers. If None, automatically detect columns with 'bid_prc' or 'ask_prc'.
    - base_alpha: Base smoothing factor for exponential moving average (default is 0.2).
    - init_vol: Initial volatility value for the first observation (default is 0).

    Returns:
    - True if no outliers are detected, False if outliers are found.
    """
    if price_cols is None:
        # Automatically detect price columns (bid and ask prices)
        price_cols = [col for col in data.columns if col.startswith('bid_prc') or col.startswith('ask_prc')]

    outliers_detected = False

    for price_col in price_cols:
        print(f"Processing price column: {price_col} in {csv_file}")

        price_vals = data[price_col].values

        smooth_vol = calculate_exp_smooth_volatility(price_vals, base_alpha, init_vol)

        z_scores = zscore(price_vals)

        # Dynamically adjust the Z-score threshold based on smoothed volatility
        dynamic_threshold = 3 + 1.5 * pd.Series(smooth_vol).rolling(window=30).mean().fillna(0)

        # Detect outliers using the dynamically adjusted threshold
        outliers = abs(z_scores) > dynamic_threshold

        if outliers.any():
            print(f"Price outliers detected in column {price_col} of {csv_file}.")
            outliers_detected = True  # Set flag to true if any outliers are found

    return not outliers_detected  # Return True if no outliers are found, False otherwise


def run_quality_checks(directory_path):
    """
    Process all CSV files in the directory and apply quality checks.
    This includes time-based and price outlier detection.
    """
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)

        data.fillna(method='ffill', inplace=True)  # Forward filling missing values

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

        # Run price outliers detection on all price columns
        if not check_price_outliers(data, csv_file):
            print(f"Price outliers detected in {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")
