# This algorithm uses two bollinger bands to determine when to buy or sell and asset

import json
from datetime import datetime
from multiprocessing import Process
from threading import Thread

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from helper import bars
import helper.file_manager as file_manager
import math
from connection.account import Account
from connection.websocket import WebSocket
from helper.CSVReadWrite import CSVReadWrite
from helper.ValidateString import ValidateString
from interfaces.IAlgorithm import IAlgorithm
from connection.market import Market
from connection.orders import Orders


def display_header():
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~\n")
    print("Bollinger Bands")
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~")


def enter_data():
    asset = None
    while True:
        asset = input("\nEnter asset: ")

        if not ValidateString.is_asset_valid(asset):
            print("Asset entered is not valid.")
        else:
            break

    return asset


class BollingerBands(IAlgorithm):

    def ws_open(self, ws):
        self.ws.on_open(ws)

        # Get the last 20 prices
        self.closes = list(self.df['Close'][-20:])

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

        # Get the required data: close price, date
        bar_data = message['data']
        close_price = bar_data['c']
        close_time = datetime.fromtimestamp(int(str(bar_data['e'])[:-3])).strftime("%H:%M")

        # Add the received price in the list
        self.closes.append(close_price)

        # Calc metrics
        sma = self.calc_metrics()[0]
        std = self.calc_metrics()[1]
        upper = self.calc_metrics()[2]
        lower = self.calc_metrics()[3]

        # New entry
        new_entry = {
            'Date': close_time,
            'Close': close_price,
            'SMA': sma,
            'STD': std,
            'Upper': upper,
            'Lower': lower,
            'buy_signal': np.nan,
            'sell_signal': np.nan
        }

        # Get signal
        self.buy_sell(new_entry)

        # Add entry to file
        new_entry_str = '\n{},{},{},{},{},{},{},{}'.format(
            close_time, close_price,
            new_entry['buy_signal'], new_entry['sell_signal'],
            new_entry['SMA'], new_entry['STD'],
            new_entry['Upper'], new_entry['Lower']
        )
        file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

        # Add entry to dataframe
        self.df = self.df.append(new_entry, ignore_index=True)

        # Print data on the screen
        print('{}\t{}\tUpper band: {}\tLower band: {}'.format(
            close_time, close_price,
            new_entry['Upper'], new_entry['Lower']
        ))

    def calc_metrics(self):
        closes = self.closes[-20:]

        # Calc the STD
        sma = sum(closes) / self.PERIOD
        std = self.std(closes, sma)

        # Calc Upper band and lower band
        upper = sma + (2 * std)
        lower = sma - (2 * std)

        return sma, std, upper, lower

    def std(self, data, mean):

        # Square deviations
        deviations = [(x - mean) ** 2 for x in data]

        # Variance
        variance = sum(deviations) / self.PERIOD

        return math.sqrt(variance)

    def __init__(self, mode):

        # Set bot mode
        self.mode = mode

        # In case something goes wrong
        self.error = False

        # Period over which calculations will be made
        self.PERIOD = 20

        # Display header
        display_header()

        # Enter asset
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
            self.QTY = 1000

            # Track buy price
            self.buy_price = 0

            # Tracks position status
            self.in_position = False

            # Tracks the close prices
            self.closes = []

            # Init websocket
            self.ws = WebSocket(self)

            # Setup the plot's process
            self.p = Process(target=self.plot_live_graph)

        elif self.mode == 'test':
            # self.position = False
            self.hist_df = pd.DataFrame()

    def retrieve_data(self):

        # In case no error, write data to a file
        csv_file = CSVReadWrite("temp_files/{}.csv".format(self.symbol),
                                "Date,Close")

        if self.mode == 'active':
            bars_dict = bars.get_historical_data(self.symbol, 100, '1Min')
            if bars_dict:
                csv_file.write_file(bars_dict, 't', 'c')
                self.df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.df = self.df.set_index(pd.DatetimeIndex(self.df['Date'].values).strftime("%H:%M"))
                self.df['buy_signal'] = np.nan
                self.df['sell_signal'] = np.nan
            else:
                self.error = True
        else:
            bars_dict = bars.get_historical_data(self.symbol, 100, 'day')
            if bars_dict:
                csv_file.write_file(bars_dict, 't', 'c')
                self.hist_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.hist_df = self.hist_df.set_index(
                    pd.DatetimeIndex(self.hist_df['Date'].values).strftime("%Y:%m:%d"))
            else:
                self.error = True

    def pre_calculate(self, data):

        # Calculate the Simple Moving Average
        data['SMA'] = data['Close'].rolling(window=self.PERIOD).mean()

        # Calculate the standard deviation
        data['STD'] = data['Close'].rolling(window=self.PERIOD).std()

        # Calculate the upper bands and the lower bands
        data['Upper'] = data['SMA'] + (2 * data['STD'])
        data['Lower'] = data['SMA'] - (2 * data['STD'])

        # Write to file
        data.to_csv(r'temp_files/{}.csv'.format(self.symbol), index=False)

    def buy_sell(self, data):

        if data['Close'] > data['Upper']:
            # Sell!
            print('Sell signal!')
            if self.in_position:
                if self.buy_price <= data['Close']:
                    # Run thread to submit order
                    t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                    t.start()

                    # Change position status
                    self.in_position = False

                    # Reset buy price
                    self.buy_price = 0

                    # Add sell signal
                    data['sell_signal'] = data['Close']

                    # Wait for order to finish
                    t.join()
                else:
                    print('We bought at a higher price. Can\'t sell now.')
            else:
                print('Nothing to sell.')
        elif data['Close'] < data['Lower']:
            # Buy
            print('Buy signal!')
            if not self.in_position:
                # Run thread to submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'buy'])
                t.start()

                # Change position status
                self.in_position = True

                # Set buy price
                self.buy_price = data['Close']

                # Add buy signal
                data['buy_signal'] = data['Close']

                # Wait for order to finish
                t.join()
            else:
                print('Already in position.')

    def buy_sell_historical(self, data):

        buy_signal = []
        sell_signal = []

        for i in range(len(data['Close'])):
            if data['Close'][i] >= data['Upper'][i]:
                # Sell
                buy_signal.append(np.nan)
                sell_signal.append(data['Close'][i])
            elif data['Close'][i] <= data['Lower'][i]:
                # Buy
                buy_signal.append(data['Close'][i])
                sell_signal.append(np.nan)
            else:
                # Do nothing
                buy_signal.append(np.nan)
                sell_signal.append(np.nan)

        return buy_signal, sell_signal

    def close_position_before_market_close(self):

        # Close position
        print("Market closing soon.")

        # Liquidate
        self.liquidate_position()

        print("[EXITING]")

    def liquidate_position(self):
        has_position = self.__account.has_position(self.symbol)

        if has_position[0]:
            print("[Liquidating].")
            side = 'sell'

            qty = abs(int(float(has_position[1].qty)))

            t_submit_order = Thread(target=self.__orders.submit_order,
                                    args=[self.symbol, qty, side])

            t_submit_order.start()
            t_submit_order.join()

    def plot_hist_graph(self, data):
        plt.style.use('fivethirtyeight')
        fig = plt.figure(figsize=(12.2, 6.4), facecolor='white')

        # Add the subplot
        ax = fig.add_subplot(111)

        ax.xaxis.set_ticks([])

        # Change the color of the left and bottom axis
        ax.spines['bottom'].set_color('gray')
        ax.spines['left'].set_color('gray')

        # Get the index values
        x_axis = data.index

        # Remove grid
        ax.grid(False)

        # Disable the top and right axis
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Plot the bands
        ax.plot(x_axis, data['Upper'], color='brown', lw=1, label='Upper', alpha=0.5)
        ax.plot(x_axis, data['Lower'], color='brown', lw=1, label='Lower', alpha=0.5)

        # Plot the closing price and the moving average
        ax.plot(x_axis, data['Close'], color='black', lw=3, label='Close Price', alpha=0.5)
        ax.plot(x_axis, data['SMA'], color='blue', lw=1, label='Simple Moving Average')

        # Add the buy and sell signals
        ax.scatter(x_axis, data['Buy'], label='Buy', alpha=1, color='green', marker='^')
        ax.scatter(x_axis, data['Sell'], label='Sell', alpha=1, color='red', marker='v')

        # Set the title and show the plot
        ax.set_title("Bollinger Bands for {}".format(self.symbol), color='black')
        ax.set_ylabel('USD Price ($)', color='black')
        ax.set_xlabel('Time', color='black')
        plt.xticks(rotation=45, fontsize=7)
        ax.legend(loc='upper left', framealpha=0.2, fancybox=True)
        plt.show()

    def plot_live_graph(self):
        self.fig.suptitle("Price of {} over time".format(self.symbol))

        ani = animation.FuncAnimation(self.fig, self.animate_graph)
        plt.show()

    def animate_graph(self, i):

        # Read file
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))

        # Clear and plot
        self.ax.clear()
        self.ax.plot(file_df['Date'], file_df['Close'], linewidth=3)
        self.ax.plot(file_df['Date'], file_df['Upper'], linewidth=1)
        self.ax.plot(file_df['Date'], file_df['Lower'], linewidth=1)
        self.ax.plot(file_df['Date'], file_df['SMA'], linewidth=1)

        # Draw buy and sell signals
        self.ax.scatter(file_df['Date'], file_df['buy_signal'], marker='^', color='green', alpha=1.0)
        self.ax.scatter(file_df['Date'], file_df['sell_signal'], marker='v', color='red', alpha=1.0)

        # Set labels
        self.ax.set_ylabel("Price of {} in $".format(self.symbol))
        self.ax.xaxis.set_ticks([])

    def execute(self):
        if self.error:
            print('Error occurred')
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

            # Calculate parameters
            self.pre_calculate(self.df)

            # Run the web socket
            t_socket = Thread(target=self.ws.connect_socket)
            t_socket.start()

            # Run the plot's process
            self.p.start()

            # Wait for thread to finish work
            t_socket.join()

        elif self.mode == 'test':

            # Retrieve historical data
            self.retrieve_data()

            # Calculate metrics
            self.pre_calculate(self.hist_df)

            # Get buy and sell signals
            self.hist_df = self.hist_df[self.PERIOD-1:]
            self.hist_df['Buy'] = self.buy_sell_historical(self.hist_df)[0]
            self.hist_df['Sell'] = self.buy_sell_historical(self.hist_df)[1]

            # Plot the graph
            self.plot_hist_graph(self.hist_df)

        # Delete csv file
        file_manager.delete_file('{}.csv'.format(self.symbol), True)
