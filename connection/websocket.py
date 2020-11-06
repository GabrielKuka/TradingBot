import websocket, json
from config import *

class WebSocket:

    def __init__(self):

        self.authenticated = False
        self.ws = websocket.WebSocketApp(SOCKET_URL,
                        on_message = lambda ws, message: self.on_message(ws, message),
                        on_open = lambda ws: self.on_open(ws),
                        on_close = lambda ws: self.on_close(ws)
                                        )

        self.ws.run_forever()



    def on_open(self, ws):
        print("[CONNECTION OPENED]")

        # Authenticate
        self.authenticate()

        # Stream something
        self.stream_trades('SPY')


    def on_close(self, ws):
        print("[CONNECTION CLOSED]")


    def on_message(self, ws, message):

        message = json.loads(message)

        if not self.authenticated:
            self.check_auth(message)


        print(message['data']['p'])


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


    def stream_trades(self, symbol):
        listen_message = {"action": "listen", "data": {"streams": ["T.{}".format(symbol)]}}
        self.ws.send(json.dumps(listen_message))


    def stream_minute_bars(self, symbol):
        listen_message = {"action": "listen", "data": {"streams":
                                                       ["AM.{}".format(symbol)]}}
        self.ws.send(json.dumps(listen_message))


