
import pandas as pd
from statistics import median


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
