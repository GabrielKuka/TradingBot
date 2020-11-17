# This algorithm uses two bollinger bands to determine when to buy or sell and asset

import json
from multiprocessing import Process
from threading import Thread

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import helper.file_manager as file_manager
import math
from connection.account import Account
from connection.websocket import WebSocket
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

        # Stream minute bars
        self.ws.stream_trades(self.symbol)

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

        # Get the required data: close price
        bar_data = message['data']
        close_price = bar_data['p']
        self.counter += 1

        # Add the received price in the list
        self.closes.append(close_price)

        # Calc metrics
        sma = self.calc_metrics()[0]
        std = self.calc_metrics()[1]
        upper = self.calc_metrics()[2]
        lower = self.calc_metrics()[3]

        if sma == 0 or std == 0 or upper == 0 or lower == 0:
            pass
        else:
            # New entry
            new_entry = {
                'Date': self.counter,
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
            new_entry_str = '{},{},{},{},{},{},{},{}'.format(
                self.counter, close_price,
                new_entry['buy_signal'], new_entry['sell_signal'],
                new_entry['SMA'], new_entry['STD'],
                new_entry['Upper'], new_entry['Lower']
            )
            file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

            # Add entry to dataframe
            self.df = self.df.append(new_entry, ignore_index=True)

            # Print data on the screen
            print('{}\tPrice: ${}\tUpper band: {}\tLower band: {}'.format(
                self.counter, close_price,
                new_entry['Upper'], new_entry['Lower']
            ))

    def calc_metrics(self):
        if len(self.closes) > 20:
            closes = self.closes[-20:]

            # Calc the STD
            sma = sum(closes) / self.PERIOD
            std = self.std(closes, sma)

            # Calc Upper band and lower band
            upper = sma + (2 * std)
            lower = sma - (2 * std)

            return sma, std, upper, lower
        else:
            return 0, 0, 0, 0

    def std(self, data, mean):

        # Square deviations
        deviations = [(x - mean) ** 2 for x in data]

        # Variance
        variance = sum(deviations) / self.PERIOD

        return math.sqrt(variance)

    def __init__(self):

        # Period over which calculations will be made
        self.PERIOD = 20

        # Display header
        display_header()

        # Enter asset
        self.symbol = enter_data()

        self.counter = 0

        self.buy_price = 0

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
        self.QTY = 3000

        # Tracks position status
        self.in_position = False

        # Tracks the close prices
        self.closes = []

        # Init websocket
        self.ws = WebSocket(self)

        # Setup the plot's process
        self.p = Process(target=self.plot_live_graph)

    def buy_sell(self, data):

        if data['Close'] > data['Upper']:
            # Sell!
            print('Sell signal!')
            if self.in_position:
                if data['Close'] - self.buy_price >= 0:
                    # Run thread to submit order
                    t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                    t.start()

                    # Change position status
                    self.in_position = False

                    # Reset previous buy price
                    self.buy_price = 0

                    # Add sell signal
                    data['sell_signal'] = data['Close']

                    t.join()
                else:
                    print('Can\'t sell now. We bought at a higher price.')
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

                # Set the previous buy price
                self.buy_price = data['Close']

                # Add buy signal
                data['buy_signal'] = data['Close']

                t.join()
            else:
                print('Already in position.')

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

    def plot_live_graph(self):
        self.fig.suptitle("Price of {} over time".format(self.symbol))

        ani = animation.FuncAnimation(self.fig, self.animate_graph)
        plt.show()

    def animate_graph(self, i):

        # Read file
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
        if not file_df.empty:
            # Clear and plot
            self.ax.clear()
            self.ax.plot(file_df['Date'], file_df['Close'], alpha=0.5, linewidth=3)
            self.ax.plot(file_df['Date'], file_df['Upper'], alpha=0.5, linewidth=1)
            self.ax.plot(file_df['Date'], file_df['Lower'], alpha=0.5, linewidth=1)
            self.ax.plot(file_df['Date'], file_df['SMA'], alpha=0.5, linewidth=1)

            # Draw buy and sell signals
            self.ax.scatter(file_df['Date'], file_df['buy_signal'], marker='^', color='green', alpha=1.0)
            self.ax.scatter(file_df['Date'], file_df['sell_signal'], marker='v', color='red', alpha=1.0)

            # Set labels
            self.ax.set_ylabel("Price of {} in $".format(self.symbol))
            self.ax.set_xlabel("Time")
            self.ax.tick_params(axis='x', rotation=45)
            plt.xticks(fontsize=5)

    def execute(self):

        # Cancel existing orders
        self.__orders.cancel_opened_orders()

        # Liquidate position if it exists
        self.liquidate_position()

        # Wait for market to open
        t = Thread(target=self.__market.await_market_open)
        t.start()
        t.join()
        print("[Market Opened]")

        # Setup file
        file = open('temp_files/{}.csv'.format(self.symbol), 'w')
        file.write('Date,Close,buy_signal,sell_signal,SMA,STD,Upper,Lower\n')
        file.close()

        # Run the web socket
        t_socket = Thread(target=self.ws.connect_socket)
        t_socket.start()

        # Run the plot's process
        self.p.start()

        # Wait for thread to finish work
        t_socket.join()

        # Delete file
        file_manager.delete_file('SPY.csv'.format(self.symbol))

