
import pandas as pd
from statistics import median
import os

def quality_check(data, csv_file):
    """
    Check for missing values and detect potential outliers in the dataset.
    Returns True if the data passes the quality checks, otherwise False.
    """

    # Check for missing values
    if data.isnull().values.any():
        print(f"Missing data detected in {csv_file}.")
        return False

    # Check for outliers in numerical columns using the MAD method
    numerical_cols = data.select_dtypes(include=['float64', 'int64']).columns

    for col in numerical_cols:
        if not check_outliers(data[col], csv_file, col):
            return False

    return True


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

def process_directory(directory_path):
    """Process all CSV files in a directory and apply data quality checks."""
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]

    # Iterate over each file in the directory
    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        data = pd.read_csv(file_path)


        # Perform quality checks on each file
        if not quality_check(data, csv_file):
            print(f"Data quality check failed for {csv_file}")
        else:            print(f"Data quality check passed for {csv_file}")

def timestamp_consistency():
    pass

def duplicate_values_check():
    pass



