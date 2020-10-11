import json, websocket
import algorithms.momentum.rsi.rsi_algo as rsi
from minute_bar import MinuteBar
from algorithms.momentum.dual_avg_crossover.dual_avg_crossover import DualAverageCrossover
from config import *


authenticated = False

ws = None
closes = []
in_position = False
algorithms = {1:'RSI', 2:'Dual Average CrossOver'}

def begin( ):
    global ws
    handle_command()


def stream_trades(symbol):
    global ws;
    listen_message = {"action": "listen", "data": {"streams": ["T.{}".format(symbol)]}}
    ws.send(json.dumps(listen_message))


def stream_minute_bars(symbol):
    global ws
    listen_message = {"action": "listen", "data": {"streams":
                                                   ["AM.{}".format(symbol)]}}
    ws.send(json.dumps(listen_message))


def handle_command():
    global algorithms, ws

    for key in algorithms:
        print("{0}. {1}".format((key), algorithms[key]))

    algo = int(input("Choose one of the algorithms => "))

    if algo == 1:
        # RSI
        print("[Trying to connect...]")
        ws = websocket.WebSocketApp(socket, on_open=on_open,
                                    on_message=on_message, on_close=on_close)
        ws.run_forever()
        ws.close()

    elif algo == 2:
        dac = DualAverageCrossover()
        dac.execute()


def on_open(ws):
    # Websocket connected
    print("[Connection Opened]")

    # Authenticate user
    authenticate()

    # Stream something
    #stream_minute_bars(asset)


def on_message(ws, message):
    global authenticated

    if not authenticated:
        check_auth(json.loads(message))

#    bar_data = json.loads(message)["data"]
#    mBar = MinuteBar(bar_data['T'], bar_data['c'])
#
#    closes.append(float(mBar.closing_price))
#    print(mBar)
#
#    rsi.calc_rsi(closes, in_position)


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
