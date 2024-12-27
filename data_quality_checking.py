import pandas as pd
import os
import json
import logging
import tarfile
import re

logging.basicConfig(level=logging.INFO)

RELATIVE_CHANGE_THRESHOLD = 0.30
ABSOLUTE_CHANGE_THRESHOLD = 1000
LOOKBACK_WINDOW = 20

price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols
bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols
MAX_VALID_PRICE = 1e9


def extract_date_from_filename(filename):
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return None


def is_valid_price(price, last_valid_price=None, relative_threshold=RELATIVE_CHANGE_THRESHOLD):
    try:
        price_float = float(price)
        if price_float <= 0 or price_float < 10:
            logging.debug(f"Invalid price due to being negative or too small: {price_float}")
            return False
        if price_float > MAX_VALID_PRICE:
            logging.debug(f"Invalid price due to exceeding max valid price: {price_float}")
            return False
        if last_valid_price is not None:
            relative_change = abs(price_float - last_valid_price) / last_valid_price
            if relative_change > relative_threshold:
                logging.debug(f"Price {price_float} is outlier (relative change: {relative_change})")
                return False
        return True
    except (ValueError, TypeError) as e:
        logging.debug(f"Error processing price: {e}")
        return False

def custom_btc_outlier_detection(data, price_cols, volume_cols,
                                 relative_change_threshold=RELATIVE_CHANGE_THRESHOLD,
                                 absolute_change_threshold=ABSOLUTE_CHANGE_THRESHOLD,
                                 lookback_window=LOOKBACK_WINDOW):
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

            if pd.isna(current_price):
                continue

            if (current_price == 0) and (current_volume == 0):
                continue

            if (current_price == 0) and (current_volume != 0):
                outlier_indices.append(i)
                continue

            if not is_valid_price(current_price, last_valid_price):
                outlier_indices.append(i)
                continue

            last_valid_price = current_price

        if outlier_indices:
            outliers[price_col] = outlier_indices
    return outliers

def detect_zero_entries_multiple(data, price_cols, volume_cols):
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
    duplicates = data.duplicated(keep=False)
    duplicate_count = duplicates.sum()
    duplicate_indices = data[duplicates].index.tolist()
    return duplicate_count, duplicate_indices

def detect_time_based_outliers(data, timestamp_col, threshold_ms=300):
    if timestamp_col not in data.columns:
        return 0, [], pd.DataFrame(), pd.DataFrame(), None
    data = data.dropna(subset=[timestamp_col])
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 1000
    time_differences = data[['time_diff_ms']].copy()
    time_outliers = data[data['time_diff_ms'] >= threshold_ms]
    average_time_diff = data['time_diff_ms'].mean()  # Calculate the average time difference
    return len(time_outliers), time_outliers.index.tolist(), time_differences, time_outliers, average_time_diff


def split_and_tar_summary(summary_df, rows_per_file=600, tar_file_name='summary_archive.tar.gz'):
    output_dir = 'summary_files'
    os.makedirs(output_dir, exist_ok=True)
    total_rows = len(summary_df)
    file_count = 0
    file_names = []

    for start in range(0, total_rows, rows_per_file):
        end = min(start + rows_per_file, total_rows)
        chunk = summary_df.iloc[start:end]
        file_name = os.path.join(output_dir, f'summary_part_{file_count + 1}.csv')
        chunk.to_csv(file_name, index=False)
        file_count += 1
        logging.info(f"Created: {file_name}")
        file_names.append(file_name)

    with tarfile.open(tar_file_name, 'w:gz') as tar:
        for fn in file_names:
            tar.add(fn, arcname=os.path.basename(fn))
            logging.info(f"Added to TAR.GZ: {fn}")

    logging.info(f"All files compressed into: {tar_file_name}")

    for fn in file_names:
        os.remove(fn)
    os.rmdir(output_dir)

def identify_exchange_code(filename):
    base = os.path.basename(filename)
    match = re.search(r'_(\d+)\.csv$', base)
    print(match)
    if match:
        return match.group(1)
    return None

def run_quality_checks(directory_path, rows_per_file=600):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    summary_data = []

    for csv_file in csv_files:
        logging.info(f"Working on file name: {csv_file}")
        if "DERIBIT" in csv_file:
            continue
        file_path = os.path.join(directory_path, csv_file)
        try:
            data = pd.read_csv(file_path)
            data.columns = data.columns.str.strip().str.lower()
            data.fillna(method='ffill', inplace=True)

            duplicates_count, duplicates_indices = check_duplicates(data)
            zero_count, zero_details = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
            custom_outliers = custom_btc_outlier_detection(data, all_price_cols, all_volume_cols)

            time_outliers_count = 0
            time_outliers_indices = []
            time_outliers = pd.DataFrame()

            for ts_col in ['timestamp', 'date', 'time']:
                if ts_col in data.columns:
                    (time_outliers_count, time_outliers_indices,
                     _, time_outliers, avg_time_diff) = detect_time_based_outliers(data, ts_col)
                    break

            total_outliers = sum(len(indices) for indices in custom_outliers.values())
            total_issues = duplicates_count + zero_count + total_outliers + time_outliers_count

            exchange_code = identify_exchange_code(csv_file)

            summary_entry = {
                'file': csv_file,
                'exchange_code': exchange_code,
                'total_rows': len(data),
                'duplicates': duplicates_count,
                'duplicates_indices': json.dumps(duplicates_indices),
                'zero_entries': zero_count,
                'zero_entries_details': json.dumps(zero_details),
                'total_outliers': total_outliers,
                'outliers_details': json.dumps(custom_outliers),
                'time_outliers': time_outliers_count,
                'time_outliers_indices': json.dumps(time_outliers_indices),
                'average_time_diff_ms': avg_time_diff,
                'total_issues': total_issues
            }

            if time_outliers_count > 0 and 'time_diff_ms' in time_outliers.columns:
                time_diff_ms_dict = time_outliers['time_diff_ms'].dropna().to_dict()
                summary_entry['time_outliers_ms'] = json.dumps(time_diff_ms_dict)

            if total_issues != 0:
                summary_data.append(summary_entry)

        except pd.errors.EmptyDataError:
            logging.info("Empty file")
            exchange_code = identify_exchange_code(csv_file)
            summary_data.append({
                'file': csv_file,
                'exchange_code': exchange_code,
                'total_rows': 0,
                'duplicates': 0,
                'duplicates_indices': "[]",
                'zero_entries': 0,
                'zero_entries_details': "{}",
                'total_outliers': 0,
                'outliers_details': "{}",
                'time_outliers': 0,
                'time_outliers_indices': "[]",
                'average_time_diff_ms': avg_time_diff,
                'total_issues': 0
            })
        except Exception as e:
            logging.error(f"Error processing file {csv_file}: {e}")

    summary_df = pd.DataFrame(summary_data)

    created_tar_files = []
    if not summary_df.empty and 'exchange_code' in summary_df.columns:
        unique_codes = summary_df['exchange_code'].dropna().unique()
        for code in unique_codes:
            exch_df = summary_df[summary_df['exchange_code'] == code].copy()
            tar_file_name = f'btc_data_quality_summary_{code}.tar.gz'
            split_and_tar_summary(exch_df, rows_per_file=rows_per_file, tar_file_name=tar_file_name)
            created_tar_files.append(tar_file_name)
    else:
        if not summary_df.empty:
            tar_file_name = 'btc_data_quality_summary.tar.gz'
            split_and_tar_summary(summary_df, rows_per_file=rows_per_file, tar_file_name=tar_file_name)
            created_tar_files.append(tar_file_name)

    if created_tar_files:
        master_tar_name = 'all_btc_data_quality_summaries.tar.gz'
        with tarfile.open(master_tar_name, 'w:gz') as master_tar:
            for tf in created_tar_files:
                master_tar.add(tf)
                logging.info(f"Added {tf} to {master_tar_name}")

        for tf in created_tar_files:
             os.remove(tf)

        logging.info(f"All exchange tar.gz files combined into {master_tar_name}")
