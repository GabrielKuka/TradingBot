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


class RSI(IAlgorithm):

    def ws_open(self, ws):
        self.ws.on_open(ws)

        # Get the last 14 closes
        self.closes = list(self.df['Close'])[-14:]

        # Stream something
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
        close_price = bar_data['c']
        close_time = datetime.fromtimestamp(int(str(bar_data['e'])[:-3])).strftime("%H:%M")

        # Append close price to the list
        self.closes.append(close_price)

        # Calculate the RSI
        rsi = self.calc_rsi()

        # New entry
        new_entry = {
            'Date': close_time,
            'Close': close_price,
            'RSI': rsi,
            'buy_signal': np.nan,
            'sell_signal': np.nan
        }

        # Get buy or sell signal
        self.buy_sell(new_entry)

        # Add entry to file
        new_entry_str = '{},{},{},{},{}'.format(close_time, close_price, new_entry['buy_signal'], new_entry['sell_signal'], rsi)
        file_manager.append_to_file('temp_files/{}.csv'.format(self.symbol), new_entry_str)

        # Add entry to dataframe
        self.df = self.df.append(new_entry, ignore_index=True)

        # Print the received data + RSI
        print('{}\tPrice: {}\tRSI: {}'.format(close_time, close_price, str(rsi)))

    def __init__(self, mode):

        # RSI Constants
        self.RSI_PERIOD = 14
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70

        # Bot mode
        self.mode = mode

        # In case of any errors
        self.error = False

        # Enter asset
        self.enter_data()

        if self.mode == 'active':

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

        elif self.mode == 'test':
            self.hist_df = pd.DataFrame()

    def retrieve_data(self):

        bars_dict = bars.get_historical_data(self.symbol, 50, '1Min')

        if bars_dict:
            # In case no error, write data to a file
            csv_file = CSVReadWrite("temp_files/{}.csv".format(self.symbol),
                                    "Date,Close")
            csv_file.write_file(bars_dict, 't', 'c')

            if self.mode == 'active':
                self.df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.df = self.df.set_index(pd.DatetimeIndex(self.df['Date'].values).strftime("%H:%M"))
                self.df['buy_signal'] = np.nan
                self.df['sell_signal'] = np.nan
            else:
                self.hist_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))
                self.hist_df = self.hist_df.set_index(pd.DatetimeIndex(self.hist_df['Date'].values).strftime("%H:%M"))
        else:
            self.error = True

    def pre_calculate(self, data):

        # Get price difference from the previous days
        delta = data['Close'].diff(1)
        delta = delta.dropna()

        # Get positive and negative values
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0

        # Get the average gain and the average loss
        avg_gain = up.rolling(window=self.RSI_PERIOD).mean()
        avg_loss = abs(down.rolling(window=self.RSI_PERIOD).mean())

        # Calculate the Relative Strength (RS)
        RS = avg_gain / avg_loss

        # Calculate the Relative Strength Index (RSI)
        r_s_i = 100.0 - (100.0 / (1 + RS))

        data['RSI'] = r_s_i

        # Write to file
        data.to_csv(r'temp_files/{}.csv'.format(self.symbol), index=False)

    def buy_sell(self, data):

        if data['RSI'] > self.RSI_OVERBOUGHT:
            # Sell
            if self.in_position:
                # Run thread to submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'sell'])
                t.start()
                t.join()

                # Change the position status
                self.in_position = False

                # Add sell signal
                data['sell_signal'] = data['Close']
            else:
                print('Nothing to sell.')
        elif data['RSI'] < self.RSI_OVERSOLD:
            # Buy
            if not self.in_position:
                # Run thread to submit order
                t = Thread(target=self.__orders.submit_order, args=[self.symbol, self.QTY, 'buy'])
                t.start()
                t.join()

                # Change the position status
                self.in_position = True

                # Add buy signal
                data['buy_signal'] = data['Close']
            else:
                print('Nothing to buy. Already in position')

    def buy_sell_historical(self, data):

        buy_signal = []
        sell_signal = []

        for i in range(len(data['Close'])):
            if data['RSI'][i] > self.RSI_OVERBOUGHT:
                # Sell
                buy_signal.append(np.nan)
                sell_signal.append(data['Close'][i])
            elif data['RSI'][i] < self.RSI_OVERSOLD:
                # Buy
                buy_signal.append(data['Close'][i])
                sell_signal.append(np.nan)
            else:
                buy_signal.append(np.nan)
                sell_signal.append(np.nan)

        return buy_signal, sell_signal

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

    def animate_graph(self, i):

        # Read the file and store data to a dataframe
        file_df = pd.read_csv('temp_files/{}.csv'.format(self.symbol))

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

        ani = animation.FuncAnimation(self.fig, self.animate_graph, interval=600)
        plt.show()

    def plot_hist_graph(self, data):
        plt.style.use('fivethirtyeight')
        fig, (ax1, ax2) = plt.subplots(2, 1, facecolor='black')

        fig.suptitle('RSI Algorithm', color='white')

        # Set the background color
        ax1.set_facecolor('black')
        ax2.set_facecolor('black')

        # Set axis values colors
        ax1.tick_params(axis='x', colors='white')
        ax1.tick_params(axis='y', colors='white')
        ax2.tick_params(axis='x', colors='white')
        ax2.tick_params(axis='y', colors='white')

        # Change the color of the left and bottom axis
        ax1.spines['bottom'].set_color('gray')
        ax1.spines['left'].set_color('gray')
        ax2.spines['bottom'].set_color('gray')
        ax2.spines['left'].set_color('gray')

        # Remove grids
        ax1.grid(False)
        ax2.grid(False)

        # Disable the top and right axis
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)

        # Plot the closing prices and RSI
        ax1.plot(data.index, data['Close'], color='blue', lw=2, label='Closing Prices', alpha=0.5)
        ax2.plot(data.index, data['RSI'], color='green', lw=2, label='RSI', alpha=1.0)

        # Draw the buy and sell signals
        ax1.scatter(data.index, data['Buy'], color='green', marker='^', alpha=1.0)
        ax1.scatter(data.index, data['Sell'], color='red', marker='v', alpha=1.0)

        # Draw the limit lines
        ax2.axhline(y=self.RSI_OVERSOLD, lw=2, linestyle='--', color='green')
        ax2.axhline(y=self.RSI_OVERBOUGHT, lw=2, linestyle='--', color='red')

        # Set titles and labels
        ax1.set_ylabel('Closing Prices for {} in USD'.format(self.symbol), color='white')
        ax2.set_ylabel('RSI Values', color='white')
        ax2.set_xlabel('Time', color='white')

        # Show the legends on both plots
        ax1.legend(loc='upper left', framealpha=0.2, fancybox=True)
        ax2.legend(loc='upper left', framealpha=0.2)

        # Rotate x ticks
        plt.xticks(rotation=45, fontsize=7)

        ax1.set_xticks([])

        # Show the plots
        plt.show()

    def execute(self):

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

            # Retrieve Data
            self.retrieve_data()

            # Calculate Metric
            self.pre_calculate(self.df)

            # Start Algo
            t_socket = Thread(target=self.ws.connect_socket)
            t_socket.start()

            # Run the plot's process
            self.p.start()

            t_socket.join()

        elif self.mode == 'test':

            # Retrieve historical data
            self.retrieve_data()

            # Calculate metric
            self.pre_calculate(self.hist_df)

            # Get buy and sell signals
            self.hist_df = self.hist_df[self.RSI_PERIOD - 1:]
            self.hist_df['Buy'] = self.buy_sell_historical(self.hist_df)[0]
            self.hist_df['Sell'] = self.buy_sell_historical(self.hist_df)[1]

            # Plot the graph
            self.plot_hist_graph(self.hist_df)

        else:
            print('Weird!')
