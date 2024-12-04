import pandas as pd
import os
import numpy as np
import json
import logging

logging.basicConfig(level=logging.INFO)

RELATIVE_CHANGE_THRESHOLD = 0.80
ABSOLUTE_CHANGE_THRESHOLD = 20000
LOOKBACK_WINDOW = 15

price_levels = range(1, 21)
bid_price_cols = [f'bid_prc{level}' for level in price_levels]
ask_price_cols = [f'ask_prc{level}' for level in price_levels]
all_price_cols = bid_price_cols + ask_price_cols
bid_volume_cols = [f'bid_vol{level}' for level in price_levels]
ask_volume_cols = [f'ask_vol{level}' for level in price_levels]
all_volume_cols = bid_volume_cols + ask_volume_cols
MAX_VALID_PRICE = 1e9

def is_valid_price(price, last_valid_price=None, relative_threshold=RELATIVE_CHANGE_THRESHOLD):
    try:
        price_float = float(price)
        if price_float < 0 or price_float < 10:
            logging.debug(f"Invalid price due to being negative or too small: {price_float}")
            return False
        if price_float > MAX_VALID_PRICE:
            logging.debug(f"Invalid price due to exceeding max valid price: {price_float}")
            return False
        if last_valid_price is not None:
            dynamic_threshold = last_valid_price * relative_threshold
            logging.debug(f"Last valid price: {last_valid_price}")
            logging.debug(f"Dynamic threshold: {dynamic_threshold}")
            if abs(price_float - last_valid_price) > dynamic_threshold:
                logging.debug(f"Price {price_float} is outlier (diff from last valid: {abs(price_float - last_valid_price)})")
                return False
        return True
    except (ValueError, TypeError) as e:
        logging.debug(f"Error processing price: {e}")
        return False

def interpolate_zeros(data, price_cols, volume_cols):
    for price_col, volume_col in zip(price_cols, volume_cols):
        if price_col in data.columns and volume_col in data.columns:
            data[price_col] = pd.to_numeric(data[price_col], errors='coerce')
            data[volume_col] = pd.to_numeric(data[volume_col], errors='coerce')
            zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
            if zero_condition.any():
                data.loc[zero_condition, price_col] = np.nan
                data.loc[zero_condition, volume_col] = np.nan
                data[price_col].interpolate(method='linear', inplace=True)
                data[volume_col].interpolate(method='linear', inplace=True)
                data[price_col].fillna(method='ffill', inplace=True)
                data[volume_col].fillna(method='ffill', inplace=True)
                data[price_col].fillna(method='bfill', inplace=True)
                data[volume_col].fillna(method='bfill', inplace=True)

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
            elif (current_price == 0) and (current_volume != 0):
                outlier_indices.append(i)
                continue
            if not is_valid_price(current_price, last_valid_price):
                outlier_indices.append(i)
                continue
            if last_valid_price is not None:
                relative_change = abs(current_price - last_valid_price) / last_valid_price
                absolute_change = abs(current_price - last_valid_price)
                is_relative_outlier = relative_change > relative_change_threshold
                is_absolute_outlier = absolute_change > absolute_change_threshold
                if is_relative_outlier or is_absolute_outlier:
                    logging.debug(
                        f"Price {current_price} at index {i} detected as an outlier (relative change: {relative_change}, absolute change: {absolute_change})")
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
            logging.debug(f"Skipping {price_col} and {volume_col} as they are not present in the data.")
            continue
        zero_condition = (data[price_col] == 0) & (data[volume_col] == 0)
        if zero_condition.any():
            zero_indices = data[zero_condition].index.tolist()
            zero_entries_details[f"{price_col} & {volume_col}"] = zero_indices
    total_zero_count = sum(len(indices) for indices in zero_entries_details.values())
    return total_zero_count, zero_entries_details

def check_duplicates(data):
    data = data[1::]
    duplicates = data.duplicated(keep=False)
    duplicate_count = duplicates.sum()
    duplicate_indices = data[duplicates].index.tolist()
    return duplicate_count, duplicate_indices

def detect_time_based_outliers(data, timestamp_col, threshold_ms=750):
    if timestamp_col not in data.columns:
        return 0, []
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], format='%H:%M:%S.%fZ', errors='coerce')
    data = data.sort_values(by=timestamp_col)
    data['time_diff_ms'] = data[timestamp_col].diff().dt.total_seconds() * 1000
    time_outliers = data[data['time_diff_ms'] >= threshold_ms]
    return len(time_outliers), time_outliers.index.tolist()

def run_quality_checks(directory_path, summary_file='btc_data_quality_summary.csv'):
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    summary_data = []
    for csv_file in csv_files:
        logging.info(f"working on file name: {csv_file}")
        if "DERIBIT" in csv_file:
            continue
        file_path = os.path.join(directory_path, csv_file)
        try:

            data = pd.read_csv(file_path)
            data.columns = data.columns.str.strip().str.lower()
            data.fillna(method='ffill', inplace=True)
            duplicates_count, duplicates_indices = check_duplicates(data)
            zero_count, zero_details = detect_zero_entries_multiple(data, all_price_cols, all_volume_cols)
            interpolate_zeros(data, all_price_cols, all_volume_cols)
            custom_outliers = custom_btc_outlier_detection(data, all_price_cols, all_volume_cols)
            time_outliers_count, time_outliers_indices = (0, [])
            if 'date' in data.columns:
                time_outliers_count, time_outliers_indices = detect_time_based_outliers(data, 'date')
            total_outliers = sum(len(indices) for indices in custom_outliers.values())
            summary_data.append({
                'file': csv_file,
                'total_rows': len(data),
                'duplicates': duplicates_count,
                'duplicates_indices': json.dumps(duplicates_indices),
                'zero_entries': zero_count,
                'zero_entries_details': json.dumps(zero_details),
                'total_outliers': total_outliers,
                'outliers_details': json.dumps(custom_outliers),
                'time_outliers': time_outliers_count,
                'time_outliers_indices': json.dumps(time_outliers_indices),
                'total_issues': duplicates_count + zero_count + total_outliers + time_outliers_count
            })
        except pd.errors.EmptyDataError:
            logging.info("Empty file")
            summary_data.append({
                'file': csv_file,
                'total_rows': "0",
                'duplicates': "0",
                'duplicates_indices': "0",
                'zero_entries': "0",
                'zero_entries_details': "0",
                'total_outliers': "0",
                'outliers_details': "0",
                'time_outliers': "0",
                'time_outliers_indices': "0",
                'total_issues': "0"
            }
            )
        except Exception as e:
            logging.error(f"Error processing file {csv_file}: {e}")



    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    print(f"Data quality summary saved to {summary_file}")


