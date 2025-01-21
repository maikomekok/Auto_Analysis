import os
import re
import json
import tarfile
import logging
from datetime import datetime

import pandas as pd

logging.basicConfig(level=logging.INFO)

RELATIVE_CHANGE_THRESHOLD = 0.30
ABSOLUTE_CHANGE_THRESHOLD = 1000
LOOKBACK_WINDOW = 20
MAX_VALID_PRICE = 1e9

price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{i}' for i in price_levels]
ask_price_cols = [f'ask_prc{i}' for i in price_levels]
all_price_cols = bid_price_cols + ask_price_cols

bid_volume_cols = [f'bid_vol{i}' for i in price_levels]
ask_volume_cols = [f'ask_vol{i}' for i in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols


def is_valid_price(price,
                   last_valid_price=None,
                   relative_threshold=RELATIVE_CHANGE_THRESHOLD,
                   absolute_threshold=ABSOLUTE_CHANGE_THRESHOLD):
    """
    Determines whether a given 'price' is valid.
      - Must be a positive float >= 10.0 and < MAX_VALID_PRICE.
      - Relative change (vs. last_valid_price) must be below 'relative_threshold'.
      - Absolute change must be below 'absolute_threshold'.
    """
    try:
        price_float = float(price)
    except (ValueError, TypeError):
        logging.debug(f"Invalid price type or unable to convert: {price}")
        return False

    # Basic bounds check
    if price_float <= 0 or price_float < 10:
        logging.debug(f"Invalid price due to being <= 0 or < 10: {price_float}")
        return False
    if price_float > MAX_VALID_PRICE:
        logging.debug(f"Invalid price due to exceeding MAX_VALID_PRICE: {price_float}")
        return False

    # Optional checks against last_valid_price
    if last_valid_price is not None and last_valid_price > 0:
        rel_change = abs(price_float - last_valid_price) / last_valid_price
        if rel_change > relative_threshold:
            logging.debug(
                f"Price {price_float} outlier (relative change: {rel_change:.2%} > {relative_threshold:.2%})."
            )
            return False

        abs_change = abs(price_float - last_valid_price)
        if abs_change > absolute_threshold:
            logging.debug(
                f"Price {price_float} outlier (absolute change: {abs_change} > {absolute_threshold})."
            )
            return False

    return True


def custom_btc_outlier_detection(data, price_cols, volume_cols,
                                 relative_change_threshold=RELATIVE_CHANGE_THRESHOLD,
                                 absolute_change_threshold=ABSOLUTE_CHANGE_THRESHOLD,
                                 lookback_window=LOOKBACK_WINDOW):
    """
    Flags outliers in price columns based on:
      - Price == 0 while volume != 0
      - Price fails 'is_valid_price' checks vs. last_valid_price
    Returns a dict of { price_col : [row indices] } of outliers.
    """
    outliers = {}

    for price_col, volume_col in zip(price_cols, volume_cols):
        if price_col not in data.columns or volume_col not in data.columns:
            continue

        prices = pd.to_numeric(data[price_col], errors='coerce')
        volumes = pd.to_numeric(data[volume_col], errors='coerce')

        outlier_indices = []
        last_valid_price = None

        for i in range(len(prices)):
            current_price = prices.iloc[i]
            current_volume = volumes.iloc[i]

            # Skip NaN prices
            if pd.isna(current_price):
                continue

            # If both price and volume are zero => skip (assume no data)
            if (current_price == 0) and (current_volume == 0):
                continue

            # If price=0 but volume!=0 => outlier
            if (current_price == 0) and (current_volume != 0):
                outlier_indices.append(i)
                continue

            # Check the price validity
            if not is_valid_price(
                    current_price,
                    last_valid_price,
                    relative_change_threshold,
                    absolute_change_threshold
            ):
                outlier_indices.append(i)
                continue

            # Update last_valid_price if everything is valid
            last_valid_price = current_price

        if outlier_indices:
            outliers[price_col] = outlier_indices

    return outliers


def detect_zero_entries_multiple(data, price_cols, volume_cols):
    """
    Counts and indexes where both price and volume are zero for each col pair.
    Returns:
      total_zero_count, { "bid_prcX & bid_volX": [row indices], ... }
    """
    zero_entries_details = {}

    for price_col, volume_col in zip(price_cols, volume_cols):
        if price_col not in data.columns or volume_col not in data.columns:
            continue

        zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
        if zero_condition.any():
            zero_indices = data[zero_condition].index.tolist()
            zero_entries_details[f"{price_col} & {volume_col}"] = zero_indices

    total_zero_count = sum(len(indices) for indices in zero_entries_details.values())
    return total_zero_count, zero_entries_details


def check_duplicates(data):
    """
    Finds duplicate rows in the given DataFrame.
    Returns:
      duplicate_count, [list of row indices that are duplicated].
    """
    duplicates = data.duplicated(keep=False)
    duplicate_count = duplicates.sum()
    duplicate_indices = data[duplicates].index.tolist()
    return duplicate_count, duplicate_indices


def detect_time_based_outliers(data, timestamp_col, threshold_ms=300):
    """
    Sorts data by timestamp_col, calculates time diffs (ms), and flags rows
    where diff >= threshold_ms. Returns:
      number_of_outliers,
      list_of_outlier_indices,
      time_differences_df,
      outlier_rows_df,
      average_time_diff
    """
    if timestamp_col not in data.columns:
        return 0, [], pd.DataFrame(), pd.DataFrame(), None

    data = data.dropna(subset=[timestamp_col]).copy()
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors='coerce')
    data = data.sort_values(by=timestamp_col)

    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 1000
    time_differences = data[['time_diff_ms']].copy()
    time_outliers = data[data['time_diff_ms'] >= threshold_ms]
    average_time_diff = data['time_diff_ms'].mean()

    return len(time_outliers), time_outliers.index.tolist(), time_differences, time_outliers, average_time_diff


def extract_date_from_filename(filename):
    """
    Extracts a date from the filename in the format YYYY-MM-DD via regex.
    If no match, returns today's date as YYYY-MM-DD.
    """
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return datetime.now().strftime('%Y-%m-%d')


def extract_tar_gz(file_path, extract_path):
    """
    Extracts the .tar.gz file at 'file_path' into 'extract_path'.
    """
    with tarfile.open(file_path, 'r:gz') as tar:
        tar.extractall(path=extract_path)
        logging.info(f"Extracted {file_path} to {extract_path}")


def identify_exchange_code(filename):
    """
    Uses regex to find '_digits.csv' in a filename. E.g. 'foo_1234.csv' => '1234'
    Returns None if no match found.
    """
    base = os.path.basename(filename)
    match = re.search(r'_(\d+)\.csv$', base)
    if match:
        return match.group(1)
    return None


def cleanup_directory(directory_path):
    """
    Deletes all files and empty subdirectories under 'directory_path',
    then removes directory_path itself if empty.
    """
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir_ in dirs:
            dir_path = os.path.join(root, dir_)
            os.rmdir(dir_path)

    try:
        os.rmdir(directory_path)
        logging.info(f"Removed empty directory: {directory_path}")
    except OSError:
        pass

    logging.info(f"Cleaned up directory: {directory_path}")


def split_and_tar_summary(summary_df,
                          rows_per_file=1000,
                          tar_file_name='summary_archive.tar.gz'):
    """
    Splits 'summary_df' into chunks of size 'rows_per_file' and writes them to CSV.
    Then archives all CSVs into 'tar_file_name'.
    """
    output_dir = os.path.dirname(tar_file_name)
    if not output_dir:
        output_dir = '.'  # if tar_file_name has no path, use current dir

    os.makedirs(output_dir, exist_ok=True)

    temp_summary_dir = os.path.join(output_dir, 'summary_files')
    os.makedirs(temp_summary_dir, exist_ok=True)

    total_rows = len(summary_df)
    logging.info(f"Preparing to split {total_rows} rows into chunks of {rows_per_file}.")

    # Write chunked CSV files
    part_number = 0
    for start_idx in range(0, total_rows, rows_per_file):
        end_idx = start_idx + rows_per_file
        chunk = summary_df.iloc[start_idx:end_idx]
        part_number += 1
        chunk_file = os.path.join(temp_summary_dir, f'summary_part_{part_number}.csv')
        chunk.to_csv(chunk_file, index=False)
        logging.info(f"Created chunk file: {chunk_file}")

    # Tar all chunk files
    with tarfile.open(tar_file_name, 'w:gz') as tar:
        for file in os.listdir(temp_summary_dir):
            file_path = os.path.join(temp_summary_dir, file)
            tar.add(file_path, arcname=file)
            logging.info(f"Added {file} to archive {tar_file_name}")

    # Clean up the temporary chunk files
    cleanup_directory(temp_summary_dir)
    logging.info(f"Summary archive created at: {tar_file_name}")


def run_quality_checks(directory_path, output_path, rows_per_file=1000):
    """
    Looks for CSV files in 'directory_path', runs multiple data-quality checks:
      - Duplicates
      - Zero price/volume
      - Custom outlier detection
      - Time-based outliers (on the first recognized timestamp column)
    Skips files containing 'DERIBIT' in the path.
    Summarizes issues into a DataFrame and then archives by 'exchange_code'.
    """
    csv_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(root, file))

    if not csv_files:
        logging.warning(f"No CSV files found in {directory_path}. Skipping...")
        return

    # Pick a date (from the first CSV) to name output folders
    first_date = extract_date_from_filename(os.path.basename(csv_files[0]))

    summary_data = []

    for csv_file in csv_files:
        if "DERIBIT" in csv_file.upper():
            logging.info(f"Skipping DERIBIT file: {csv_file}")
            continue

        logging.info(f"Processing file: {csv_file}")

        try:
            data = pd.read_csv(csv_file)
            # Standardize column names
            data.columns = data.columns.str.strip().str.lower()
            # Forward fill to handle missing data
            data.fillna(method='ffill', inplace=True)

            # 1. Check duplicates
            duplicates_count, duplicates_indices = check_duplicates(data)

            # 2. Zero entries
            zero_count, zero_details = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)

            # 3. Custom outlier detection
            custom_outliers = custom_btc_outlier_detection(data, all_price_cols, all_volume_cols)
            total_outliers = sum(len(indices) for indices in custom_outliers.values())

            # 4. Time-based outliers
            # We'll check for 'timestamp', 'date', or 'time' columns in that order.
            time_outliers_count = 0
            time_outliers_indices = []
            average_time_diff = None

            for ts_col in ['timestamp', 'date', 'time']:
                if ts_col in data.columns:
                    (time_outliers_count,
                     time_outliers_indices,
                     _,
                     _,
                     average_time_diff) = detect_time_based_outliers(data, ts_col)
                    break

            # Sum up total issues
            total_issues = (
                    duplicates_count
                    + zero_count
                    + total_outliers
                    + time_outliers_count
            )

            exchange_code = identify_exchange_code(csv_file)
            logging.info(f"Identified exchange code for {csv_file}: {exchange_code}")

            # If you want to include ONLY files with issues OR truly empty files, do:
            #   if (len(data) == 0) or (total_issues != 0):
            # Otherwise, if you want to log everything, remove this condition
            if total_issues != 0 or len(data) == 0:
                summary_entry = {
                    'file': csv_file,
                    'exchange_code': exchange_code,
                    'total_rows': len(data),
                    'duplicates': duplicates_count,
                    'duplicates_indices': json.dumps(duplicates_indices),
                    'zero_entries': zero_count,
                    'zero_entries_details': json.dumps(zero_details),
                    'custom_price_outliers': total_outliers,
                    'outliers_details': json.dumps(custom_outliers),
                    'time_outliers': time_outliers_count,
                    'time_outliers_indices': json.dumps(time_outliers_indices),
                    'avg_time_diff_ms': average_time_diff,
                    'total_issues': total_issues
                }
                summary_data.append(summary_entry)

        except pd.errors.EmptyDataError:
            # Means the CSV is truly empty (no headers, etc.)
            logging.warning(f"Empty file detected: {csv_file}")
            exchange_code = identify_exchange_code(csv_file)
            summary_data.append({
                'file': csv_file,
                'exchange_code': exchange_code,
                'total_rows': 0,
                'duplicates': 0,
                'duplicates_indices': json.dumps([]),
                'zero_entries': 0,
                'zero_entries_details': json.dumps({}),
                'custom_price_outliers': 0,
                'outliers_details': json.dumps({}),
                'time_outliers': 0,
                'time_outliers_indices': json.dumps([]),
                'avg_time_diff_ms': None,
                'total_issues': 0
            })

        except Exception as e:
            logging.error(f"Error processing file {csv_file}: {e}")

    # After processing ALL CSVs, group and create archives if there's anything in summary_data
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        grouped = summary_df.groupby('exchange_code')

        for exchange_code, group_df in grouped:
            if not exchange_code:
                exchange_code = "UNKNOWN"

            daily_folder = os.path.join(output_path, first_date)
            os.makedirs(daily_folder, exist_ok=True)

            tar_file_name = os.path.join(
                daily_folder, f'{first_date}_btc_data_quality_summary_{exchange_code}.tar.gz'
            )
            split_and_tar_summary(
                group_df,
                rows_per_file=rows_per_file,
                tar_file_name=tar_file_name
            )
            logging.info(f"Summary for exchange code {exchange_code} saved to {tar_file_name}")

    else:
        logging.warning(f"No issues found in CSV files from {directory_path}. No summary created.")


def process_daily_data(input_folder, output_folder):
    """
    High-level workflow:
      1. Find .tar.gz files in 'input_folder'.
      2. Extract each archive, then run quality checks on the extracted CSVs.
      3. (Optionally) create a daily summary archive from 'output_folder' contents.
      4. Clean up the extracted .tar.gz or input folder if needed.
    """
    tar_files = [f for f in os.listdir(input_folder) if f.endswith('.tar.gz')]
    if not tar_files:
        logging.warning(f"No .tar.gz files found in {input_folder}.")
        return

    for tar_file in tar_files:
        tar_file_path = os.path.join(input_folder, tar_file)
        logging.info(f"Processing archive: {tar_file_path}")

        # 1. Extract tar.gz
        extract_tar_gz(tar_file_path, input_folder)

        # 2. lolll,,,, Run quality checks (creates tar.gz summary per exchange_code)
        run_quality_checks(input_folder, output_folder)

        # date_str = extract_date_from_filename(tar_file)
        # daily_archive = os.path.join(output_folder, f'{date_str}_summary.tar.gz')
        # with tarfile.open(daily_archive, 'w:gz') as tar:
        #     for root, dirs, files in os.walk(output_folder):
        #         for file_ in files:
        #             file_path = os.path.join(root, file_)
        #             if file_path == daily_archive:
        #                 continue
        #             tar.add(file_path, arcname=file_)
        # logging.info(f"Daily summary archive created at: {daily_archive}")

        # 3. Optionally remove the original tar file, or all extracted CSVs:
        # os.remove(tar_file_path)
        # logging.info(f"Deleted processed .tar.gz file: {tar_file_path}")

        # Or cleanup the entire input folder if you want to remove extracted data:
        cleanup_directory(input_folder)
        logging.info(f"Cleaned up extracted data in: {input_folder}")
