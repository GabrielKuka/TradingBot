import config
from data.connection import *

class Orders:

    def __init__(self):

        conn = Connection(config.api_key, config.api_secret,
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
            self.cancel_order(order_id)



    def submit_order(self, symbol, qty, order_side, resp):
       if qty > 0:
          try:
            self.__alpaca.submit_order(symbol, qty, order_side, "market", "day")
            print("Market order of | " + str(qty) + " " + symbol + " " + order_side + " | completed.")
            resp.append(True)
          except:
            print("Order of | " + str(qty) + " " + symbol + " " + order_side + " | did not go through.")
            resp.append(False)
          else:
              print("Quantity is 0, order of | " + str(qty) + " " + symbol + " " + order_side + " | not completed.")
              resp.append(True)


    #def submit_batch_order(self, qty, stocks, side, resp):
    #    executed = []
    #    incomplete = []
    #    for stock in stocks:
    #      if self.blacklist.isdisjoint({stock}):
    #        respSO = []
    #        tSubmitOrder = threading.Thread(target=self.submit_order,
    #                                        args=[stock, qty, side, respSO])
    #        tSubmitOrder.start()
    #        tSubmitOrder.join()
    #        if not respSO[0]:
    #          # Stock order did not go through, add it to incomplete.
    #          incomplete.append(stock)
    #        else:
    #          executed.append(stock)
    #        respSO.clear()
    #    resp.append([executed, incomplete]) 
