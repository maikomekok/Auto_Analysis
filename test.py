def single_file_summary(input_path):
    # this is the ugliest bullshit function I've ever written and i am ashamed of it.
    results = defaultdict(lambda: defaultdict(lambda: []))

    files = [f for f in os.listdir(input_path) if isfile(os.path.join(input_path, f))]
    delta_out_files = [f for f in os.listdir(input_path + '/delta_out/') if
                       isfile(os.path.join(input_path + '/delta_out/', f))]
    date_roots = sorted(list(set([f[8:26] for f in files])))
    last_date = [f for f in files if 'summary' in f][-1].split('_')[1]
    weights = {'1': 0.0, '2': 0.14465716735322742, '3': 0.00580204432322911, '4': 0.3330502301293559,
               '5': 0.006247723608708225, \
               '6': 0.007997581876292128, '9': 0.1000049023782509, '16': 0.2126465688031466, '17': 0.18959378152778963,
               '30': 0.0}
    weighted_exchanges = ['1', '2', '3', '4', '5', '6', '9', '16', '17', '30']
    keep_deri_cols = ['funding_8h', 'current_funding', 'open_interest', 'interest_value', 'index_price']

    print('Processing ' + str(len(date_roots)) + ' date roots...')
    for root in tqdm(date_roots):
        if 'summary' in root:
            continue
        root_files = [f for f in files if root in f and 'summary' in f]
        delta_root_files = [f for f in delta_out_files if root in f]
        deribit_files = [f for f in files if root in f and 'DERIBIT' in f]
        root_data_dict, delta_data_dict = {}, {}
        weighted_count, index_start, index_end, index_avg = 0, 0, 0, 0
        bid_flow_total, ask_flow_total, net_flow_total, weight_sum = 0, 0, 0, 0
        full_composite = False

        for root_file in root_files:
            ex_num = root_file.split('_')[-1].split('.')[0]
            delta_root_file = [f for f in delta_root_files if '_' + ex_num + '.csv' in f][0]
            root_data_dict[ex_num] = pd.read_csv(input_path + '/' + root_file)
            delta_data_dict[ex_num] = pd.read_csv(input_path + '/delta_out/' + delta_root_file)

            results[ex_num]['start_price'].append(root_data_dict[ex_num]['index_price'].iloc[0])
            results[ex_num]['end_price'].append(root_data_dict[ex_num]['index_price'].iloc[-1])
            results[ex_num]['avg_price'].append(root_data_dict[ex_num]['index_price'].mean())

            if ex_num in weighted_exchanges:
                # this 'composite' stuff is an attempt to make an 'average' from all of the metrics across all exchanges
                # ... the idea being we can then compare any exchange with the 'composite' average and see where they are in our little family of exchanges
                weighted_count += 1
                weight_sum += weights[ex_num]
                index_start += weights[ex_num] * results[ex_num]['start_price'][-1]
                index_end += weights[ex_num] * results[ex_num]['end_price'][-1]
                index_avg += weights[ex_num] * results[ex_num]['avg_price'][-1]
                bid_flow_total += delta_data_dict[ex_num]['bid_flow'].abs().sum()
                ask_flow_total += delta_data_dict[ex_num]['ask_flow'].abs().sum()
                net_flow_total += delta_data_dict[ex_num]['net_flow'].sum()
                normalized_flow_total = (delta_data_dict[ex_num]['net_flow'].sum() - delta_data_dict[ex_num][
                    'net_flow'].min()) \
                                        / (delta_data_dict[ex_num]['net_flow'].max() - delta_data_dict[ex_num][
                    'net_flow'].min())

                if weighted_count == len(weighted_exchanges):
                    results['composite']['date'].append(root)
                    results['composite']['start_price'].append(index_start)
                    results['composite']['end_price'].append(index_end)
                    results['composite']['avg_price'].append(index_avg)
                    results['composite']['price_delta_BP'].append(10000 * (results['composite']['end_price'][-1] - \
                                                                           results['composite']['start_price'][-1]) / \
                                                                  results['composite']['start_price'][-1])
                    results['composite']['bid_flow'].append(bid_flow_total)
                    results['composite']['ask_flow'].append(ask_flow_total)
                    results['composite']['net_flow'].append(net_flow_total)
                    results['composite']['net_flow_normalized'].append(normalized_flow_total)
                    weighted_count = 0
                    index_start = 0
                    index_end = 0
                    index_avg = 0
                    full_composite = True

                    try:
                        deri_file = deribit_files[0]
                        deri_df = pd.read_csv(input_path + '/' + deri_file)
                        for col in keep_deri_cols:
                            results['composite'][col].append(deri_df[col].mean())
                    except:
                        # print('Error deribit processing ::: ' + str(deribit_files))
                        pass

        if not full_composite:
            # this whole thing is a (BAD) way to deal with missing exchanges in the base data
            # if any exchange is missing, full_composite will be false and the calculations will adjust
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
                results['composite']['price_delta_BP'].append(10000 * (results['composite']['end_price'][-1] - \
                                                                       results['composite']['start_price'][-1]) / \
                                                              results['composite']['start_price'][-1])
                results['composite']['bid_flow'].append(bid_flow_total / weight_sum)
                results['composite']['ask_flow'].append(ask_flow_total / weight_sum)
                results['composite']['net_flow'].append(net_flow_total / weight_sum)
            weighted_count = 0
            index_start = 0

            try:
                deri_file = deribit_files[0]
                deri_df = pd.read_csv(input_path + '/' + deri_file)
                for col in keep_deri_cols:
                    results['composite'][col].append(deri_df[col].mean())

            except:
                # print('Error deribit processing ::: ' + str(deribit_files))
                pass

        for root_file in root_files:
            try:
                ex_num = root_file.split('_')[-1].split('.')[0]
                delta_root_file = [f for f in delta_root_files if '_' + ex_num + '.csv' in f][0]
                root_file_data = root_data_dict[ex_num]
                delta_root_file_data = delta_data_dict[ex_num]
            except:
                print('Error processing ::: ' + root_file)
                continue

            results = summarize_delta_file(delta_root_file_data, results, ex_num)
            results = summarize_exchange_file(root_file_data, results, ex_num)
            results[ex_num]['date'].append(root)

        # for deri_file in deribit_files:
    return results, last_date
