import json, websocket
from config import *


class WebSocket:

    def __init__(self, i_algo):

        # Keeps track of auth status
        self.__authenticated = False

        # Setup websocket
        self.__ws = websocket.WebSocketApp(SOCKET_URL,
                                           on_open=lambda ws: i_algo.ws_open(ws),
                                           on_close=lambda ws: i_algo.ws_close(ws),
                                           on_message=lambda ws, message: i_algo.ws_message(ws, message)
                                           )

    def connect_socket(self):
        self.__ws.run_forever()

    def disconnect_socket(self):
        self.__ws.close()

    def on_open(self, ws):
        print("[CONNECTION OPENED]")

        # Authenticate
        self.authenticate()

    def on_close(self, ws):
        print('[CONNECTION CLOSED]')

    def on_message(self, ws, message):
        # Check authentication
        if not self.__authenticated:
            self.check_auth(message)

    def authenticate(self):
        auth_data = {
            "action": "authenticate",
            "data": {"key_id": api_key, "secret_key": api_secret}
        }

        self.__ws.send(json.dumps(auth_data))

    def check_auth(self, message):

        action = message['stream']
        result = message['data']['status']

        if action == "authorization" and result == "authorized":
            print("[Authenticated]")
            self.__authenticated = True
        else:
            print("[UNAUTHORIZED]")
            self.__authenticated = False

    def stream_minute_bars(self, symbol):
        listen_message = {"action": "listen", "data": {"streams":
                                                           ["AM.{}".format(symbol)]}}
        self.__ws.send(json.dumps(listen_message))

    def stream_trades(self, symbol):
        listen_message = {"action": "listen", "data": {"streams": ["T.{}".format(symbol)]}}
        self.__ws.send(json.dumps(listen_message))
