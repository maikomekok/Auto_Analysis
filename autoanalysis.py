import os
import sys
import getopt
import glob
import pathlib
import tarfile
import warnings
import statistics
from datetime import datetime
from os.path import isfile

warnings.simplefilter(action='ignore', category=FutureWarning)
import numpy as np
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
from tqdm import tqdm
from os.path import isfile, join
# from datetime import date
# from apscheduler.scheduler import Scheduler
# from apscheduler.schedulers.blocking import BlockingScheduler


# from autosim import generate_daily_dataset


def daily_autoanalysis(date_end=None):
    # daily function to run the autoanalysis pipeline -- generates daily dataset, runs autoanalysis
    # the schedule function is currently running, which runs this 'daily' every day
    # for now you can safely ignore these and start with the base 'autoanalysis' func...
    data_path = 'C:/Users/admin/Desktop/data_small/'
    summary_path = 'C:/Users/admin/Desktop/data_small'
    coin = 'btc'
    date_delta = 1

    date_end = datetime.now()
    # remove all files in summary_path
    files = [f for f in os.listdir(data_path) if isfile(os.path.join(data_path, f))]
    for f in files:
        os.remove(data_path + f)

    delta_out_files = [f for f in os.listdir(data_path + 'delta_out/') if
                       isfile(os.path.join(data_path + 'delta_out/', f))]
    for f in delta_out_files:
        os.remove(data_path + 'delta_out/' + f)
    # generates a daily dataset by grabbing it from the server and unpacking it -- youll use at some point, but can be replaced for now
    generate_daily_dataset(data_path, date_end, date_delta, coin, file_type='raw')
    Autoanalysis(data_path)


def generate_daily_dataset(a, b, c, d):
    pass


def autoanalysis_of_graphs():

    data_path = 'C:/Users/admin/Desktop/data_small/'
    summary_path = 'C:/Users/admin/Desktop/data_small/summaries/'
    os.makedirs(summary_path, exist_ok=True)  # Ensure summary directory exists

    # List all CSV files in the data directory
    csv_files = [f for f in os.listdir(data_path) if f.endswith('.csv')]

    # Loop through each CSV file and analyze it
    for csv_file in csv_files:
        file_path = os.path.join(data_path, csv_file)
        print(f"Analyzing {csv_file}")

        try:
            # Load the CSV data
            data = pd.read_csv(file_path)

            if data.empty:
                print(f"{csv_file} is empty or has no readable data.")
                continue

            # Perform some basic analysis, like summary statistics
            summary = data.describe()
            print(f"Summary statistics for {csv_file}:\n", summary)

            # Save the summary to a new CSV file in the summary folder
            summary_file = os.path.join(summary_path, f"summary_{csv_file}")
            summary.to_csv(summary_file, index=True)

            if len(data.columns) >= 2:
                data.plot(x=data.columns[2], y=data.columns[3], kind='line')
                plt.title(f"{csv_file} Data Plot")
                plt.savefig(os.path.join(summary_path, f"plot_{csv_file}.png"))
                plt.clf()  # Clear figure for the next plot

        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    print("Autoanalysis completed.")






def Autoanalysis(input_path):
    # Create separate directories for different types of summaries
    summary_dir = 'C:/Users/admin/Desktop/summaries'
    composite_dir = 'C:/Users/admin/Desktop/summary_composite'


    # Ensure the summary and composite directories exist
    os.makedirs(summary_dir, exist_ok=True)
    os.makedirs(composite_dir, exist_ok=True)

    # Retrieve the files in the input_path
    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f))]

    # Run delta_raw_data, summarize_join_exchanges, and single_file_summary

    delta_raw_data(input_path)
    date_str = summarize_join_exchanges(input_path)
    results, date_str = single_file_summary(input_path)

    # Replace '-' with '_' in date_str for consistency in file names
    date_str = date_str.replace('-', '_')

    # Process and save each exchange's summary
    for ex_num in results:
        # Print the lengths of each array to identify any issues
        for key, value in results[ex_num].items():
            print(f"{key}: {len(value)}")

        # Ensure all arrays have the same length
        max_length = max(len(v) for v in results[ex_num].values())
        for key in results[ex_num]:
            if len(results[ex_num][key]) < max_length:
                results[ex_num][key] += [np.nan] * (max_length - len(results[ex_num][key]))

        # Create the DataFrame from results
        df_ex = pd.DataFrame(results[ex_num])
        print(f"Writing summary file for exchange ::: {ex_num}")

        # Correct the file path to save in summaries folder
        try:
            summary_file_path = os.path.join(summary_dir, f'summary_{ex_num}.csv')
            print(f"Saving summary file for exchange {ex_num} to {summary_file_path}")
            df_ex.to_csv(summary_file_path, index=False)
            print(f"File for exchange {ex_num} saved successfully.")
        except Exception as e:
            print(f"Error saving file for exchange {ex_num}: {e}")

    # Save the composite summary (if applicable)
    if 'composite' in results:
        try:
            composite_file_path = os.path.join(composite_dir, 'summary_composite.csv')
            print(f"Saving composite summary to {composite_file_path}")
            df_composite = pd.DataFrame(results['composite'])
            df_composite.to_csv(composite_file_path, index=False)
            print(f"Composite summary saved successfully.")
        except Exception as e:
            print(f"Error saving composite summary: {e}")

# This function is not working
def schedule_autoanalysis():
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_autoanalysis, "interval", days=1)

    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


def expand_tar_gz(file_path, target_path):
    # Open the tar.gz file
    with tarfile.open(file_path, "r:gz") as tar:
        # Extract the contents to the target path
        tar.extractall(path=target_path)
        print(f"{file_path} has been successfully expanded to {target_path}.")


def clear_directory(path):
    files = glob.glob(str(path) + '/*')
    for f in files:
        os.remove(f)


def export_data(df, export_path):
    try:
        df[['date', 'bid_flow', 'ask_flow', 'net_flow']].to_csv(export_path, index=False)
    except:
        pass


def delta_raw_data(data_path):
    files = [f for f in os.listdir(data_path) if isfile(os.path.join(data_path, f))]

    # create new directory
    out_path = pathlib.Path(data_path + '/delta_out')
    out_path.mkdir(parents=True, exist_ok=True)

    # unpack .tar.gz files
    print('Calculating cumulative delta...')
    for f in tqdm(files):
        if 'DERIBIT' in f:
            continue
        if 'summary' in f:
            continue
        """ check if outfile exists"""
        if os.path.isfile(str(out_path) + '/' + f.replace('raw', 'cum_delta')):
            continue
        data = calculate_cumulative_delta(str(data_path) + '/' + f)
        export_data(data, str(out_path) + '/' + f.replace('raw', 'cum_delta'))


def plot_flows(simdata_path, delta_path):
    # designed to plot 'cumulative volume delta' --
    # not currently used + can be ignored at first, but might be interesting to play with
    delta_files = [f for f in os.listdir(delta_path) if isfile(os.path.join(delta_path, f))]
    simdata_files = [f for f in os.listdir(simdata_path) if isfile(os.path.join(simdata_path, f))]
    exchange_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17, 18, 22, 23, 24]

    df_all = pd.DataFrame()
    i = 0
    print('Processing ' + str(len(delta_files)) + ' delta files...')
    for delta_file in tqdm(sorted(delta_files)):
        if i > 1:
            break
        i += 1
        try:
            delta_file_root = delta_file[:26]
            delta_data = pd.read_csv(delta_path + '/' + delta_file)
            simdata_file = [f for f in simdata_files if delta_file_root in f][0]
            simdata_data = pd.read_csv(simdata_path + '/' + simdata_file)

            """ drop columns in simdata_data if not date_unified or ex_2_index"""
            simdata_data = simdata_data[['date_unified', 'ex_2_index']]

            """ merge dataframes """
            df = pd.merge(delta_data, simdata_data, on='date_unified', how='outer')
            """ fill empty values with later previous value"""
            df = df.replace(r'^\s*$', np.nan, regex=True)
            df = df.fillna(method='ffill')
            """ concat dataframes vertically """
            df_all = pd.concat([df_all, df], ignore_index=True)
        except:
            pass

    ask_cols = [c for c in df_all.columns if 'ask_flow' in c]
    bid_cols = [c for c in df_all.columns if 'bid_flow' in c]
    net_cols = [c for c in df_all.columns if 'net_flow' in c]

    df_all['ask_flow'] = df_all[ask_cols].sum(axis=1)
    df_all['bid_flow'] = df_all[bid_cols].sum(axis=1)
    df_all['total_flow'] = df_all['ask_flow', 'bid_flow'].abs().sum(axis=1)
    # df_all['net_flow'] = df_all[net_cols].sum(axis=1)
    """ caclulate net_flow as sum of absolute values of net_cols"""
    df_all['net_flow'] = df_all[net_cols].abs().sum(axis=1)

    """ drop rows with net_flow = 0 """
    df_all = df_all[df_all['net_flow'] != 0]

    print('Plotting ' + str(len(exchange_numbers)) + ' exchanges...')
    for ex_num in exchange_numbers:
        print('Plotting exchange ' + str(ex_num) + '...')
        df_all['ask_flow_percent_' + str(ex_num)] = df_all['ask_flow_' + str(ex_num)] / df_all['ask_flow']
        df_all['bid_flow_percent_' + str(ex_num)] = df_all['bid_flow_' + str(ex_num)] / df_all['bid_flow']
        df_all['net_flow_percent_' + str(ex_num)] = df_all['net_flow_' + str(ex_num)] / df_all['net_flow']

        """ plot ex_2_index as a line and net_flow as a bar on a secondary axis"""
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax2 = ax1.twinx()
        ax1.plot(df_all['date_unified'], df_all['ex_2_index'], color='blue')
        ax2.bar(df_all['date_unified'], df_all['net_flow_' + str(ex_num)], color='red')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('ex_2_index', color='blue')
        ax2.set_ylabel('net_flow_' + str(ex_num), color='red')
        plt.title('ex_2_index and net_flow_' + str(ex_num) + ' over time')
        plt.savefig(delta_path + '/' + 'net_flow_' + str(ex_num) + '.png')

    df_all.to_csv(delta_path + '/all_cum_delta_joined.csv', index=False)


def summarize_join_exchanges(input_path):
    # first layer of the 'main' summary function -- calls various calculation function on the raw exchange data
    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f))]
    date_roots = sorted(list(set([f[:26] for f in files])))
    last_date = files[-1][:10].replace('-', '_')

    print('Calculating exchange summary data...')
    for root in tqdm(date_roots):
        df_dict = {}
        date_files = [f for f in files if root in f]
        for date_file in date_files:
            if 'summary' in date_file:
                # print('Skipping ' + date_file + '...')
                continue
            if os.path.isfile(input_path + 'summary_' + date_file):
                # print('Skipping ' + date_file + '...')
                continue
            if 'DERIBIT' in date_file:
                continue
            try:
                df_dict[date_file] = pd.read_csv(input_path + '/' + date_file)
            except:
                print('Error reading file: ' + date_file)
                continue
        df_dict = calculate_new_order_counts(df_dict)
        df_dict = calculate_market_percentage_depth(df_dict)
        df_dict = calculate_simple_spread(df_dict)
        df_dict = calculate_exchange_index_price(df_dict)

        for df in df_dict:
            for i in range(1, 21):
                df_dict[df] = df_dict[df].drop(['bid_prc' + str(i), 'ask_prc' + str(i), \
                                                'bid_vol' + str(i), 'ask_vol' + str(i)], axis=1)
            df_dict[df].to_csv(input_path + '/summary_' + df, index=False)

    return last_date


def calculate_cumulative_delta(input_path):
    # calculates 'cumulative volume delta' from orderbook --
    # the amount of order ask/bidflow at each time step... very useful metric
    try:
        df = pd.read_csv(input_path)
    except:
        print('Error reading file: ' + input_path)
        return None

    bid_prc_dict = defaultdict(lambda: [])
    bid_vol_dict = defaultdict(lambda: [])
    ask_prc_dict = defaultdict(lambda: [])
    ask_vol_dict = defaultdict(lambda: [])

    for i in range(1, 21):
        bid_prc_dict[i] = df['bid_prc' + str(i)].tolist()
        bid_vol_dict[i] = df['bid_vol' + str(i)].tolist()
        ask_prc_dict[i] = df['ask_prc' + str(i)].tolist()
        ask_vol_dict[i] = df['ask_vol' + str(i)].tolist()

    for n in range(0, len(df)):
        current_bid_prices = [bid_prc_dict[i][n] for i in range(1, 21)]
        current_bid_volumes = [bid_vol_dict[i][n] for i in range(1, 21)]
        current_ask_prices = [ask_prc_dict[i][n] for i in range(1, 21)]
        current_ask_volumes = [ask_vol_dict[i][n] for i in range(1, 21)]

        flow_ask = 0
        flow_bid = 0
        current_bids = dict(zip(current_bid_prices, current_bid_volumes))
        current_asks = dict(zip(current_ask_prices, current_ask_volumes))

        if n == 0:
            previous_bids = current_bids
            previous_asks = current_asks
        else:
            max_prev_bid = max(previous_bids.keys())
            min_prev_bid = min(previous_bids.keys())
            max_prev_ask = max(previous_asks.keys())
            min_prev_ask = min(previous_asks.keys())

            for bid in previous_bids:
                if bid in current_bids:
                    flow_bid += current_bids[bid] - previous_bids[bid]
                elif min_prev_bid < bid < max_prev_bid:
                    flow_bid -= previous_bids[bid]
            for ask in previous_asks:
                if ask in current_asks:
                    flow_ask += current_asks[ask] - previous_asks[ask]

        df.at[n, 'bid_flow'] = flow_bid
        df.at[n, 'ask_flow'] = flow_ask
        df.at[n, 'net_flow'] = flow_bid - flow_ask

        previous_bids = current_bids
        previous_asks = current_asks

    return df


def calculate_true_depth_price(ask_price_vals, bid_price_vals, ask_size_vals, bid_size_vals, len_df, MIN_COIN_AMOUNT):
    # calculates the midprice at a certain volume 'depth' within the orderbook
    # (as opposed to / generally better than the simple midprice from the best bid & ask)
    depth_prices = []

    for i in range(0, len_df):
        if bid_size_vals[1][i] > MIN_COIN_AMOUNT:
            bid_depth = bid_price_vals[1][i] * MIN_COIN_AMOUNT
        elif bid_size_vals[1][i] + bid_size_vals[2][i] > MIN_COIN_AMOUNT:
            bid_depth = bid_price_vals[1][i] * bid_size_vals[1][i] + bid_price_vals[2][i] * (
                        MIN_COIN_AMOUNT - bid_size_vals[1][i])
        elif bid_size_vals[1][i] + bid_size_vals[2][i] + bid_size_vals[3][i] > MIN_COIN_AMOUNT:
            bid_depth = bid_price_vals[1][i] * bid_size_vals[1][i] + bid_price_vals[2][i] * bid_size_vals[2][i] + \
                        bid_price_vals[3][i] * \
                        (MIN_COIN_AMOUNT - bid_size_vals[1][i] - bid_size_vals[2][i])
        elif bid_size_vals[1][i] + bid_size_vals[2][i] + bid_size_vals[3][i] + bid_size_vals[4][i] > MIN_COIN_AMOUNT:
            bid_depth = bid_price_vals[1][i] * bid_size_vals[1][i] + bid_price_vals[2][i] * bid_size_vals[2][i] + \
                        bid_price_vals[3][i] * bid_size_vals[3][i] + bid_price_vals[4][i] * \
                        (MIN_COIN_AMOUNT - bid_size_vals[1][i] - bid_size_vals[2][i] - bid_size_vals[3][i])
        else:
            bid_depth = bid_price_vals[1][i] * bid_size_vals[1][i] + bid_price_vals[2][i] * bid_size_vals[2][i] + \
                        bid_price_vals[3][i] * bid_size_vals[3][i] + bid_price_vals[4][i] * \
                        bid_size_vals[4][i] + bid_price_vals[5][i] * (
                                    MIN_COIN_AMOUNT - bid_size_vals[1][i] - bid_size_vals[2][i] - bid_size_vals[3][i] -
                                    bid_size_vals[4][i])
        if ask_size_vals[1][i] > MIN_COIN_AMOUNT:
            ask_depth = ask_price_vals[1][i] * MIN_COIN_AMOUNT
        elif ask_size_vals[1][i] + ask_size_vals[2][i] > MIN_COIN_AMOUNT:
            ask_depth = ask_price_vals[1][i] * ask_size_vals[1][i] + ask_price_vals[2][i] * (
                        MIN_COIN_AMOUNT - ask_size_vals[1][i])
        elif ask_size_vals[1][i] + ask_size_vals[2][i] + ask_size_vals[3][i] > MIN_COIN_AMOUNT:
            ask_depth = ask_price_vals[1][i] * ask_size_vals[1][i] + ask_price_vals[2][i] * ask_size_vals[2][i] + \
                        ask_price_vals[3][i] * \
                        (MIN_COIN_AMOUNT - ask_size_vals[1][i] - ask_size_vals[2][i])
        elif ask_size_vals[1][i] + ask_size_vals[2][i] + ask_size_vals[3][i] + ask_size_vals[4][i] > MIN_COIN_AMOUNT:
            ask_depth = ask_price_vals[1][i] * ask_size_vals[1][i] + ask_price_vals[2][i] * ask_size_vals[2][i] + \
                        ask_price_vals[3][i] * ask_size_vals[3][i] + ask_price_vals[4][i] * \
                        (MIN_COIN_AMOUNT - ask_size_vals[1][i] - ask_size_vals[2][i] - ask_size_vals[3][i])
        else:
            ask_depth = ask_price_vals[1][i] * ask_size_vals[1][i] + ask_price_vals[2][i] * ask_size_vals[2][i] + \
                        ask_price_vals[3][i] * ask_size_vals[3][i] + ask_price_vals[4][i] * \
                        ask_size_vals[4][i] + ask_price_vals[5][i] * (
                                    MIN_COIN_AMOUNT - ask_size_vals[1][i] - ask_size_vals[2][i] - ask_size_vals[3][i] -
                                    ask_size_vals[4][i])
        depth_prices.append((bid_depth + ask_depth) / (2 * MIN_COIN_AMOUNT))

    return depth_prices


def calculate_exchange_index_price(df_dict):
    # calculates an 'index' price for each exchange.  also pretty inefficient
    bid_price_vals = defaultdict(lambda: [])
    ask_price_vals = defaultdict(lambda: [])
    bid_size_vals = defaultdict(lambda: [])
    ask_size_vals = defaultdict(lambda: [])
    for df in df_dict:
        for i in range(1, 6):
            bid_size_vals[i] = df_dict[df]['bid_vol' + str(i)].values
            ask_size_vals[i] = df_dict[df]['ask_vol' + str(i)].values
            bid_price_vals[i] = df_dict[df]['bid_prc' + str(i)].values
            ask_price_vals[i] = df_dict[df]['ask_prc' + str(i)].values

        data_count = len(df_dict[df])
        depth_prices = calculate_true_depth_price(ask_price_vals, bid_price_vals, ask_size_vals, bid_size_vals,
                                                  data_count, 0.175)
        depth_prices = [round(p, 3) for p in depth_prices]
        df_dict[df]['index_price'] = depth_prices

    return df_dict


def calculate_simple_spread(df_dict):
    for df in df_dict:
        df_dict[df]['simple_spread'] = df_dict[df]['ask_prc1'] - df_dict[df]['bid_prc1']
    return df_dict


def calculate_market_percentage_depth(df_dict):
    # calculates the order volume within a certain percentage of the midprice
    # could *definitely* be refactored to be more efficient``
    percentages = [0.000005, 0.00001, 0.000025, 0.00005, 0.0001]
    bid_prc_vals = defaultdict(lambda: [])
    ask_prc_vals = defaultdict(lambda: [])
    bid_vol_vals = defaultdict(lambda: [])
    ask_vol_vals = defaultdict(lambda: [])
    # print('Calculating market percentage depth...')

    for df in df_dict:
        bid_vol_total_vals = []
        ask_vol_total_vals = []
        bid_depth_vals = defaultdict(lambda: [])
        ask_depth_vals = defaultdict(lambda: [])
        for i in range(1, 21):
            bid_vol_vals[i] = df_dict[df]['bid_vol' + str(i)].values
            ask_vol_vals[i] = df_dict[df]['ask_vol' + str(i)].values
            bid_prc_vals[i] = df_dict[df]['bid_prc' + str(i)].values
            ask_prc_vals[i] = df_dict[df]['ask_prc' + str(i)].values

        for k in range(0, len(df_dict[df])):
            bid_vol_total_vals.append(sum([bid_vol_vals[i][k] for i in range(1, 21)]))
            ask_vol_total_vals.append(sum([ask_vol_vals[i][k] for i in range(1, 21)]))

            midprice_k = (bid_prc_vals[1][k] + ask_prc_vals[1][k]) / 2
            for p in percentages:
                percent_midprice = midprice_k * p
                bid_done = False
                ask_done = False
                bid_vol_sum = 0
                ask_vol_sum = 0
                for i in range(1, 21):
                    bid_vol_sum += bid_vol_vals[i][k]
                    ask_vol_sum += ask_vol_vals[i][k]
                    if bid_prc_vals[i][k] <= midprice_k - percent_midprice and not bid_done:
                        bid_depth_vals[p].append(round(bid_vol_sum, 3))
                        bid_done = True
                    if ask_prc_vals[i][k] >= midprice_k + percent_midprice and not ask_done:
                        ask_depth_vals[p].append(round(ask_vol_sum, 3))
                        ask_done = True
                    if bid_done and ask_done:
                        break

                if not bid_done:
                    bid_depth_vals[p].append(bid_vol_sum)
                if not ask_done:
                    ask_depth_vals[p].append(ask_vol_sum)

        bid_vol_total_vals = [round(v, 3) for v in bid_vol_total_vals]
        ask_vol_total_vals = [round(v, 3) for v in ask_vol_total_vals]

        df_dict[df]['bid_vol_total'] = bid_vol_total_vals
        df_dict[df]['ask_vol_total'] = ask_vol_total_vals
        for p in percentages:
            df_dict[df]['bid_depth_' + str(p)] = bid_depth_vals[p]
            df_dict[df]['ask_depth_' + str(p)] = ask_depth_vals[p]

    return df_dict


def calculate_new_order_counts(df_dict):
    # calculates the number of 'new' orders in the orderbook at each time step
    # ...not even sure how useful this is, just an idea for a metric!
    for df in df_dict:
        previous_orderbook = []
        ask_prc_vals = defaultdict(lambda: [])
        bid_prc_vals = defaultdict(lambda: [])
        ask_vol_vals = defaultdict(lambda: [])
        bid_vol_vals = defaultdict(lambda: [])

        for i in range(1, 21):
            ask_prc_vals[i] = df_dict[df]['ask_prc' + str(i)].values
            bid_prc_vals[i] = df_dict[df]['bid_prc' + str(i)].values
            ask_vol_vals[i] = df_dict[df]['ask_vol' + str(i)].values
            bid_vol_vals[i] = df_dict[df]['bid_vol' + str(i)].values

        for k in range(0, len(df_dict[df])):
            current_orderbook = []
            bid_new_orders, ask_new_orders = 0, 0

            for i in range(1, 21):
                current_orderbook.append((bid_prc_vals[i][k], bid_vol_vals[i][k]))
                current_orderbook.append((ask_prc_vals[i][k], ask_vol_vals[i][k]))
                if k == 0:
                    ask_new_orders = 0
                    bid_new_orders = 0
                elif (bid_prc_vals[i][k], bid_vol_vals[i][k]) not in previous_orderbook:
                    bid_new_orders += 1
                elif (ask_prc_vals[i][k], ask_vol_vals[i][k]) not in previous_orderbook:
                    ask_new_orders += 1

            df_dict[df].at[k, 'bid_new_orders'] = bid_new_orders
            df_dict[df].at[k, 'ask_new_orders'] = ask_new_orders
            previous_orderbook = current_orderbook

    return df_dict



def single_file_summary(input_path):
    """ Main function to summarize files and return results, optimizing file reads. """
    results = defaultdict(lambda: defaultdict(list))

    # Gather files
    files = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]
    delta_out_files = [f for f in os.listdir(os.path.join(input_path, 'delta_out')) if os.path.isfile(os.path.join(input_path, 'delta_out', f))]
    date_roots = sorted(list(set([f[8:26] for f in files])))
    last_date = [f for f in files if 'summary' in f][-1].split('_')[1]

    # Initialize weights and exchanges
    weights = {
        '1': 0.0, '2': 0.14465716735322742, '3': 0.00580204432322911,
        '4': 0.3330502301293559, '5': 0.006247723608708225, '6': 0.007997581876292128,
        '9': 0.1000049023782509, '16': 0.2126465688031466, '17': 0.18959378152778963,
        '30': 0.0
    }
    weighted_exchanges = list(weights.keys())
    keep_deri_cols = ['funding_8h', 'current_funding', 'open_interest', 'interest_value', 'index_price']

    print(f'Processing {len(date_roots)} date roots...')

    for root in tqdm(date_roots):
        if 'summary' in root:
            continue

        root_files = [f for f in files if root in f and 'summary' in f]
        delta_root_files = [f for f in delta_out_files if root in f]
        deribit_files = [f for f in files if root in f and 'DERIBIT' in f]

        # Initialize data dicts (we will only load the file data once)
        root_data_dict, delta_data_dict = {}, {}
        weighted_count, weight_sum = 0, 0
        index_start, index_end, index_avg = 0, 0, 0
        bid_flow_total, ask_flow_total, net_flow_total = 0, 0, 0
        full_composite = False

        # Load all files into root_data_dict and delta_data_dict at once
        for root_file in root_files:
            ex_num = root_file.split('_')[-1].split('.')[0]
            delta_root_file = next((f for f in delta_root_files if f'_{ex_num}.csv' in f), None)

            if not delta_root_file:
                continue

            # Load CSV data once
            root_data_dict[ex_num] = pd.read_csv(os.path.join(input_path, root_file))
            delta_data_dict[ex_num] = pd.read_csv(os.path.join(input_path, 'delta_out', delta_root_file))

        # Now process the loaded data without re-reading the files
        for ex_num, root_data in root_data_dict.items():
            delta_data = delta_data_dict[ex_num]

            # Calculate prices
            start_price = root_data['index_price'].iloc[0]
            end_price = root_data['index_price'].iloc[-1]
            avg_price = root_data['index_price'].mean()

            results[ex_num]['start_price'].append(start_price)
            results[ex_num]['end_price'].append(end_price)
            results[ex_num]['avg_price'].append(avg_price)

            if ex_num in weighted_exchanges:
                weight = weights[ex_num]
                weighted_count += 1
                weight_sum += weight
                index_start += weight * start_price
                index_end += weight * end_price
                index_avg += weight * avg_price
                bid_flow_total += delta_data['bid_flow'].abs().sum()
                ask_flow_total += delta_data['ask_flow'].abs().sum()
                net_flow_total += delta_data['net_flow'].sum()

                if weighted_count == len(weighted_exchanges):
                    net_flow_min = delta_data['net_flow'].min()
                    net_flow_max = delta_data['net_flow'].max()
                    normalized_flow_total = (net_flow_total - net_flow_min) / (net_flow_max - net_flow_min) if net_flow_max - net_flow_min != 0 else 0

                    # Save composite results
                    results['composite']['date'].append(root)
                    results['composite']['start_price'].append(index_start)
                    results['composite']['end_price'].append(index_end)
                    results['composite']['avg_price'].append(index_avg)
                    price_delta_bp = 10000 * (index_end - index_start) / index_start if index_start != 0 else 0
                    results['composite']['price_delta_BP'].append(price_delta_bp)
                    results['composite']['bid_flow'].append(bid_flow_total)
                    results['composite']['ask_flow'].append(ask_flow_total)
                    results['composite']['net_flow'].append(net_flow_total)
                    results['composite']['net_flow_normalized'].append(normalized_flow_total)

                    # Reset composite metrics
                    weighted_count = 0
                    index_start, index_end, index_avg = 0, 0, 0
                    full_composite = True

                    # Process Deribit data if available
                    if deribit_files:
                        deri_df = pd.read_csv(os.path.join(input_path, deribit_files[0]))
                        for col in keep_deri_cols:
                            results['composite'][col].append(deri_df[col].mean())

        if not full_composite:
            # Handle missing exchanges for the composite
            results['composite']['date'].append(root)
            if weight_sum == 0:
                results['composite']['start_price'].append(results['composite']['start_price'][-1])
                results['composite']['end_price'].append(results['composite']['end_price'][-1])
                results['composite']['avg_price'].append(results['composite']['avg_price'][-1])
                results['composite']['price_delta_BP'].append(results['composite']['price_delta_BP'][-1])
                results['composite']['bid_flow'].append(results['composite']['bid_flow'][-1])
                results['composite']['ask_flow'].append(results['composite']['ask_flow'][-1])
                results['composite']['net_flow'].append(results['composite']['net_flow'][-1])
                results['composite']['net_flow_normalized'].append(results['composite']['net_flow_normalized'][-1])
            else:
                results['composite']['start_price'].append(index_start / weight_sum)
                results['composite']['end_price'].append(index_end / weight_sum)
                results['composite']['avg_price'].append(index_avg / weight_sum)
                price_delta_bp = 10000 * (index_end / weight_sum - index_start / weight_sum) / (index_start / weight_sum)
                results['composite']['price_delta_BP'].append(price_delta_bp)
                results['composite']['bid_flow'].append(bid_flow_total / weight_sum)
                results['composite']['ask_flow'].append(ask_flow_total / weight_sum)
                results['composite']['net_flow'].append(net_flow_total / weight_sum)

        # Process individual exchange files
        for ex_num, root_data in root_data_dict.items():
            try:
                delta_data = delta_data_dict[ex_num]

                results[ex_num]['bid_flow_sum'].append(delta_data['bid_flow'].abs().sum())
                results[ex_num]['ask_flow_sum'].append(delta_data['ask_flow'].abs().sum())
                results[ex_num]['net_flow_sum'].append(delta_data['net_flow'].sum())
                results[ex_num]['start_price'].append(root_data['index_price'].iloc[0])
                results[ex_num]['end_price'].append(root_data['index_price'].iloc[-1])
                results[ex_num]['avg_price'].append(root_data['index_price'].mean())
                results[ex_num]['date'].append(root)
            except Exception as e:
                print(f"Error processing exchange {ex_num}: {e}")
                results[ex_num]['bid_flow_sum'].append(np.nan)
                results[ex_num]['ask_flow_sum'].append(np.nan)
                results[ex_num]['net_flow_sum'].append(np.nan)
                results[ex_num]['start_price'].append(np.nan)
                results[ex_num]['end_price'].append(np.nan)
                results[ex_num]['avg_price'].append(np.nan)
                results[ex_num]['date'].append(root)

    return results, last_date



def summarize_delta_file(delta_file_data, results, ex_num):
    # sort of experimental attempt to find how the bid/ask/net flows of each exchange compare to the composite or 'normalized' value
    # might need to be revised, but i think this is an interesting path...
    results[ex_num]['bid_flow_share'].append(
        delta_file_data['bid_flow'].abs().sum() / results['composite']['bid_flow'][-1])
    results[ex_num]['ask_flow_share'].append(
        delta_file_data['ask_flow'].abs().sum() / results['composite']['ask_flow'][-1])
    results[ex_num]['net_flow_share'].append(delta_file_data['net_flow'].sum() / results['composite']['net_flow'][-1])

    results[ex_num]['bid_flow'].append(delta_file_data['bid_flow'].abs().sum())
    results[ex_num]['ask_flow'].append(delta_file_data['ask_flow'].abs().sum())
    results[ex_num]['net_flow'].append(delta_file_data['net_flow'].sum())
    results[ex_num]['net_flow_normalized'].append(
        (delta_file_data['net_flow'].sum() - delta_file_data['net_flow'].min()) \
        / (delta_file_data['net_flow'].max() - delta_file_data['net_flow'].min()))

    return results


def summarize_exchange_file(summary_file_data, results, ex_num):
    # filters outliers and calculates some simple and some more complex summary values for each individual data file
    # can definitely be improved
    summary_file_cols = ['bid_new_orders', 'ask_new_orders', 'bid_vol_total', 'ask_vol_total', \
                         'bid_depth_5e-06', 'ask_depth_5e-06', 'bid_depth_1e-05', 'ask_depth_1e-05', \
                         'bid_depth_2.5e-05', 'ask_depth_2.5e-05', 'bid_depth_5e-05', 'ask_depth_5e-05', \
                         'bid_depth_0.0001', 'ask_depth_0.0001', 'simple_spread', 'index_price']

    for col in summary_file_cols:
        colname = col
        vals = list(summary_file_data[colname].values)
        vals = filter_data_two_stdev(vals)

        try:
            # if there are no 'vals' after the filter function, something is wrong!
            results[ex_num][col].append(sum(vals) / len(vals))
        except:
            print(list(summary_file_data[colname].values))
            sys.exit(2)

    results[ex_num]['data_count'].append(len(summary_file_data))
    results[ex_num]['exchange_premium'].append(
        100 * results[ex_num]['avg_price'][-1] / results['composite']['avg_price'][-1])
    results[ex_num]['relative_price_move'].append(
        (results[ex_num]['end_price'][-1] - results[ex_num]['start_price'][-1]) \
        / (results['composite']['end_price'][-1] - results['composite']['start_price'][-1]))

    return results


def calc_initial_mad(input_path, n_files):
    print('Calculating initial MAD...')
    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f))]
    date_roots = sorted(list(set([f[:26] for f in files])))
    vols = []
    prc_diffs = []
    core_cols = []

    for i in range(1, 21):
        core_cols.append('ask_prc' + str(i))
        core_cols.append('bid_prc' + str(i))
        core_cols.append('ask_vol' + str(i))
        core_cols.append('bid_vol' + str(i))

    for root in tqdm(date_roots[:int(n_files)]):
        date_files = [f for f in files if root in f]
        for date_file in date_files:
            if 'summary' in date_file:
                continue
            if 'DERIBIT' in date_file:
                continue
            if '_1.csv' not in date_file:
                continue
            data = pd.read_csv(input_path + '/' + date_file)
            for col in core_cols:
                if 'vol' in col:
                    vols.extend(list(data[col].values))
                elif 'prc' in col:
                    # calculate the difference of each value from the previous value
                    # diffs_col = [data[col].values[i] - data[col].values[i-1] for i in range(1,len(data[col].values))]
                    prc_diffs.extend(data[col].values)

    # calculate median absolute deviation
    print('Data length... ' + str(len(vols)))
    median_vol = statistics.median(vols)
    median_prc = statistics.median(prc_diffs)
    print('Median vol ::: ' + str(median_vol))
    print('Median prc ::: ' + str(median_prc))

    mad_vol = statistics.median([abs(v - median_vol) for v in vols])
    mad_prc = statistics.median([abs(v - median_prc) for v in prc_diffs])
    print('MAD vol ::: ' + str(mad_vol))
    print('MAD prc ::: ' + str(mad_prc))

    return mad_vol, mad_prc, median_vol, median_prc


def qa_raw_data(input_path):
    # quality assurance function draft for raw data.
    # not currently used in the daily autoanalysis, but possibly a base for some ideas
    exchanges = [9]
    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f)) and 'summary' not in f]
    date_roots = sorted(list(set([f[:26] for f in files if 'summary' not in f and 'DERIBIT' not in f])))
    day_str = files[-1][:10].replace('-', '_')
    results = defaultdict(lambda: [])
    last_times = defaultdict(lambda: [])
    core_cols = []
    for i in range(1, 21):
        core_cols.append('ask_prc' + str(i))
        core_cols.append('bid_prc' + str(i))
        core_cols.append('ask_vol' + str(i))
        core_cols.append('bid_vol' + str(i))

    # 'mad' = "mean absolute deviation" -- one method of finding outliers.  could possibly be improved
    mad_vol, mad_prc, median_vol, median_prc = calc_initial_mad(input_path, 4)

    for ex in exchanges:
        for root in tqdm(date_roots[5:]):
            df_dict = {}
            date_files = [f for f in files if root in f]
            for date_file in date_files:
                if 'summary' in date_file or 'DERIBIT' in date_file:
                    continue
                if '_' + str(ex) + '.csv' not in date_file:
                    continue

                data = pd.read_csv(input_path + '/' + date_file)
                ex_num = date_file.split('_')[-1].split('.')[0]
                file_len = len(data)
                results['date'].append(root)
                results['data_count'].append(file_len)

                for col in core_cols:
                    vals = list(data[col].values)
                    if 'vol' in col:
                        zero_vals = [v for v in vals if v == 0]
                        vals = [v for v in vals if v != 0]
                        # outlier_vals = [v for v in vals if v > median_vol + 30*mad_vol or v < median_vol - 30*mad_vol or v < 0]
                        outlier_vals = [v for v in vals if v < 0 or v > 50]
                        results[col + '_outlier_count'].append(len(outlier_vals))
                        results[col + '_zero_count'].append(len(zero_vals))
                        # median_vol = statistics.median(vals)
                    elif 'prc' in col:
                        #     prc_diff_vals = [vals[i] - vals[i-1] for i in range(1,len(vals))]
                        zero_vals = [v for v in vals if v == 0]
                        vals = [v for v in vals if v != 0]
                        outlier_vals = [v for v in vals if
                                        v > median_prc + 15 * mad_prc or v < median_prc - 15 * mad_prc]
                        results[col + '_outlier_count'].append(len(outlier_vals))
                        results[col + '_zero_count'].append(len(zero_vals))
                        median_prc = statistics.median(vals)

                date_vals = list(data['date'].values)
                # sample date -- 2023-12-20 12:02:56.565000
                first_time = date_vals[0]
                last_times[ex_num].append(date_vals[-1])
                time_diffs = [(pd.Timestamp(date_vals[i + 1]) - pd.Timestamp(date_vals[i])).total_seconds() for i in
                              range(len(date_vals) - 1)]
                results['max_time_diff'].append(max(time_diffs))
                results['avg_time_diff'].append(sum(time_diffs) / len(time_diffs))
                if len(last_times[ex_num]) > 1:
                    results['file_time_diff'].append(
                        (pd.Timestamp(first_time) - pd.Timestamp(last_times[ex_num][-2])).total_seconds())
                else:
                    results['file_time_diff'].append(0)

        for key in results:
            if 'date' in key or 'data_count' in key or 'file_time_diff' in key:
                continue
            print(key + ' ::: ' + str(round(100 * sum(results[key]) / len(results[key]), 3)))

        # get count of results['file_time_diff'] values greater than 5
        print('file_time_diff > 5 ::: ' + str(len([v for v in results['file_time_diff'] if v > 5])))
        print('data count total ::: ' + str(sum(results['data_count'])))

        df = pd.DataFrame(results)
        df.to_csv(input_path + 'qa_' + day_str + '_ex' + str(ex) + '.csv', index=False)


def filter_data_two_stdev(data_list):
    # filter out data outliers to make plots more readable -- might want to remove this sometimes to see and understand outliers
    data_list = [float(d) for d in data_list]
    mean = sum(data_list) / len(data_list)
    stdev = statistics.stdev(data_list)

    if stdev == 0:
        return data_list
    else:
        filtered_data = [d for d in data_list if mean - stdev <= d <= mean + stdev]
        return filtered_data


def filter_spread_data(data, avg_price, spread_val, ex_num):
    bid_vals = list(data['EX' + ex_num + 'bid_market_depth_' + spread_val + 'BTC'].values)
    ask_vals = list(data['EX' + ex_num + 'ask_market_depth_' + spread_val + 'BTC'].values)

    bid_vals = [(1 / float(spread_val)) * float(v) for v in bid_vals if
                avg_price * 0.9 < (1 / float(spread_val)) * float(v) < avg_price * 1.1]
    ask_vals = [(1 / float(spread_val)) * float(v) for v in ask_vals if
                avg_price * 0.9 < (1 / float(spread_val)) * float(v) < avg_price * 1.1]

    avg_spread = sum(ask_vals) / len(ask_vals) - sum(bid_vals) / len(bid_vals)

    return avg_spread


def exponential_moving_average(alpha, prev_avg, step_val):
    return alpha * step_val + (1 - alpha) * prev_avg


def weights_moving_average(alpha, prev_weights, step_weights):
    base = [exponential_moving_average(alpha, prev_weights[i], step_weights[i]) for i in range(len(step_weights))]
    sum_base = sum(base)
    return [e / sum_base for e in base]


def plot_summary_data(input_path):
    exchanges = [1, 2, 3, 4, 5, 6, 9, 16, 17, 30, 31]
    # exchanges = [3]
    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f))]
    # create input_path + '/plots' directory if it doesn't exist
    pathlib.Path(input_path + '/plots').mkdir(parents=True, exist_ok=True)

    for ex_num in exchanges:
        df_ex = pd.DataFrame()
        exchange_files = sorted([f for f in files if '_ex' + str(ex_num) + '_' in f])

        for e in exchange_files:
            print('Processing ::: ' + e)
            df = pd.read_csv(input_path + '/' + e)
            df_ex = pd.concat([df_ex, df], ignore_index=True)

        cols = list(df.columns)
        print('Processing ::: ' + str(ex_num))

        x_labels_vals = list(df_ex['date'].values)
        # keep first thirteen characters of date string -- cleans up date labels in plot
        x_labels_vals = [x[:13] for x in x_labels_vals]
        xticks = []
        xlabels = []
        i = 1
        while i < len(x_labels_vals):
            xticks.append(i)
            xlabels.append(x_labels_vals[i])
            i += int(5000)

        for c in cols:
            print('Plotting ::: ' + c)
            if 'date' in c or 'avg_price' in c or 'start_price' in c or 'end_price' in c or 'data_count' in c:
                continue
            fig, ax1 = plt.subplots(figsize=(20, 10))
            ax2 = ax1.twinx()
            plot_vals = df_ex[c].values

            # plot exponential moving averages to smooth noise in the data / make plots readable
            ema_vals = [plot_vals[0]]
            for i in range(1, len(plot_vals)):
                ema_vals.append(exponential_moving_average(0.005, ema_vals[-1], plot_vals[i]))

            ax1.plot(df_ex['date'], ema_vals, color='blue')
            ax2.plot(df_ex['date'], df_ex['avg_price'], color='red')
            ax1.set_xticks(xticks)
            ax1.set_xticklabels(labels=xlabels, rotation=45)

            ax1.set_xlabel('Date')
            ax1.set_ylabel(c, color='blue')
            ax2.set_ylabel('avg_price', color='red')
            plt.title(c + ' and avg_price over time')
            plt.savefig(input_path + '/plots/' + str(ex_num) + '_' + c + '.png')
            plt.close(fig)
