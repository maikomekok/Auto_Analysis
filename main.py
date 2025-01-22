import os
import sys
import getopt
from datetime import datetime
from data_quality_checking import process_daily_data
from analyze_exchanges import analyze


def main(input_path, summary_path, mode):
    os.makedirs(summary_path, exist_ok=True)

    daily_folder = os.path.join(summary_path, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(daily_folder, exist_ok=True)

    if mode == "quality_check":
        print(f"Running Data Quality Check on data in {input_path}...")
        process_daily_data(input_path, daily_folder)
    elif mode == "analyze_exchanges":
        analyze(db_path=".")
    else:
        print(f"Unknown mode: {mode}. Use --help for usage instructions.")

def print_help():
    print("""
    Usage: main.py [options]

    Options:
    -i, --input     Path to the input directory with .tar.gz files
    -s, --summary   Path to the directory for saving summary files (default: ./summaries)
    -m, --mode      Mode of operation: 'quality_check' (default: quality_check)
    -h, --help      Display this help message
    """)

if __name__ == '__main__':
    input_path = '.'
    summary_path = './summaries'
    mode = 'quality_check'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:s:m:h", ["input=", "summary=", "mode=", "help"])
    except getopt.GetoptError:
        print("Invalid arguments. Use --help for usage instructions.")
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit()
        elif opt in ("-i", "--input"):
            input_path = arg
        elif opt in ("-s", "--summary"):
            summary_path = arg
        elif opt in ("-m", "--mode"):
            mode = arg

    main(input_path, summary_path, mode)
