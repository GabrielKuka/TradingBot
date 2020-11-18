# This algorithms uses the dual average crossover to determine when to buy and
# when to sell.


import json
from helper import bars
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import helper.file_manager as file_manager

from interfaces.IAlgorithm import IAlgorithm
from connection.websocket import WebSocket
from helper.CSVReadWrite import CSVReadWrite
from helper.ValidateString import ValidateString
from multiprocessing import Process
from threading import Thread
from connection.account import Account
from connection.market import Market
from connection.orders import Orders


def display_header():
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~\n")
    print("Dual Moving Average Crossover")
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~")


def enter_data():
    asset, days = None, None

    while True:
        asset = input("\nEnter asset => ")

        if not ValidateString.is_asset_valid(asset):
            print("\n[Asset Not Valid]\n")
            print("1. Asset must be in capital.")
            print("2. Asset must be at most 4 characters.")
        else:
            break

    return asset


class DualAverageCrossover(IAlgorithm):

    def ws_open(self, ws):
        self.ws.on_open(ws)

        # Get the last 100 prices
        self.closes = list(self.df['Close'])[-100:]

        # Stream minute bars
        self.ws.stream_minute_bars(self.symbol)

    def ws_close(self, ws):
        self.ws.on_close(ws)

        # Delete csv file
        file_manager.delete_file('temp_files/{}.csv'.format(self.symbol))

        # Terminate process if still running
        if self.p is not None:
            self.p.terminate()
            self.p.join()

    def ws_message(self, ws, message):
        # Liquidate position
        if self.__market.is_market_closing():
            self.close_position_before_market_close()

            # Close graphs
            if self.p is not None:
                self.p.terminate()
                self.p.join()

            return

        # Convert data to python dict
        message = json.loads(message)

        self.ws.on_message(ws, message)

        # Get the required data: time, close price
        bar_data = message['data']
        close_price = bar_data['c']
        close_time = datetime.fromtimestamp(int(str(bar_data['e'])[:-3])).strftime("%H:%M")

        # Add the received price in the list
        self.closes.append(close_price)

        # Calc metrics
        sma30 = self.calc_metrics()[0]
        sma100 = self.calc_metrics()[1]

        # New Entry
        new_entry = {
            'Date': close_time,
            'Close': close_price,
            'SMA30': sma30,
            'SMA100': sma100,
            'buy_signal': np.nan,
            'sell_signal': np.nan
        }

        # Get Signal
        self.buy_sell(new_entry)

        # Add Entry to file
        new_entry_str = '{},{},{},{},{},{}  '.format(
            close_time, close_price, new_entry['buy_signal'], new_entry['sell_signal'], sma30, sma100
        )
        file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

        # Add entry to dataframe
        self.df = self.df.append(new_entry, ignore_index=True)

        # Print data on the screen
        print('{}\tPrice: {}\tSMA30: {}\tSMA100: {}'.format(
            close_time, close_price,
            new_entry['SMA30'], new_entry['SMA100']
        ))

    def calc_metrics(self):
        closes = self.closes[-100:]

        sma30 = sum(closes[-30:])/30
        sma100 = sum(closes)/100

        return sma30, sma100

    def __init__(self, mode):

        # In case of any error
        self.error = False

        # Bot mode
        self.mode = mode

        # Display Header
        display_header()

        self.symbol = enter_data()

        if self.mode == 'active':
            # Setup Plot
            plt.style.use('seaborn')
            self.fig, self.ax = plt.subplots()

            # Account references
            self.__orders = Orders()
            self.__account = Account()
            self.__market = Market()

            # Dataframe to store data
            self.df = pd.DataFrame()

            # Qty to purchase
            self.QTY = 50

            # Tracks position status
            self.in_position = False

            # Tracks the close prices
            self.closes = []

            # Init websocket
            self.ws = WebSocket(self)

            # Track buy price
            self.buy_price = 0

            # Setup the plot's process
            self.p = Process(target=self.plot_live_graph)

        elif self.mode == 'test':
            self.hist_df = pd.DataFrame()
        else:
            print('Weird!')

    def retrieve_data(self):
        # Retrieve bars from API
        print("[Requesting Data]")

        # Create CSV File
        csv_file = CSVReadWrite("temp_files/{}.csv".format(self.symbol), "Date,Close")

        if self.mode == 'active':

            bars_dict = bars.get_historical_data(self.symbol, 200, '1Min')

            if bars_dict:
                csv_file.write_file(bars_dict, 't', 'c')
                self.df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.df = self.df.set_index(pd.DatetimeIndex(self.df['Date'].values).strftime("%H:%M"))
                self.df['buy_signal'] = np.nan
                self.df['sell_signal'] = np.nan
            else:
                self.error = True
        elif self.mode == 'test':
            bars_dict = bars.get_historical_data(self.symbol, 400, 'day')
            if bars_dict:
                csv_file.write_file(bars_dict, 't', 'c')
                self.hist_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.hist_df = self.hist_df.set_index(pd.DatetimeIndex(self.hist_df['Date'].values))
            else:
                self.error = True

    def pre_calculate(self, data):

        # Calculate SMA30
        data['SMA30'] = data['Close'].rolling(window=30).mean()

        # Calculate SMA100
        data['SMA100'] = data['Close'].rolling(window=100).mean()

        # Write to file
        data.to_csv(r'temp_files/{}.csv'.format(self.symbol), index=False)

    def buy_sell(self, data):

        if data['SMA30'] > data['SMA100']:
            # Sell
            if self.in_position:
                if self.buy_price <= data['Close']:
                    # Submit order
                    t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                    t.start()

                    # Change position status
                    self.in_position = False

                    # Add sell signal
                    data['sell_signal'] = data['Close']

                    # Reset buy price
                    self.buy_price = 0

                    # Wait for order to finish
                    t.join()
                else:
                    print('We bought at a higher price. Can\'t sell now.')
            else:
                print('Sell signal generated. No asset to sell.')
        elif data['SMA100'] < data['SMA30']:
            # Buy
            if not self.in_position:
                # Submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'buy'])
                t.start()

                # Change position status
                self.in_position = True

                # Add buy signal
                data['buy_signal'] = data['Close']

                # Set buy price
                self.buy_price = data['Close']

                # Wait for order to finish
                t.join()

    def liquidate_position(self):
        has_position = self.__account.has_position(self.symbol)

        if has_position[0]:
            print("[Closing Position].")
            side = 'sell'

            qty = abs(int(float(has_position[1].qty)))

            t_submit_order = Thread(target=self.__orders.submit_order,
                                    args=[self.symbol, qty, side])

            t_submit_order.start()
            t_submit_order.join()

    def close_position_before_market_close(self):
        # Close position
        print("Market closing soon.")

        # Liquidate
        self.liquidate_position()

        print("[EXITING]")
        exit()

    def buy_sell_historical(self, data):

        print("[Executing Algo]")

        buy_signal = []
        sell_signal = []
        crossed = -1

        for i in range(len(data)):
            if data['SMA30'][i] > data['SMA100'][i]:
                if crossed != 1:
                    sell_signal.append(data['Close'][i])
                    buy_signal.append(np.nan)
                    crossed = 1
                else:
                    sell_signal.append(np.nan)
                    buy_signal.append(np.nan)

            elif data['SMA30'][i] < data['SMA100'][i] and crossed == 1:
                if crossed != 0:
                    sell_signal.append(np.nan)
                    buy_signal.append(data['Close'][i])
                    crossed = 0
                else:
                    sell_signal.append(np.nan)
                    buy_signal.append(np.nan)
            else:
                sell_signal.append(np.nan)
                buy_signal.append(np.nan)

        return buy_signal, sell_signal

    def plot_hist_graph(self, data):
        print("[Drawing Graph]")

        plt.style.use("fivethirtyeight")

        fig, ax = plt.subplots(1, 1, facecolor='black')

        fig.suptitle('Dual Moving Averages Crossover', color='white')

        # Disable the grid
        ax.grid(False)

        # Set background color and change axis values color
        ax.set_facecolor('black')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')

        ax.set_ylabel('{} price in $ (USD)'.format(self.symbol), color='white')

        # Disable the top and right axis
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Change the color of the left and bottom axis
        ax.spines['left'].set_color('gray')
        ax.spines['bottom'].set_color('gray')

        # Plot asset prices
        ax.plot(data['Close'], label='Close Prices', color='orange', alpha=0.5, linewidth=2)

        # Plot SMA30 and SMA100
        ax.plot(data['SMA30'], label='SMA30', color='brown', alpha=0.4, linewidth=1)
        ax.plot(data['SMA100'], label='SMA100', color='brown', alpha=0.4, linewidth=1)

        # Draw buy and sell signals
        ax.scatter(data.index, data['Buy'], label='Buy', marker='^',
                   color='green')
        ax.scatter(data.index, data['Sell'], label='Sell', marker='v',
                   color='red')

        ax.legend(loc='upper left')

        plt.xticks(rotation=45, fontsize=7)
        plt.show()

    def plot_live_graph(self):
        self.fig.suptitle("Dual Moving Averages Crossover")

        ani = animation.FuncAnimation(self.fig, self.animate_graph)
        plt.show()

    def animate_graph(self, i):
        # Read file
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))

        # Clear and plot
        self.ax.clear()
        self.ax.plot(file_df['Date'], file_df['Close'], label='Close Price', color='black', lw=2)
        self.ax.plot(file_df['Date'], file_df['SMA30'], label='SMA30', color='red', lw=1)
        self.ax.plot(file_df['Date'], file_df['SMA100'], label='SMA100', color='blue', lw=1)

        # Draw buy and sell signals
        self.ax.scatter(file_df['Date'], file_df['buy_signal'], label='Buy Signal', color='green', alpha=1.0, marker='^')
        self.ax.scatter(file_df['Date'], file_df['sell_signal'], label='Sell Signal', color='red', alpha=1.0, marker='v')

        # Remove grid
        self.ax.grid(False)

        self.ax.xaxis.set_ticks([])

        # Show the legend
        self.ax.legend(loc='upper left')

        # Set labels
        self.ax.set_ylabel('Close Price of {} in $'.format(self.symbol))

    def execute(self):

        if self.error:
            # Delete csv file
            file_manager.delete_file('temp_files/{}.csv'.format(self.symbol))
            return

        if self.mode == 'active':
            # Cancel existing orders
            self.__orders.cancel_opened_orders()

            # Liquidate position if it exists
            self.liquidate_position()

            # Wait for market to open
            t = Thread(target=self.__market.await_market_open)
            t.start()
            t.join()
            print("[Market Opened]")

            # Retrieve historical data about the asset
            self.retrieve_data()

            # Calculate metrics
            self.pre_calculate(self.df)

            # Start algo in a thread
            t_socket = Thread(target=self.ws.connect_socket)
            t_socket.start()

            # Run the plot's process
            self.p.start()

            # Wait for socket to close
            t_socket.join()

        elif self.mode == 'test':

            # Retrieve historical data
            self.retrieve_data()

            # Calculate Metrics
            self.pre_calculate(self.hist_df)

            # Get buy and sell signals
            self.hist_df = self.hist_df[99:]
            self.hist_df['Buy'] = self.buy_sell_historical(self.hist_df)[0]
            self.hist_df['Sell'] = self.buy_sell_historical(self.hist_df)[1]

            # Plot graph
            self.plot_hist_graph(self.hist_df)

        # Delete CSV File
        file_manager.delete_file('{}.csv'.format(self.symbol), True)