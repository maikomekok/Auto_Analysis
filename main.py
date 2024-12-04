import os
import sys
import getopt
# from autoanalysis import Autoanalysis, autoanalysis_of_graphs
from data_quality_checking import run_quality_checks


def main(input_path, mode):
    # input_path = 'C:/Users/admin/Desktop/data_small'  # Default directory of CSV files
    summary_path = 'C:/Users/admin/Desktop/summaries'  # Default directory of summaries

    # mode = 'quality_check'  # Default mode

    # try:
    #     # Parse command-line arguments
    #     opts, args = getopt.getopt(argv, "i:s:m:h", ["input=", "summary=", "mode=", "help"])
    # except getopt.GetoptError:
    #     print("Invalid arguments. Use --help for usage instructions.")
    #     sys.exit(2)
    #
    # # Process the options
    # for opt, arg in opts:
    #     if opt in ("-h", "--help"):
    #         print_help()
    #         sys.exit()
    #     elif opt in ("-i", "--input"):
    #         input_path = arg
    #     elif opt in ("-s", "--summary"):
    #         summary_path = arg
    #     elif opt in ("-m", "--mode"):
    #         mode = arg

    # Ensure the summary directory exists
    os.makedirs(summary_path, exist_ok=True)


    # Execute based on the selected mode

    if mode == "analyze":
        print(f"Running Autoanalysis on data in {input_path}...")
        Autoanalysis(input_path)
    elif mode == "quality_check":
        print(f"Running Data Quality Check on data in {input_path}...")
        run_quality_checks(input_path)
    elif mode == "graphs":
        print("Generating graphs...")
        autoanalysis_of_graphs()
    else:
        print(f"Unknown mode: {mode}. Use --help for usage instructions.")


def print_help():
    """  Prints the usage instructions. """
    print("""
    Usage: main.py [options]

    Options:
    -i, --input     Path to the input directory with CSV files (default: C:/Users/admin/Desktop/data_small)
    -s, --summary   Path to the directory for saving summary files (default: C:/Users/admin/Desktop/summaries)
    -m, --mode      Mode of operation: 'analyze', 'quality_check', or 'graphs' (default: analyze)
    -h, --help      Display this help message
    """)
    print()


if __name__ == '__main__':
    # main(sys.argv[1:])
    try:
        argv = sys.argv[1:]
        opts, args = getopt.getopt(argv, "i:m:")
    except getopt.GetoptError:
        print("No arguments provided.  Exiting script")
        sys.exit(2)

    print(opts)
    for opt, arg in opts:
        if opt in ["-i"]:
            input_path = arg
        if opt in ["-m"]:
            mode = arg

main(input_path, mode)



