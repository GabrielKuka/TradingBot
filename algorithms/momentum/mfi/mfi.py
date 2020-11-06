# This python script calculates the Money Flow Index for a particular asset

import warnings, bars
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from helper.CSVReadWrite import CSVReadWrite
from helper.ValidateString import ValidateString

warnings.filterwarnings('ignore')


class MoneyFlowIndex:

    def __init__(self, period=14, high=80, low=20):
        """Period - HIGH - LOW"""

        self.error = False

        self.display_header()

        # Assign variables
        self.symbol, self.days = self.input_data()

        self.PERIOD = period
        self.HIGH = high
        self.LOW = low
        self.MFI_MARGIN = 3

        print("[Requesting Data]")
        bars_dict = bars.get_historical_data(self.symbol, self.days, 'day')

        if bars_dict != False:

            # In case no error, write data to a file
            csvfile = CSVReadWrite("files/ohlc/{}.csv".format(self.symbol),
                                   "Date,Open,High,Low,Close,Volume")
            csvfile.write_file(bars_dict, 't', 'o', 'h', 'l', 'c', 'v')

        else:
            self.error = True

    def display_header(self):
        print("\n\t\t\t~+~+~+~+~+~+~+~+~+~+~+~+~\n")
        print("\t\t Money Flow Index Algorithm")
        print("\n\t\t\t~+~+~+~+~+~+~+~+~+~+~+~+~")

    def input_data(self):
        asset, days = None, None

        while True:
            asset = input("Enter asset => ")

            if not ValidateString.is_asset_valid(asset):
                print("\n[Asset Not Valid]\n")
                print("1. Asset must be in capital.")
                print("2. Asset must be at most 4 characters.")
            else:
                break

        while True:
            days = input("Days in the past to retrieve data => ")

            if not ValidateString.are_days_valid(days):
                print("\n[Value Not Valid]\n")
                print("1. Days must be from 50 - 1000")
            else:
                break

        return asset, days

    def setup_dataframes(self):
        print('[Setting up dataframes]')

        # Get the data
        self.bars_df = pd.read_csv("files/ohlc/{}.csv".format(self.symbol))

        # Set the index
        self.bars_df = self.bars_df.set_index(pd.DatetimeIndex(self.bars_df['Date'].values));

    def pre_calculations(self):

        # Calculate the Typical price
        self.typical_price = (self.bars_df['High'] + self.bars_df['Low'] +
                              self.bars_df['Close']) / 3

        # Calculate the Raw Money Flow
        self.raw_money_flow = self.typical_price * self.bars_df['Volume']

    def find_flows(self):

        # Store the (+) and (-) money flows for each day
        positive_flows = []
        negative_flows = []

        # Store the sum of each flow
        self.positive_mf = []
        self.negative_mf = []

        # Calculate the (+) and (-) money flows
        for i in range(1, len(self.typical_price)):

            if self.typical_price[i] > self.typical_price[i - 1]:
                positive_flows.append(self.raw_money_flow[i - 1])
                negative_flows.append(0)
            elif self.typical_price[i] < self.typical_price[i - 1]:
                positive_flows.append(0)
                negative_flows.append(self.raw_money_flow[i - 1])
            else:
                positive_flows.append(0)
                negative_flows.append(0)

        # Sum them up
        for i in range(self.PERIOD - 1, len(positive_flows)):
            self.positive_mf.append(sum(positive_flows[i + 1 - self.PERIOD:i + 1]))

        for i in range(self.PERIOD - 1, len(negative_flows)):
            self.negative_mf.append(sum(negative_flows[i + 1 - self.PERIOD:i + 1]))

    # Calculate the money flow index
    def find_mfi(self):
        mfi = 100 * (np.array(self.positive_mf) / (np.array(self.positive_mf)
                                                   + np.array(self.negative_mf)))
        return mfi

    def add_mfi(self):
        self.mfi_df = pd.DataFrame()
        self.mfi_df['MFI'] = self.find_mfi()

    def get_signal(self):

        print('[Executing Algo]')

        # Create a new dataframe
        final_df = self.bars_df[self.PERIOD:]
        final_df['MFI'] = self.find_mfi()

        # Store buy and sell signals
        buy_signal = []
        sell_signal = []

        for i in range(len(final_df['MFI'])):

            if final_df['MFI'][i] > self.HIGH - self.MFI_MARGIN:
                buy_signal.append(np.nan)
                sell_signal.append(final_df['Close'][i])
            elif final_df['MFI'][i] < self.LOW + self.MFI_MARGIN:
                buy_signal.append(final_df['Close'][i])
                sell_signal.append(np.nan)
            else:
                buy_signal.append(np.nan)
                sell_signal.append(np.nan)

        final_df['Buy'] = buy_signal
        final_df['Sell'] = sell_signal

        return final_df

    def visualize_data(self, data):
        print('[Drawing Graph]')

        plt.style.use("fivethirtyeight")
        fig, (ax1, ax2) = plt.subplots(2, 1, facecolor='black')

        fig.suptitle('Money Flow Index', color='white')

        # Set background color
        ax1.set_facecolor('black')
        ax2.set_facecolor('black')

        # Set axis values colors
        ax1.tick_params(axis='x', colors='white')
        ax1.tick_params(axis='y', colors='white')
        ax2.tick_params(axis='x', colors='white')
        ax2.tick_params(axis='y', colors='white')

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

        # Plot asset prices
        ax1.plot(data['Close'], color='yellow', label="Close Price", alpha=0.5, linewidth=2)

        # Draw buy and sell signals
        ax1.scatter(data.index, data['Buy'], color="green",
                    label="Buy Signal", marker="^", alpha=1)
        ax1.scatter(data.index, data['Sell'], color="red",
                    label="Sell signal", marker="v", alpha=1)

        ax1.legend(loc='upper left')

        # Plot asset MFI and draw limit lines
        ax2.axhline(10, color='red', linestyle='--', linewidth=2)
        ax2.axhline(20, color='green', linestyle='--', linewidth=2)
        ax2.axhline(80, color='green', linestyle='--', linewidth=2)
        ax2.axhline(90, color='red', linestyle='--', linewidth=2)
        ax2.axhline(y=(self.LOW + self.MFI_MARGIN), color='yellow', linestyle='--', linewidth=1)
        ax2.axhline(y=(self.HIGH - self.MFI_MARGIN), color='yellow', linestyle='--', linewidth=1)

        ax2.plot(self.mfi_df['MFI'], label='MFI', linewidth=2)

        plt.show()

    def execute(self):

        if self.error:
            return

        self.setup_dataframes()
        self.pre_calculations()
        self.find_flows()
        self.add_mfi()

        data = self.get_signal()
        self.visualize_data(data)
