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


def run_quality_checks(directory_path):
    """Process all CSV files in the directory and apply quality checks."""
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)

        # Run quality checks on the data
        if not quality_check(data, csv_file):
            print(f"Data quality check failed for {csv_file}.")
        else:
            print(f"Data quality check passed for {csv_file}.")

def check_z_score_outliers(column_data,csv_file,col_name,threshold = 3):
    z_scores = zscore(column_data)
    outliers = (abs(z_scores)>threshold)
    if outliers.any():
        print(f"Outliers detected in column {col_name} of csv file {csv_file}")
