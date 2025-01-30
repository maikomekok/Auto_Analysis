
import os
import sys
import argparse
import tarfile
import gzip
import shutil
import sqlite3
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import logging

# Setup logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("analyze_exchanges.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def setup_database(db_path):
    """
    Sets up the SQLite database and creates the necessary table if it doesn't exist.

    Parameters:
    - db_path (str): Path to the SQLite database file.

    Returns:
    - conn (sqlite3.Connection): SQLite database connection object.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                date DATE NOT NULL,
                exchange_code INTEGER NOT NULL,
                total_outliers INTEGER NOT NULL,
                average_time_outliers REAL NOT NULL
            );
        ''')
        conn.commit()
        logging.info(f"Database setup complete at '{db_path}'")
        return conn
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        sys.exit(1)


def decompress_tar_gz(filepath, extract_to):
    """
    Decompresses a .tar.gz or .tgz file into the specified directory.

    Parameters:
    - filepath (str): Path to the .tar.gz or .tgz file.
    - extract_to (str): Directory where files will be extracted.
    """
    try:
        with tarfile.open(filepath, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_to)
        logging.info(f"Extracted '{filepath}' to '{extract_to}'")
    except tarfile.TarError as e:
        logging.error(f"Failed to extract '{filepath}': {e}")
        raise


def parse_filename(filename):
    """
    Parses the filename to extract date and exchange code.
    Expected format: YYYY-MM-DD_<exchange>_data_quality_summary_<code>.tar.gz

    Parameters:
    - filename (str): Name of the tar.gz file.

    Returns:
    - date (str): Extracted date in YYYY-MM-DD format.
    - exchange_code (int): Extracted exchange code.
    """
    try:
        base = os.path.basename(filename)
        # Remove extension
        if base.endswith('.tar.gz'):
            base = base[:-7]
        elif base.endswith('.tgz'):
            base = base[:-4]
        elif base.endswith('.tar'):
            base = base[:-4]
        else:
            raise ValueError("Unsupported file extension")

        parts = base.split('_')
        date = parts[0]  # YYYY-MM-DD
        exchange_code = int(parts[-1])  # Assuming the last part is the exchange code
        return date, exchange_code
    except (IndexError, ValueError) as e:
        logging.error(f"Filename parsing error for '{filename}': {e}")
        raise


def summarize_csv(csv_path):
    """
    Summarizes the CSV summary file.
    Assumes the CSV has columns like 'outlier_count' and 'outlier_time'.

    Parameters:
    - csv_path (str): Path to the CSV file.

    Returns:
    - total_outliers (int): Total number of outliers.
    - average_time_outliers (float): Average time of outliers.
    """
    try:
        df = pd.read_csv(csv_path)
        # Verify required columns exist
        required_columns = ['outlier_count', 'outlier_time']
        for column in required_columns:
            if column not in df.columns:
                raise KeyError(f"Missing required column: '{column}'")

        total_outliers = int(df['outlier_count'].sum())
        average_time_outliers = float(df['outlier_time'].mean())

        return total_outliers, average_time_outliers
    except KeyError as e:
        logging.error(f"Missing expected column in CSV '{csv_path}': {e}")
        raise
    except ValueError as e:
        logging.error(f"Data type conversion error in CSV '{csv_path}': {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to summarize CSV '{csv_path}': {e}")
        raise


def analyze(exchange_dir, db_path):
    """
    Analyzes all .tar.gz files in the specified directory and updates the SQLite database.

    Parameters:
    - exchange_dir (str): Path to the directory containing .tar.gz files.
    - db_path (str): Path to the SQLite database file.
    """
    # Connect to the database
    conn = setup_database(db_path)
    cursor = conn.cursor()

    # List all .tar.gz and .tgz files
    tar_gz_files = [f for f in os.listdir(exchange_dir) if f.endswith(('.tar.gz', '.tgz'))]

    if not tar_gz_files:
        logging.warning(f"No .tar.gz or .tgz files found in '{exchange_dir}'")
        conn.close()
        return

    # Process each file with a progress bar
    for tar_file in tqdm(tar_gz_files, desc="Processing files"):
        tar_path = os.path.join(exchange_dir, tar_file)

        # Check if already processed
        cursor.execute("SELECT id FROM exchange_summaries WHERE file_name = ?", (tar_file,))
        if cursor.fetchone():
            logging.info(f"Skipping '{tar_file}' as it's already processed.")
            continue

        # Create a temporary extraction directory
        temp_extract_dir = os.path.join(exchange_dir, f"temp_{tar_file}")
        os.makedirs(temp_extract_dir, exist_ok=True)

        try:
            # Decompress the tar.gz file
            decompress_tar_gz(tar_path, temp_extract_dir)

            # Assuming there's only one CSV file inside the tar.gz
            csv_files = [f for f in os.listdir(temp_extract_dir) if f.endswith('.csv')]
            if not csv_files:
                logging.warning(f"No CSV files found in '{tar_file}'")
                shutil.rmtree(temp_extract_dir)
                continue
            elif len(csv_files) > 1:
                logging.warning(f"Multiple CSV files found in '{tar_file}'. Only the first will be processed.")

            csv_path = os.path.join(temp_extract_dir, csv_files[0])

            # Summarize the CSV
            total_outliers, average_time_outliers = summarize_csv(csv_path)

            # Parse the filename to get date and exchange_code
            date, exchange_code = parse_filename(tar_file)

            # Insert into the database
            cursor.execute('''
                INSERT INTO exchange_summaries (file_name, date, exchange_code, total_outliers, average_time_outliers)
                VALUES (?, ?, ?, ?, ?)
            ''', (tar_file, date, exchange_code, total_outliers, average_time_outliers))
            conn.commit()
            logging.info(
                f"Inserted summary for '{tar_file}': Date={date}, Exchange Code={exchange_code}, Total Outliers={total_outliers}, Avg Time Outliers={average_time_outliers}")

        except Exception as e:
            logging.error(f"Failed to process '{tar_file}': {e}")
            # Optionally, continue to next file or exit
            continue
        finally:
            # Cleanup: Delete the extracted files
            shutil.rmtree(temp_extract_dir)
            logging.info(f"Deleted temporary directory '{temp_extract_dir}'")

    # Close the database connection
    conn.close()
    logging.info("Database connection closed.")


def main():
    """
    Main function to parse arguments and initiate the analysis.
    """
    parser = argparse.ArgumentParser(
        description="Analyze Exchange Summary .tar.gz files and store summaries in SQLite DB.")
    parser.add_argument('-i', '--input', type=str, required=True,
                        help='Path to the input directory containing .tar.gz files.')
    parser.add_argument('-d', '--db', type=str, required=True, help='Path to the SQLite database file.')

    args = parser.parse_args()

    input_dir = args.input
    db_path = args.db

    # Validate input directory
    if not os.path.isdir(input_dir):
        logging.error(f"Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    analyze(exchange_dir=input_dir, db_path=db_path)


if __name__ == "__main__":
    main()
