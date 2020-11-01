# This algorithms uses the dual average crossover to determine when to buy and

# when to sell.

from helper.CSVReadWrite import CSVReadWrite
import re, bars, asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from time import perf_counter
from datetime import datetime
from interfaces.IMomentumAlgo import IMomentumAlgo
from helper.ValidateString import ValidateString


class DualAverageCrossover(IMomentumAlgo):

    def __init__(self):

        self.error = False

        self.display_header()

        self.symbol, self.days = self.input_data()

        # Retrieve bars from API
        print("[Requesting Data]")
        bars_dict = bars.get_historical_data(self.symbol, self.days, 'day')

        if bars_dict != False:

            # Save the data into a file
            csvfile = CSVReadWrite("files/ohlc/{}.csv".format(self.symbol), "Date,Open,High,Low,Close")
            csvfile.write_file(bars_dict, 't', 'o', 'h', 'l', 'c')

            # Read the file
            self.bars_df = pd.read_csv("files/ohlc/{}.csv".format(self.symbol))
        else:
            self.error = True


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
            days = input("Days in the past to retrieve data [30 - 1000] => ")
            if not ValidateString.are_days_valid(days):
                print("\n[Value Not Valid]\n")
                print("1. Days must be from 30 - 1000.")
            else:
                break

        return asset, days



    def display_header(self):
        print("\n\t\t\t~+~+~+~+~+~+~+~+~+~+~+~+~\n")
        print("\t\tDual Simple Average Crossover Algorithm")
        print("\n\t\t\t~+~+~+~+~+~+~+~+~+~+~+~+~")
        print("\nChoose an asset that hasn't been split or reverse split.\n")


    def setup_dataframes(self):
        print("[Setting up dataframes]")

        # Create a SMA with 30 day window
        sma30_df = pd.DataFrame()
        sma30_df['Close'] = self.bars_df['Close'].rolling(window=30).mean()

        # Create a SMA with 100 day window
        sma100_df = pd.DataFrame()
        sma100_df['Close'] = self.bars_df['Close'].rolling(window=100).mean()

        # Create a new dataframe to store all the data
        data = pd.DataFrame()
        data[self.symbol] = self.bars_df['Close']
        data['SMA30'] = sma30_df['Close']
        data['SMA100'] = sma100_df['Close']

        return data


    # Create a signal for when to buy/sell the stock
    def buy_sell(self):
        data = self.setup_dataframes()

        print("[Executing Algo]")

        sigPriceSell = []
        sigPriceBuy = []
        crossed = -1

        for i in range(len(data)):
            if data['SMA30'][i] > data['SMA100'][i]:
                if crossed != 1:
                    sigPriceBuy.append(data[self.symbol][i])
                    sigPriceSell.append(np.nan)
                    crossed = 1
                else:
                    sigPriceBuy.append(np.nan)
                    sigPriceSell.append(np.nan)

            elif data['SMA30'][i] < data['SMA100'][i] and crossed == 1:
                if crossed != 0:
                    sigPriceBuy.append(np.nan)
                    sigPriceSell.append(data[self.symbol][i])
                    crossed = 0
                else:
                    sigPriceBuy.append(np.nan)
                    sigPriceSell.append(np.nan)

            else:
                sigPriceBuy.append(np.nan)
                sigPriceSell.append(np.nan)

        return (sigPriceBuy, sigPriceSell), data


    def visualize_data(self, data):
        print("[Drawing Graph]")

        plt.style.use("fivethirtyeight")

        plt.figure(figsize=(12.5, 4.5))
        plt.plot(data[self.symbol], label=self.symbol, alpha=0.4)
        plt.plot(data['SMA30'], label='SMA30', alpha=0.4)
        plt.plot(data['SMA100'], label='SMA100', alpha=0.4)
        plt.scatter(data.index, data['Buy_Signal_Price'], label='Buy', marker='^',
                    color='green')
        plt.scatter(data.index, data['Sell_Signal_Price'], label='Sell', marker='v',
                    color='red')
        plt.ylabel("Close Price in USD ($)")
        plt.title("{} Close Price History Buy and Sell Signals".format(self.symbol))
        plt.legend(loc='upper left')
        plt.show()



    def execute(self):

        if self.error == True:
            return
        t_start = perf_counter()
        # Store the buy and sell data into a variable
        buy_sell, data = self.buy_sell()
        data['Buy_Signal_Price'] = buy_sell[0]
        data['Sell_Signal_Price'] = buy_sell[1]

        t_stop = perf_counter()
        print("Executed in {}".format(str(t_stop-t_start)))


        # Vizualize the data!
        self.visualize_data(data)



