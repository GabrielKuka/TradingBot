import numpy, talib, websocket, json, threading
import helper.file_manager as file_manager
from multiprocessing import Process
from config import *
from helper.ValidateString import ValidateString
from minute_bar import *
from market import *
from orders import *
from account import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class RSI:

    def __init__(self, bot_mode):

        # RSI Constants
        self.RSI_PERIOD = 14
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70

        if bot_mode == 'active':

            # Setup Plot
            plt.style.use('seaborn')
            self.fig, self.ax = plt.subplots()

            # Create empty file to store price data
            file_manager.create_file('file.csv', 'date,price', True)

            # Tracks auth status
            self.authenticated = False

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

            # Asset to use
            self.symbol = None

            # Enter asset
            self.enter_asset()

            # Run the plot's process
            self.p = Process(target=self.plot_graph)
            self.p.start()

        elif bot_mode == 'test':
            pass

    def execute(self):

        # Cancel existing orders
        self.__orders.cancel_opened_orders()

        # Wait for market to open
        t = threading.Thread(target=self.__market.await_market_open)
        t.start()
        t.join()
        print("[Market Opened]")

        # Start Algo
        self.init_socket()

    def close_position_before_market_close(self):

        # Find how much time till market close
        close_time = self.__market.get_close_time()
        current_time = self.__market.get_current_time()

        till_close = close_time - current_time

        if till_close < (60 * 15):

            # Close positions
            print("Market closing soon.")
            print("[Closing Position].")

            has_position = self.__account.has_position(self.symbol)

            if has_position[0]:
                side = 'sell'

                qty = abs(int(float(has_position[1].qty)))

                t_submit_order = threading.Thread(target=self.__orders.submit_order,
                                                  args=[self.symbol, qty, side])

                t_submit_order.start()
                t_submit_order.join()

            print("[EXITING]")
            exit()

    def enter_asset(self):

        while True:
            asset = input("Enter an asset: ")

            if not ValidateString.is_asset_valid(asset):
                print("Invalid input. Try again.")
            else:
                self.symbol = asset
                break

    def init_socket(self):

        self.ws = websocket.WebSocketApp(SOCKET_URL,
                                         on_message=lambda ws, message: self.on_message(ws, message),
                                         on_close=lambda ws: self.on_close(ws),
                                         on_open=lambda ws: self.on_open(ws)
                                         )
        self.ws.run_forever()

    def calc_rsi(self):

        if len(self.closes) > self.RSI_PERIOD:

            np_closes = numpy.array(self.closes)
            rsi_values = talib.RSI(np_closes, self.RSI_PERIOD)

            rsi_values = list(filter(lambda x: not numpy.isnan(x), rsi_values))

            file_manager.apply_rsi_values("files/rsi.txt", str(rsi_values) + "\n\n")

            last_rsi = rsi_values[-1]

            print("Current RSI: {0}".format(last_rsi))

            if last_rsi > self.RSI_OVERBOUGHT:
                if self.in_position:
                    side = 'sell'

                    t = threading.Thread(target=self.__orders.submit_order(self.symbol, self.QTY, side))
                    t.start()
                    t.join()

                    self.in_position = False
                else:
                    print("Nothing to sell")

            elif last_rsi < self.RSI_OVERSOLD:
                if not self.in_position:
                    side = 'buy'

                    t = threading.Thread(target=self.__orders.submit_order(self.symbol, self.QTY, side))
                    t.start()
                    t.join()

                    self.in_position = True
                else:
                    print("Already own the stock!")
            else:
                print("Nothing to buy or sell.\nAsset's latest RSI is between 30 and 70.")

    def animate_graph(self, i):
        import pandas as pd

        # Read file
        data = pd.read_csv('temp_files/file.csv')

        # Clear and plot
        self.ax.clear()
        self.ax.plot(data['date'], data['price'], linewidth=1)

    def plot_graph(self):
        self.fig.suptitle("Price of {} over time".format(self.symbol))

        self.ax.set_ylabel("Price of {} in $".format(self.symbol))
        self.ax.set_xlabel("Time")

        ani = animation.FuncAnimation(self.fig, self.animate_graph, interval=59)
        plt.show()

    def on_open(self, ws):
        print("[CONNECTION OPENED]")

        # Authenticate
        self.authenticate()

        # Stream something
        self.stream_minute_bars(self.symbol)

    def on_close(self, ws):
        print("[CONNECTION CLOSED]")

        # Close plot if opened
        plt.close(self.fig)

        # Close plot's process if alive
        if self.p is not None:
            self.p.terminate()
            self.p.join()

    def on_message(self, ws, message):
        from datetime import datetime

        # Convert data to a dictionary
        message = json.loads(message)

        # Check authentication
        if not self.authenticated:
            self.check_auth(message)

        # Close position before market close
        self.close_position_before_market_close()

        bar_data = message['data']

        close_price = bar_data['c']
        timestamp = bar_data['e']

        minute_bar = MinuteBar(self.symbol, close_price)
        minute_bar.timestamp = datetime.fromtimestamp(int(str(timestamp)[:-3])).strftime("%H:%M")

        self.closes.append(float(minute_bar.closing_price))

        print('{}\t{}'.format(minute_bar, minute_bar.timestamp))

        self.calc_rsi()

        # Data to save in the temp file
        line = '{},{}'.format(minute_bar.timestamp, minute_bar.closing_price)
        file_manager.append_to_file('file.csv', line, True)

    def authenticate(self):
        auth_data = {
            "action": "authenticate",
            "data": {"key_id": api_key, "secret_key": api_secret}
        }

        self.ws.send(json.dumps(auth_data))

    def check_auth(self, message):

        action = message['stream']
        result = message['data']['status']

        if action == "authorization" and result == "authorized":
            print("[Authenticated]")
            self.authenticated = True
        else:
            print("[UNAUTHORIZED]")
            self.authenticated = False

    def stream_minute_bars(self, symbol):
        listen_message = {"action": "listen", "data": {"streams":
                                                           ["AM.{}".format(symbol)]}}
        self.ws.send(json.dumps(listen_message))
