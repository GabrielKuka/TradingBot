import pandas as pd, numpy as np, json
from helper import bars
from threading import Thread

from multiprocessing import Process
from helper.ValidateString import ValidateString
from connection.market import *
from connection.orders import *
from connection.account import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import helper.file_manager as file_manager
from interfaces.IAlgorithm import IAlgorithm
from connection.websocket import WebSocket
from helper.CSVReadWrite import CSVReadWrite


def display_header():
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~\n")
    print("Relative Strength Index")
    print("\n~+~+~+~+~+~+~+~+~+~+~+~+~")


class RSI(IAlgorithm):

    def ws_open(self, ws):
        self.ws.on_open(ws)

        # Stream something
        self.ws.stream_trades(self.symbol)

    def ws_close(self, ws):
        self.ws.on_close(ws)

        # Delete csv file
        file_manager.delete_file('temp_files/{}.csv'.format(self.symbol))

        # Close plot's process if alive
        if self.p is not None:
            self.p.terminate()
            self.p.join()

    def ws_message(self, ws, message):
        from datetime import datetime

        # Liquidate position if market is closing soon
        if self.__market.is_market_closing():
            self.close_position_before_market_close()

            # Close graphs
            if self.p is not None:
                self.p.terminate()
                self.p.join()

            return

        # Convert retrieved data to python dict
        msg = json.loads(message)

        self.ws.on_message(ws, msg)

        # Get the required data: close price, time
        bar_data = msg['data']
        close_price = bar_data['p']

        # Append close price to the list
        self.closes.append(close_price)

        # increase counter
        self.counter += 1

        # Calculate the RSI
        rsi = self.calc_rsi()

        # New entry
        new_entry = {
            'Date': self.counter,
            'Close': close_price,
            'RSI': rsi,
            'buy_signal': np.nan,
            'sell_signal': np.nan
        }

        # Get buy or sell signal
        self.buy_sell(new_entry)

        # Add entry to file
        new_entry_str = '{},{},{},{},{}'.format(self.counter, close_price, new_entry['buy_signal'], new_entry['sell_signal'], rsi)
        file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

        # Add entry to dataframe
        self.df = self.df.append(new_entry, ignore_index=True)

        # Print the received data + RSI
        print('{}\tPrice: {}\tRSI: {}'.format(self.counter, close_price, str(rsi)))

    def __init__(self):

        # Show header
        display_header()

        # RSI Constants
        self.RSI_PERIOD = 14
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70

        # In case of any errors
        self.error = False

        # Enter asset
        self.enter_data()

        # Counter when data is received
        self.counter = 0

        # Previous buy price
        self.buy_price = 0

        # Setup Plot
        plt.style.use('seaborn')
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1)

        # Create a dataframe
        self.df = pd.DataFrame()

        # Tracks position status
        self.in_position = False

        # Stores closing prices
        self.closes = []

        # Account Data
        self.__market = Market()
        self.__orders = Orders()
        self.__account = Account()

        # Qty to be bought or sold
        self.QTY = 100

        # Init socket
        self.ws = WebSocket(self)

        # Setup the plot's process
        self.p = Process(target=self.plot_live_graph)


    def buy_sell(self, data):
        if data['RSI'] != 0:
            if data['RSI'] > self.RSI_OVERBOUGHT:
                # Sell
                if self.in_position:
                    if data['Close'] - self.buy_price >= 0:

                        # Run thread to submit order
                        t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                        t.start()

                        # Change the position status
                        self.in_position = False

                        # Add sell signal
                        data['sell_signal'] = data['Close']

                        # Rest buy price
                        self.buy_price = 0

                        t.join()
                    else:
                        print('We bought at a higher price. Can\'t sell now.')
                else:
                    print('Nothing to sell.')
            elif data['RSI'] < self.RSI_OVERSOLD:
                # Buy
                if not self.in_position:
                    # Run thread to submit order
                    t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'buy'])
                    t.start()

                    # Change the position status
                    self.in_position = True

                    # Add buy signal
                    data['buy_signal'] = data['Close']

                    # Add buy price
                    self.buy_price = data['Close']

                    t.join()
                else:
                    print('Nothing to buy. Already in position')

    def close_position_before_market_close(self):

        # Close position
        print("Market closing soon.")

        # Liquidate
        self.liquidate_position()

        print("[EXITING]")
        exit()

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

    def enter_data(self):

        while True:
            asset = input("Enter an asset: ")

            if not ValidateString.is_asset_valid(asset):
                print("Invalid input. Try again.")
            else:
                self.symbol = asset
                break

    def calc_rsi(self):
        if len(self.closes) > 14:
            closes = self.closes[-self.RSI_PERIOD:]

            # Calculate delta
            delta = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

            # Calculate positive and negative values
            up = list(map(lambda x: 0 if x < 0 else x, delta))
            down = list(map(lambda x: 0 if x > 0 else x, delta))

            # Calculate avg gain and losses
            avg_gain = sum(up) / len(up)
            avg_loss = abs(sum(down) / len(down))

            # Calculate the Relative Strength (RS)
            RS = avg_gain / avg_loss

            # Calculate the Relative Strength Index
            RSI = 100.0 - (100.0 / (1.0 + RS))

            return RSI
        else:
            return 0

    def animate_graph(self, i):

        # Read the file and store data to a dataframe
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))

        if not file_df.empty:
            # Clear
            self.ax1.clear()
            self.ax2.clear()

            # Plot
            self.ax1.plot(file_df['Date'], file_df['Close'], linewidth=1)
            self.ax2.plot(file_df['Date'], file_df['RSI'], linewidth=1)

            # Draw buy and sell signals
            self.ax1.scatter(file_df['Date'], file_df['buy_signal'], marker='^', color='green', alpha=1.0)
            self.ax1.scatter(file_df['Date'], file_df['sell_signal'], marker='v', color='red', alpha=1.0)

            # Remove x ticks of prices chart
            self.ax1.set_xticks([])

            # Rotate x ticks of RSI chart
            plt.xticks(rotation=45, fontsize=7)

            # Remove grids
            self.ax1.grid(False)
            self.ax2.grid(False)

            # Add limit lines
            self.ax2.axhline(y=self.RSI_OVERSOLD, linestyle='--', color='green', lw=1)
            self.ax2.axhline(y=self.RSI_OVERBOUGHT, linestyle='--', color='red', lw=1)

            # Set labels
            self.ax1.set_ylabel("Price of {} in $".format(self.symbol))
            self.ax2.set_xlabel("Time")
            self.ax2.set_ylabel('RSI Values')

    def plot_live_graph(self):
        self.fig.suptitle("Price of {} over time".format(self.symbol))

        ani = animation.FuncAnimation(self.fig, self.animate_graph)
        plt.show()

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

        # Create temp file
        file = open('temp_files/{}.csv'.format(self.symbol), 'w')
        file.write('Date,Close,buy_signal,sell_signal,RSI\n')
        file.close()

        # Start Algo
        t_socket = Thread(target=self.ws.connect_socket)
        t_socket.start()

        # Run the plot's process
        self.p.start()

        t_socket.join()

        # Delete csv file
        file_manager.delete_file('SPY.csv'.format(self.symbol), True)