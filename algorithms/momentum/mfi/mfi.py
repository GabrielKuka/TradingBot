# This python script calculates the Money Flow Index for a particular asset


import warnings, bars, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from helper.CSVReadWrite import CSVReadWrite

warnings.filterwarnings('ignore')

class MoneyFlowIndex:

    def __init__(self, period = 14, high = 80, low = 20):
        '''Period - HIGH - LOW'''

        self.error = False

        self.display_header()

        # Assign variables
        self.symbol, self.days = self.input_data()

        self.period = period
        self.high = high
        self.low = low

        print("[Requesting Data]")
        bars_dict = bars.get_historical_data(self.symbol, self.days, 'day')

        if bars_dict != False:

            # In case no error, write data to a file
            csvfile = CSVReadWrite("data/ohlc/{}.csv".format(self.symbol),
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

            if not self.is_asset_valid(asset):
                print("\n[Asset Not Valid]\n")
                print("1. Asset must be in capital.")
                print("2. Asset must be at most 4 characters.")
            else:
                break

        while True:
            days = input("Days in the past to retrieve data => ")

            if not self.are_days_valid(days):
                print("\n[Value Not Valid]\n")
                print("1. Days must be from 50 - 1000")
            else:
                break

        return asset, days


    def is_asset_valid(self, asset):
        return bool(re.match("[A-Z]{1,4}", asset))


    def are_days_valid(self, days):
        if days.isdigit() and 50 <= int(days) <= 1000:
            return True
        else:
            return False


    def setup_dataframes(self):
        print('[Setting up dataframes]')

        # Get the data
        self.bars_df = pd.read_csv("data/ohlc/{}.csv".format(self.symbol))

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

            if self.typical_price[i] > self.typical_price[i-1]:
                positive_flows.append(self.raw_money_flow[i-1])
                negative_flows.append(0)
            elif self.typical_price[i] < self.typical_price[i-1]:
                positive_flows.append(0)
                negative_flows.append(self.raw_money_flow[i-1])
            else:
                positive_flows.append(0)
                negative_flows.append(0)

        # Sum them up
        for i in range(self.period - 1, len(positive_flows)):
           self.positive_mf.append(sum(positive_flows[i+1-self.period:i+1]))

        for i in range(self.period - 1, len(negative_flows)):
           self.negative_mf.append(sum(negative_flows[i+1-self.period:i+1]))


    # Calculate the money flow index
    def find_mfi(self):
        mfi = 100 * ( np.array(self.positive_mf) / ( np.array(self.positive_mf)
                                                   + np.array(self.negative_mf)) )
        return mfi


    def add_mfi(self):
        self.mfi_df = pd.DataFrame()
        self.mfi_df['MFI'] = self.find_mfi()


    def get_signal(self):

        print('[Executing Algo]')

        # Create a new dataframe
        final_df = pd.DataFrame()
        final_df = self.bars_df[self.period:]
        final_df['MFI'] = self.find_mfi()

        # Store buy and sell signals
        buy_signal = []
        sell_signal = []

        for i in range(len(final_df['MFI'])):

            if final_df['MFI'][i] > self.high:
                buy_signal.append(np.nan)
                sell_signal.append(final_df['Close'][i])
            elif final_df['MFI'][i] < self.low:
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
        plt.figure(figsize=(12.2, 4.5))
        plt.plot(data['Close'], label="Close Price", alpha=0.5)
        plt.scatter(data.index, data['Buy'], color="green",
                    label="Buy Signal", marker="^", alpha=1)
        plt.scatter(data.index, data['Sell'], color="red",
                    label="Sell signal", marker="v", alpha=1)
        plt.title("{} Close Price".format(self.symbol))
        plt.xlabel("Date")
        plt.ylabel("Close Price USD ($)")
        plt.legend(loc='upper left')
        plt.show()


    def execute(self):

        if self.error == True:
            return

        self.setup_dataframes()
        self.pre_calculations()
        self.find_flows()
        self.add_mfi()

        data = self.get_signal()
        self.visualize_data(data)
