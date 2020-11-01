import json, websocket
import algorithms.momentum.rsi.rsi_algo as rsi
from minute_bar import MinuteBar
from algorithms.momentum.dual_avg_crossover.dual_avg_crossover import DualAverageCrossover
from algorithms.momentum.mfi import mfi
from config import *
from helper.ValidateString import ValidateString
from account import *
from longshort import *

authenticated = False

ws = None
closes = []
in_position = False

def begin():
    global ws

    print("Welcome!")

#    print(str(Account()))

    handle_mode_command()


def stream_trades(symbol):
    global ws;
    listen_message = {"action": "listen", "data": {"streams": ["T.{}".format(symbol)]}}
    ws.send(json.dumps(listen_message))


def stream_minute_bars(symbol):
    global ws
    listen_message = {"action": "listen", "data": {"streams":
                                                   ["AM.{}".format(symbol)]}}
    ws.send(json.dumps(listen_message))


def handle_mode_command():
    while True:

        print("Enter bot mode: ")
        print("0. Exit\n1. Testing Mode\n2. Action Mode\n")
        mode = input("=> ")

        if mode.isdigit():
            mode = int(mode)

            if mode == 0:

                print("\n[EXITING]")
                exit()

            if mode == 1:

               handle_test_commands()
               break

            elif mode == 2:

               print("Action mode on!")
               ls = LongShort()
               ls.execute()
               break

            else:
                print("Invalid input.\n")
        else:
            print("You can either select 1 or 2.\n")

def handle_test_commands():
    global ws

    while True:
        print("\n[TESTING MODE]\n")
        print("Choose one of the algorithms: ")
        for key in ALGORITHMS:
            print("{0}. {1}".format((key), ALGORITHMS[key]))

        algo = int(input("=> "))

        if algo == 0:
            print("\n[EXITING]\n")
            handle_mode_command()
            break
        if algo == 1:
            # RSI
            print("[Trying to connect...]")
            ws = websocket.WebSocketApp(SOCKET_URL, on_open=on_open,
                                        on_message=on_message, on_close=on_close)
            ws.run_forever()

        elif algo == 2:
            dac = DualAverageCrossover()
            dac.execute()

        elif algo == 3:
            algo = mfi.MoneyFlowIndex()
            algo.execute()


def on_open(ws):
    # Websocket connected
    print("[Connection Opened]")

    # Authenticate user
    authenticate()

    # Ask the user to enter an asset

    while True:
        asset = input("Enter an asset: ")

        if not ValidateString.is_asset_valid(asset):
            print("\n[Asset Not Valid]\n")
            print("1. Asset must be in capital.")
            print("2. Asset must be at most 4 characters.")
        else:
            break

    # Stream something
    stream_minute_bars(asset)


def on_message(ws, message):
    global authenticated

    if not authenticated:
        check_auth(json.loads(message))

    bar_data = json.loads(message)["data"]
    mBar = MinuteBar(bar_data['T'], bar_data['c'])

    closes.append(float(mBar.closing_price))
    print(mBar)

    rsi.calc_rsi(closes, in_position)


def on_close(ws):
    print("\n[Connection Closed]")


def authenticate( ):
    auth_data = {
        "action": "authenticate",
        "data": {"key_id": api_key, "secret_key": api_secret}
    }
    ws.send(json.dumps(auth_data))


def check_auth(message):
    global authenticated

    action = message['stream']
    result = message['data']['status']

    if action == "authorization" and result == "authorized":
        print("[Authenticated]")
        authenticated = True


begin()
