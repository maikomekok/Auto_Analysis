import pandas as pd
import os
from statistics import median
from scipy.stats import zscore



def check_outliers(column_data, csv_file, col_name):
    """
    Detect outliers using the Median Absolute Deviation (MAD) method.
    """
    median_val = median(column_data)
    mad_val = median([abs(x - median_val) for x in column_data])

    # Define a threshold for outlier detection (common choice is 3 times the MAD)
    threshold = 3 * mad_val
    outliers = [x for x in column_data if abs(x - median_val) > threshold]

    if len(outliers) > 0:
        print(f"Outliers detected in column {col_name} of {csv_file}.")
        return False
    return True


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
