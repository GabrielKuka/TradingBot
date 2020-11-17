import os, websocket, json
from config import *


class Auth:

    def __init__(self):

        # Init empty values
        self.__public_key = None
        self.__secret_key = None

        # Track auth status
        self.authenticated = False

    def execute(self):

        if not self.__are_credentials_stored():
            print('Enter new credentials: ')

            # Enter credentials
            self.enter_data()

            # Create Socket
            ws = websocket.WebSocketApp(SOCKET_URL, on_open=lambda x: self.on_open(x),
                                        on_message=lambda s, msg: self.on_message(s, msg))
            ws.run_forever()

    def on_open(self, ws):
        print('Checking credentials..')

        # Authenticate
        auth_data = {
            "action": "authenticate",
            "data": {"key_id": self.__public_key, "secret_key": self.__secret_key}
        }

        ws.send(json.dumps(auth_data))

    def on_message(self, ws, message):
        message = json.loads(message)

        action = message['stream']
        result = message['data']['status']

        if action == "authorization" and result == "authorized":
            print('\n~~~~~~~~\n')
            print("Keys are correct!")
            self.authenticated = True

            # Store credentials into file
            file = open('files/credentials.txt', 'w')
            content = '{}\n{}'.format(self.__public_key, self.__secret_key)
            file.write(content)
            file.close()
            print('Credentials stored into file.')
            print('\n~~~~~~~~\n')
        else:
            print("Keys are not recognized by Alpaca.")
            self.authenticated = False
            self.execute()

        ws.close()

    def enter_data(self):

        while True:
            public_key = input('Public Key: ')

            if not public_key:
                print('Invalid value.')
            else:
                self.__public_key = public_key
                break

        while True:
            secret_key = input('Secret Key: ')

            if not secret_key:
                print('Invalid value.')
            else:
                self.__secret_key = secret_key
                break

    def __are_credentials_stored(self):
        return True if os.path.exists('files/credentials.txt') \
                       and len(open('files/credentials.txt', 'r').read()) != 0 else False

    def change_credentials(self):

        # Remove Credentials
        with open('files/credentials.txt', 'w') as file:
            file.write('')

        self.execute()
