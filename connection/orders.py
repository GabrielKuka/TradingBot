import config
from connection.alpaca_connection import *


class Orders:

    def __init__(self):

        conn = AlpacaConnection(config.api_key, config.api_secret,
                                config.ACCOUNT_URL)

        self.__alpaca = conn.get_alpaca()

    def get_positions(self):
        positions = self.__alpaca.list_positions

        return positions

    def get_orders(self):
        orders = self.__alpaca.list_orders()

        return orders

    def get_opened_orders(self):
        opened_orders = self.__alpaca.list_orders(status='open')

        return opened_orders

    def cancel_order(self, order_id):
        self.__alpaca.cancel_order(order_id)

    def cancel_opened_orders(self):
        orders = self.get_opened_orders()

        for order in orders:
            self.cancel_order(order.id)

    def submit_order(self, symbol, qty, order_side):

        side = order_side.capitalize()

        if qty > 0:
            try:
                self.__alpaca.submit_order(symbol, qty, order_side, "market", "day")

                print("{0}ing {1} shares of {2} -> COMPLETED".format(side, str(qty), symbol))

            except:
                print("{0}ing {1} shares of {2} -> FAILED".format(side, str(qty), symbol))

