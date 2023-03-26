import numpy as np
import pandas as pd
import argparse
from replay import orderbook_generator
from get_BINANCE_history_trade_count import get_BINANCE_history_trade_count
from datetime import datetime
import pytz
from tqdm import tqdm

BINANCE_history_trade_count = get_BINANCE_history_trade_count()
record_start_ts_nanoseconds = BINANCE_history_trade_count["start_ts_nanoseconds"]
record_end_ts_nanoseconds = BINANCE_history_trade_count["end_ts_nanoseconds"]
full_symbol = BINANCE_history_trade_count["history_trade_count"][-1]["full_symbol"]

start = datetime.fromtimestamp(record_start_ts_nanoseconds / 1000000000, tz=pytz.utc)


parser = argparse.ArgumentParser()
parser.add_argument("--data", default='../data/2505133.csv', help="filename.", type=str)
parser.add_argument("--volume_threshold", default=1000000, help="Volume threshold", type=int)
parser.add_argument("--ticksize", default=0.0001, help="ticksize", type=float)
parser.add_argument("--maxlevel", default=10, help="maximum level of the book to study", type=int)
parser.add_argument("--time_discretization", default='volumebar', help="how to discretize time, if in volumebar or natural", type=str)
parser.add_argument("--data_frac", default=1, help="fraction of messages to read", type=float)
parser.add_argument("--only_changes", default=False, \
help="if true, the informations are stored only if the first maxlevel levels of the book change", type=bool)

def main(data, volume_threshold, ticksize, maxlevel, time_discretization, data_frac, only_changes):
    """
    Computes the necessary quantities to compute the order flow imbalance, 
    see R. Cont, A. Kukanov, S. Stoikov, 'The Price Impact of Order Book Events', and
    K. Xu1, M.D. Gould1, and S.D. Howison1, 'Multi-Level Order-Flow Imbalance in a Limit Order Book'

    args:
        data: path to the dataframe containing the raw messages
        volume_threshold: volume threshold build a volume bar
        ticksize: discretization interval of prices at which a security is
        maxlevel: maximum level of the book to study
        time_discretization: how to discretize time, if in volumebar or natural (i.e. each time aa message is read)
        data_frac: fraction of messages to read
        only_changes: if true, the informations are stored only if the first maxlevel levels of the book change
    """

    bid_prices, bid_volumes, ask_prices, ask_volumes, time, mid_price, volume_bar_label = [],[],[],[],[],[],[]

    label = 0
    for book in orderbook_generator(start, full_symbol, block_size=5000):
        ask_side, bid_side = book.asks, book.bids

        if not (any(ask_side) and any(bid_side)): continue
        ask = list(ask_side.items())
        bid = list(bid_side.items())

        if len(ask) < maxlevel or len(bid) < maxlevel: continue

        a = ask[:maxlevel]
        b = bid[:maxlevel]

        if only_changes:
            try: old_a and old_b
            except: #if old_a and old_b are not defined
                old_a = a
                old_b = b
            else: #check if the book has changed
                if np.all(a == old_a) and np.all(b == old_b): continue
            old_a = a
            old_b = b
            
        # label volume bar
        volume_bar_label.append(label)
        label += 1

        ask_prices.append(list(book.asks.keys())[:maxlevel])
        ask_volumes.append(list(book.asks.values())[:maxlevel])
        bid_prices.append(list(book.bids.keys())[:maxlevel])
        bid_volumes.append(list(book.bids.values())[:maxlevel])
        mid_price.append(np.abs(a[0][0]+b[0][0])/2)
        # int(pd.Timestamp(book.timestamp).to_datetime64())
        time.append(book.timestamp)

    df = pd.DataFrame(time,columns=['time'])
    for i in tqdm (range(maxlevel), desc = 'Assembling levels of the DataFrame'):
        df['ask_price_{}'.format(i)] = np.array(ask_prices, dtype=object)[:,i]
        df['ask_volume_{}'.format(i)] = np.array(ask_volumes, dtype=object)[:,i]
        df['bid_price_{}'.format(i)] = np.array(bid_prices, dtype=object)[:,i]
        df['bid_volume_{}'.format(i)] = np.array(bid_volumes, dtype=object)[:,i]
    df['mid_price'.format(i)] = mid_price
    df['volume_bar_label'] = volume_bar_label
    import os
    dir = '../data_cleaned'
    if os.path.isdir(dir)==False:
            os.mkdir(dir)
    print('Saving the DataFrame to {}'.format(dir))
    df.to_csv(dir+'/time_evolution_{}_levels_{}.csv'.format(maxlevel, time_discretization), index=False)

if __name__ == "__main__":
    args = vars(parser.parse_args())
    main(**args)


