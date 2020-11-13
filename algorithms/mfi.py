# This python script calculates the Money Flow Index for a particular asset

import json
from helper import bars
import warnings

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from interfaces.IAlgorithm import IAlgorithm
from connection.websocket import WebSocket
import numpy as np
import pandas as pd
import helper.file_manager as file_manager
from datetime import datetime

from helper.CSVReadWrite import CSVReadWrite
from helper.ValidateString import ValidateString
from threading import Thread
from multiprocessing import Process
from connection.account import Account
from connection.orders import Orders
from connection.market import Market

warnings.filterwarnings('ignore')


class MoneyFlowIndex(IAlgorithm):

    def ws_open(self, ws):
        self.ws.on_open(ws)

        # Stream minute bars
        self.ws.stream_minute_bars(self.symbol)

    def ws_close(self, ws):
        self.ws.on_close(ws)

        # Delete csv file
        file_manager.delete_file('temp_files/{}.csv'.format(self.symbol))

        # Close plot's process if alive
        if self.p is not None:
            self.p.terminate()
            self.p.join()

    def ws_message(self, ws, message):
        # Liquidate position if market is closing soon
        if self.__market.is_market_closing():
            self.close_position_before_market_close()

            # Close graphs
            if self.p is not None:
                self.p.terminate()
                self.p.join()

            return

        # Convert retrieved data to python dict
        message = json.loads(message)

        self.ws.on_message(ws, message)

        # Get the required data: close price, high, low, volume, time
        bar_data = message['data']
        close_price = round(bar_data['c'], 2)
        close_time = datetime.fromtimestamp(int(str(bar_data['e'])[:-3])).strftime("%H:%M")
        high_price = round(bar_data['h'], 2)
        low_price = round(bar_data['l'], 2)
        volume = bar_data['v']

        # Calc MFI
        mfi = self.calc_mfi(self.df[-14:])

        # New Entry
        new_entry = {
            'Date': close_time,
            'Close': close_price,
            'High': high_price,
            'Low': low_price,
            'Volume': volume,
            'buy_signal': np.nan,
            'sell_signal': np.nan,
            'MFI': mfi
        }

        # Get buy or sell signal
        self.buy_sell(new_entry)

        # Add Entry to file
        new_entry_str = '{},{},{},{},{},{},{},{}'.format(
            close_time, close_price,
            new_entry['High'], new_entry['Low'],
            new_entry['Volume'],
            new_entry['buy_signal'],
            new_entry['sell_signal'],
            mfi
        )
        file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

        # Add entry to dataframe
        self.df = self.df.append(new_entry, ignore_index=True)

        # Print retrieved data + MFI
        print('{}\t{}\tMFI: {}'.format(close_time, close_price, mfi))

    def __init__(self, mode):

        # In case of any errors
        self.error = False

        # Display Header
        self.display_header()

        # Bot mode
        self.mode = mode

        # Constants
        self.PERIOD = 14
        self.HIGH = 80
        self.LOW = 20
        self.MFI_MARGIN = 3

        # Assign variables
        self.symbol = self.enter_data()

        if self.mode == 'active':
            # Setup Plot
            plt.style.use('seaborn')
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1)

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

            # Init websocket
            self.ws = WebSocket(self)

            # Setup the plot's process
            self.p = Process(target=self.plot_live_graph)
        elif self.mode == 'test':
            self.hist_df = pd.DataFrame()
            self.mfi = None
        else:
            print('Weird')

    def retrieve_data(self):

        print("[Requesting Data]")
        bars_dict = bars.get_historical_data(self.symbol, 70, '1Min')

        if bars_dict:
            # In case no error, write data to a file
            csv_file = CSVReadWrite("temp_files/{}.csv".format(self.symbol),
                                    "Date,Close,High,Low,Volume")
            csv_file.write_file(bars_dict, 't', 'c', 'h', 'l', 'v')

            if self.mode == 'active':
                self.df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.df = self.df.set_index(pd.DatetimeIndex(self.df['Date'].values).strftime("%H:%M"))
                self.df['buy_signal'] = np.nan
                self.df['sell_signal'] = np.nan
            else:
                # Get the data
                self.hist_df = pd.read_csv("temp_files/{}.csv".format(self.symbol))
                self.hist_df = self.hist_df.set_index(pd.DatetimeIndex(self.hist_df['Date'].values).strftime("%H:%M"))
        else:
            self.error = True

    def display_header(self):
        print("\n~+~+~+~+~+~+~+~+~+~+~+~+~\n")
        print("Money Flow Index Algorithm")
        print("\n~+~+~+~+~+~+~+~+~+~+~+~+~")

    def calc_mfi(self, data):
        # Calc typical price
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3

        # Calc Raw Money flow
        raw_money_flow = typical_price * data['Volume']

        # Store the flows
        positive_flows = []
        negative_flows = []

        # Calculate the (+) and (-) money flows
        for i in range(1, len(typical_price)):

            if typical_price[i] > typical_price[i - 1]:
                positive_flows.append(raw_money_flow[i - 1])
                negative_flows.append(0)
            elif typical_price[i] < typical_price[i - 1]:
                positive_flows.append(0)
                negative_flows.append(raw_money_flow[i - 1])
            else:
                positive_flows.append(0)
                negative_flows.append(0)

        # Sum them up
        positive_flows_sum = sum(positive_flows)
        negative_flows_sum = sum(negative_flows)

        # Money Flow Ratio
        mfr = positive_flows_sum / negative_flows_sum

        # Calculate the Money Flow Index
        money_flow_index = 100 - (100 / (1 + mfr))

        return money_flow_index

    def enter_data(self):
        asset, days = None, None

        while True:
            asset = input("Enter asset => ")

            if not ValidateString.is_asset_valid(asset):
                print("\n[Asset Not Valid]\n")
                print("1. Asset must be in capital.")
                print("2. Asset must be at most 4 characters.")
            else:
                break

        # while True:
        #     days = input("Days in the past to retrieve data => ")
        #
        #     if not ValidateString.are_days_valid(days):
        #         print("\n[Value Not Valid]\n")
        #         print("1. Days must be from 50 - 1000")
        #     else:
        #         break

        return asset

    def pre_calculate(self, data):

        # Calc typical price
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3

        # Calc Raw Money Flows
        rmf = typical_price * data['Volume']

        # Calc + and - flows
        positive_flows = []
        negative_flows = []

        for i in range(1, len(typical_price)):
            if typical_price[i] > typical_price[i - 1]:
                positive_flows.append(rmf[i-1])
                negative_flows.append(0)
            elif typical_price[i] < typical_price[i - 1]:
                positive_flows.append(0)
                negative_flows.append(rmf[i-1])
            else:
                positive_flows.append(0)
                negative_flows.append(0)

        # Calc the sums of money flows within the time period
        positive_mf_sum = []
        negative_mf_sum = []

        for i in range(self.PERIOD - 1, len(positive_flows)):
            positive_mf_sum.append(sum(positive_flows[i+1-self.PERIOD:i+1]))

        for i in range(self.PERIOD - 1, len(negative_flows)):
            negative_mf_sum.append(sum(negative_flows[i+1-self.PERIOD:i+1]))

        self.mfi = 100 * (np.array(positive_mf_sum) / (np.array(negative_mf_sum) + np.array(positive_mf_sum)))

        data['MFI'] = np.nan
        data['MFI'][14:] = self.mfi

        data.to_csv(r'temp_files/{}.csv'.format(self.symbol), index=False)

    def buy_sell(self, data):

        if data['MFI'] > self.HIGH - self.MFI_MARGIN:
            # Sell
            if self.in_position:
                # Submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                t.start()
                t.join()

                # Change position status
                self.in_position = False

                # Add sell signal
                data['sell_signal'] = data['Close']
            else:
                print('Sell signal generated. No asset to sell.')

        elif data['MFI'] < self.LOW + self.MFI_MARGIN:
            # Buy
            if not self.in_position:
                # Submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'buy'])
                t.start()
                t.join()

                # Change position status
                self.in_position = True

                # Add buy signal
                data['buy_signal'] = data['Close']
            else:
                print('Buy signal generated. Already in position.')

    def close_position_before_market_close(self):
        # Close position
        print("Market closing soon.")

        # Liquidate
        self.liquidate_position()

        print("[EXITING]")

    def liquidate_position(self):
        has_position = self.__account.has_position(self.symbol)

        if has_position[0]:
            print("[Liquidating]")

            side = 'sell'
            qty = abs(int(float(has_position[1].qty)))

            t = Thread(target=self.__orders.submit_order, args=[self.symbol, qty, side])
            t.start()
            t.join()

    def buy_sell_historical(self, data):
        # Store buy and sell signals
        buy_signal = []
        sell_signal = []

        for i in range(len(data['MFI'])):

            if data['MFI'][i] > self.HIGH - self.MFI_MARGIN:
                buy_signal.append(np.nan)
                sell_signal.append(data['Close'][i])
            elif data['MFI'][i] < self.LOW + self.MFI_MARGIN:
                buy_signal.append(data['Close'][i])
                sell_signal.append(np.nan)
            else:
                buy_signal.append(np.nan)
                sell_signal.append(np.nan)

        return buy_signal, sell_signal

    def plot_hist_graph(self, data):
        print('[Drawing Graph]')

        plt.style.use("fivethirtyeight")
        fig, (ax1, ax2) = plt.subplots(2, 1, facecolor='black')

        fig.suptitle('Money Flow Index', color='white')

        # Set background color
        ax1.set_facecolor('black')
        ax2.set_facecolor('black')

        # Set axis values colors
        ax1.tick_params(axis='y', colors='white')
        ax2.tick_params(axis='y', colors='white')
        ax2.tick_params(axis='x', colors='white')

        # Remove x ticks of the second chart
        ax1.xaxis.set_ticks([])

        # Set labels for axis
        ax1.set_ylabel('{} price in $ (USD)'.format(self.symbol), color='white')
        ax2.set_ylabel('MFI Values', color='white')

        # Remove grids
        ax1.grid(False)
        ax2.grid(False)

        # Disable the top and right axis
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)

        # Change the color of the left and bottom axis
        ax1.spines['bottom'].set_color('gray')
        ax1.spines['left'].set_color('gray')
        ax2.spines['bottom'].set_color('black')
        ax2.spines['left'].set_color('black')

        # Plot prices and MFI
        ax1.plot(data.index, data['Close'], color='yellow', label="Close Price", alpha=0.5, linewidth=2)
        ax2.plot(data.index, data['MFI'], label='MFI', linewidth=2)

        # Draw buy and sell signals
        ax1.scatter(data.index, data['Buy'], color="green",
                    label="Buy Signal", marker="^", alpha=1)
        ax1.scatter(data.index, data['Sell'], color="red",
                    label="Sell signal", marker="v", alpha=1)

        # Draw limit lines
        ax2.axhline(10, color='red', linestyle='--', linewidth=2)
        ax2.axhline(20, color='green', linestyle='--', linewidth=2)
        ax2.axhline(80, color='green', linestyle='--', linewidth=2)
        ax2.axhline(90, color='red', linestyle='--', linewidth=2)
        ax2.axhline(y=(self.LOW + self.MFI_MARGIN), color='yellow', linestyle='--', linewidth=1)
        ax2.axhline(y=(self.HIGH - self.MFI_MARGIN), color='yellow', linestyle='--', linewidth=1)

        # Show legend
        ax1.legend(loc='upper left')

        # Rotate x axis values
        plt.xticks(rotation=45, fontsize=5)

        # Shot plot
        plt.show()

    def plot_live_graph(self):
        self.fig.suptitle('Price of {} over time'.format(self.symbol))

        ani = animation.FuncAnimation(self.fig, self.animate_graph)
        plt.show()

    def animate_graph(self, i):
        # Read file
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))

        # Clear and plot
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.plot(file_df['Date'], file_df['Close'], color='orange', lw=3, alpha=0.7)
        self.ax2.plot(file_df['Date'], file_df['MFI'], color='black', lw=3, alpha=1.0)

        # Draw buy and sell signals
        self.ax1.scatter(file_df['Date'], file_df['buy_signal'], color='green', alpha=1.0, marker='^')
        self.ax1.scatter(file_df['Date'], file_df['sell_signal'], color='red', alpha=1.0, marker='v')

        # Draw horizontal limit lines
        self.ax2.axhline(y=self.HIGH, color='red', linestyle='--')
        self.ax2.axhline(y=self.LOW, color='green', linestyle='--')
        self.ax2.axhline(y=(self.HIGH - self.MFI_MARGIN), color='brown', linestyle='--')
        self.ax2.axhline(y=(self.LOW + self.MFI_MARGIN), color='brown', linestyle='--')

        # Remove x ticks of prices chart
        self.ax1.set_xticks([])

        # Rotate x ticks of RSI chart
        plt.xticks(rotation=45, fontsize=7)

        # Remove grids
        self.ax1.grid(False)
        self.ax2.grid(False)

        # Set labels
        self.ax1.set_ylabel("Price of {} in $".format(self.symbol))
        self.ax2.set_xlabel("Time")
        self.ax2.set_ylabel('MFI Values')

    def execute(self):

        if self.error:
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

            # Run socket in a thread
            t_socket = Thread(target=self.ws.connect_socket)
            t_socket.start()

            # Run the plot's process
            self.p.start()

            # Wait for socket to finish
            t_socket.join()
        elif self.mode == 'test':

            # Retrieve historical data
            self.retrieve_data()

            # Calculate metrics
            self.pre_calculate(self.hist_df)

            # Get buy and sell signals
            self.hist_df = self.hist_df[self.PERIOD:]
            self.hist_df['MFI'] = self.mfi
            self.hist_df['Buy'] = self.buy_sell_historical(self.hist_df)[0]
            self.hist_df['Sell'] = self.buy_sell_historical(self.hist_df)[1]

            # Plot historical graph
            self.plot_hist_graph(self.hist_df)

            # Delete the file
            file_manager.delete_file('SPY.csv'.format(self.symbol))

