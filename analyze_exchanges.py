import os
import sys
import argparse
import tarfile
import shutil
import sqlite3
import pandas as pd
from tqdm import tqdm
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("analyze_exchanges.log"), logging.StreamHandler(sys.stdout)],
)


def setup_database(db_path):
    """Sets up the SQLite database and ensures the necessary table exists."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE NOT NULL,
                date DATE NOT NULL,
                exchange_code INTEGER NOT NULL,
                total_rows INTEGER NOT NULL,
                total_outliers INTEGER NOT NULL,
                average_time_outliers REAL NOT NULL,
                empty_files_count INTEGER DEFAULT 0,
                duplicate_entries INTEGER DEFAULT 0,
                zero_value_entries INTEGER DEFAULT 0,
                total_issues INTEGER DEFAULT 0
            );
        """
        )
        conn.commit()
        logging.info(f"Database setup complete at '{db_path}'")
        return conn
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        sys.exit(1)


def decompress_tar_gz(filepath, extract_to):
    """Extracts a .tar.gz archive to the specified directory."""
    try:
        with tarfile.open(filepath, "r:gz") as tar_ref:
            tar_ref.extractall(extract_to)
        logging.info(f"Extracted '{filepath}' to '{extract_to}'")
    except tarfile.TarError as e:
        logging.error(f"Failed to extract '{filepath}': {e}")
        raise


def parse_filename(filename):
    """Parses the filename to extract the date and exchange code."""
    try:
        base = os.path.basename(filename)
        base = base.replace(".tar.gz", "").replace(".tgz", "").replace(".tar", "")

        parts = base.split("_")
        date = parts[0]
        exchange_code = int(parts[-1])
        return date, exchange_code
    except (IndexError, ValueError) as e:
        logging.error(f"Filename parsing error for '{filename}': {e}")
        raise


def summarize_csv(csv_path):
    """Analyzes a CSV file and extracts summary statistics."""
    try:
        df = pd.read_csv(csv_path)

        # Detect empty file
        if df.empty:
            logging.warning(f"CSV '{csv_path}' is empty.")
            return 0, 0, 0.0, 1, 0, 0, 1  # total_rows = 0, empty_files_count = 1

        required_columns = ["custom_price_outliers", "avg_time_diff_ms", "zero_entries",]
        for column in required_columns:
            if column not in df.columns:
                raise KeyError(f"Missing required column: '{column}'")

        total_rows = df["total_rows"]
        total_outliers = int(df["custom_price_outliers"].sum())
        average_time_outliers = float(df["avg_time_diff_ms"].mean())

        empty_files_count = 0
        duplicate_entries = df["duplicates"].sum()
        zero_value_entries = df["zero_entries"].sum()
        total_issues = df["total_issues"]

        return total_rows, total_outliers, average_time_outliers, empty_files_count, duplicate_entries, zero_value_entries, total_issues

    except Exception as e:
        logging.error(f"Failed to summarize CSV '{csv_path}': {e}")
        raise


def analyze(exchange_dir, db_path):
    """Processes all .tar.gz files in the directory, extracts CSVs, and stores summaries in the database."""
    conn = setup_database(db_path)
    cursor = conn.cursor()

    tar_gz_files = [f for f in os.listdir(exchange_dir) if f.endswith((".tar.gz", ".tgz"))]

    if not tar_gz_files:
        logging.warning(f"No .tar.gz or .tgz files found in '{exchange_dir}'")
        conn.close()
        return

    for tar_file in tqdm(tar_gz_files, desc="Processing files"):
        tar_path = os.path.join(exchange_dir, tar_file)

        cursor.execute("SELECT id FROM exchange_summaries WHERE file_name = ?", (tar_file,))
        if cursor.fetchone():
            logging.info(f"Skipping '{tar_file}' as it's already processed.")
            continue

        temp_extract_dir = os.path.join(exchange_dir, f"temp_{tar_file}")
        os.makedirs(temp_extract_dir, exist_ok=True)

        try:
            decompress_tar_gz(tar_path, temp_extract_dir)

            csv_files = [f for f in os.listdir(temp_extract_dir) if f.endswith(".csv")]
            if not csv_files:
                logging.warning(f"No CSV files found in '{tar_file}'")
                continue
            elif len(csv_files) > 1:
                logging.warning(f"Multiple CSV files found in '{tar_file}'. Only the first will be processed.")

            csv_path = os.path.join(temp_extract_dir, csv_files[0])

            date, exchange_code = parse_filename(tar_file)

            (
                total_rows,
                total_outliers,
                average_time_outliers,
                empty_files_count,
                duplicate_entries,
                zero_value_entries,
                total_issues,
            ) = summarize_csv(csv_path)

            cursor.execute(
                """
                INSERT INTO exchange_summaries 
                (file_name, date, exchange_code, total_rows, total_outliers, average_time_outliers, 
                empty_files_count, duplicate_entries, zero_value_entries, total_issues)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    tar_file,
                    date,
                    exchange_code,
                    total_rows,
                    total_outliers,
                    average_time_outliers,
                    empty_files_count,
                    duplicate_entries,
                    zero_value_entries,
                    total_issues,
                ),
            )

            conn.commit()
            logging.info(
                f"Inserted summary for '{tar_file}': Date={date}, Exchange Code={exchange_code}, "
                f"Total Rows={total_rows}, Total Outliers={total_outliers}, "
                f"Avg Time Outliers={average_time_outliers}, Empty Files={empty_files_count}, "
                f"Duplicates={duplicate_entries}, Zero Entries={zero_value_entries}, "
                f"Total Issues={total_issues}"
            )

        except Exception as e:
            logging.error(f"Failed to process '{tar_file}': {e}")
            continue
        finally:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            logging.info(f"Deleted temporary directory '{temp_extract_dir}'")

    conn.close()
    logging.info("Database connection closed.")


def main():
    """Main function to parse arguments and start processing."""
    parser = argparse.ArgumentParser(description="Analyze Exchange Summary .tar.gz files and store summaries in SQLite DB.")
    parser.add_argument("-i", "--input", type=str, required=True, help="Path to the input directory containing .tar.gz files.")
    parser.add_argument("-d", "--db", type=str, required=True, help="Path to the SQLite database file.")

    args = parser.parse_args()

    input_dir = args.input
    db_path = args.db

    if not os.path.isdir(input_dir):
        logging.error(f"Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    analyze(exchange_dir=input_dir, db_path=db_path)


if __name__ == "__main__":
    main()
