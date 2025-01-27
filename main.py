import os
import sys
import argparse
from datetime import datetime
from data_quality_checking import process_daily_data
from analyze_exchanges import analyze
import logging

def main(input_path, summary_path, mode, db_path):
    os.makedirs(summary_path, exist_ok=True)
    daily_folder = os.path.join(summary_path, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(daily_folder, exist_ok=True)

    if mode == "quality_check":
        print(f"Running Data Quality Check on data in {input_path}...")
        process_daily_data(input_path, daily_folder)
    elif mode == "analyze_exchanges":
        if not db_path:
            print("Error: --db is required when mode is 'analyze_exchanges'. Use --help for usage instructions.")
            sys.exit(1)
        print(f"Running Exchange Analysis...")
        temp_extract_dir = os.path.join(summary_path, 'temp_extracted')
        analyze(exchange_dir=input_path, temp_extract_dir=temp_extract_dir, db_path=db_path)
    else:
        print(f"Unknown mode: {mode}. Use --help for usage instructions.")
        sys.exit(1)

def print_help():
    print("""
    Usage: main.py [options]

    Options:
    -i, --input     Path to the input directory containing compressed exchange files.
    -s, --summary   Path to the directory for saving summary files (default: ./summaries)
    -d, --db        Path to the SQLite database file (required for 'analyze_exchanges' mode)
    -m, --mode      Mode of operation: 'quality_check' or 'analyze_exchanges' (default: quality_check)
    -h, --help      Display this help message
    """)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Main script to run data quality checks or analyze exchanges.")

    parser.add_argument('-i', '--input', type=str, default='.', help='Path to the input directory containing compressed exchange files.')
    parser.add_argument('-s', '--summary', type=str, default='./summaries', help='Path to the directory for saving summary files.')
    parser.add_argument('-m', '--mode', type=str, choices=['quality_check', 'analyze_exchanges'], default='quality_check', help="Mode of operation: 'quality_check' or 'analyze_exchanges'.")
    parser.add_argument('-d', '--db', type=str, help='Path to the SQLite database file. Required for "analyze_exchanges" mode.')

    args = parser.parse_args()

    input_path = args.input
    summary_path = args.summary
    mode = args.mode
    db_path = args.db

    if not os.path.isdir(input_path):
        print(f"Input directory does not exist: {input_path}")
        sys.exit(1)

    if mode == 'analyze_exchanges' and not db_path:
        print("Error: --db is required when mode is 'analyze_exchanges'. Use --help for usage instructions.")
        sys.exit(1)

    if mode == 'analyze_exchanges' and not db_path:
        db_path = os.path.join(summary_path, 'exchanges.db')

    main(input_path, summary_path, mode, db_path)
