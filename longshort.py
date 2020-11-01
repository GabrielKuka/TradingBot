import alpaca_trade_api as tradeapi
import config, threading, time
from market import *
from orders import *
from account import *
from data.connection import *

class LongShort:

    def __init__(self):
        self.alpaca = tradeapi.REST(config.api_key, config.api_secret,
                                    config.ACCOUNT_URL)
        self.__market = Market()
        self.__orders = Orders()
        self.__account = Account()

        stock_universe = ['F', 'AAL', 'CCL', 'AGNC', 'IBIO', 'BAC', 'GM',
                          'SNAP', 'BA', 'TWTR', 'QCOM', 'INTC', 'MGM', 'NCLH',
                         'GPRO', 'ACB', 'NIO', 'AMD', 'T', 'UBER']

        self.all_stocks = []

        for stock in stock_universe:
            self.all_stocks.append([stock, 0])

        self.long = []
        self.short = []

        self.qty_long = 0
        self.qty_short = 0

        self.adjusted_qty_long = None
        self.adjusted_qty_short = None

        self.blacklist = set()
        self.long_amoung = 0
        self.short_amount = 0

        self.till_close = None


    def await_market_open(self):
        ''' Wait until market opens '''

        while True:

            is_open = self.__market.is_market_opened()

            if is_open:
                break
            else:
                open_time = self.__market.get_open_time()
                current_time = self.__market.get_current_time()
                till_open = int((open_time - current_time)/60)

                print("{} more minutes for stock market to open".format(str(till_open)))
                time.sleep(60)


    def execute(self):

        # Cancel all existing orders
        self.__orders.cancel_opened_orders()

        # Wait for market to open
        t1 = threading.Thread(target=self.await_market_open)
        t1.start()
        t1.join()
        print("[Market Opened]")

        # Rebalance portfolio every minute
        while True:

            # Find how much time till market close
            close_time = self.__market.get_close_time()
            current_time = self.__market.get_current_time()

            self.till_close = close_time - current_time

            if self.till_close < (60 * 15):

                # Close positions
                print("Market closing soon.")
                print("[Closing Positions].")

                positions = self.__account.list_positions()
                for position in positions:
                    order_side = 'sell' if position.side == 'long' else 'buy'

                    qty = abs(int(float(position.qty)))

                    t_submit_order = threading.Thread(target=self.submit_order, args=[position.symbol, qty, order_side])

                    t_submit_order.start()
                    t_submit_order.join()

                print("Sleeping until market close.")
                time.sleep(60 * 15)
            else:
                # Rebalance portfolio
                t_rebalance = threading.Thread(target=self.rebalance)
                t_rebalance.start()
                t_rebalance.join()
                time.sleep(60)


    def rebalance(self):
        t_rerank = threading.Thread(target=self.rerank)
        t_rerank.start()
        t_rerank.join()

        # Clear existing orders.
        orders = self.__orders.get_opened_orders()
        for order in orders:
            self.__orders.cancel_order(order.id)

        print("Going long on {}".format(str(self.long)))
        print("Going short on {}".format(str(self.short)))

        # Remove positions that are no longer in the short or long list and
        # make a list of positions that don't need to change. Adjust position
        # quantities if needed.

        executed = [[], []]
        positions = self.__account.list_positions()
        self.blacklist.clear()

        for position in positions:

            pos_in_long = self.long.count(position.symbol) > 0
            pos_in_short = self.short.count(position.symbol) > 0

            if not pos_in_long and not pos_in_short:
                # Position neither in the long nor in the short. Clear it!

                side = 'sell' if position.side == 'long' else 'buy'

                respSO = []
                t_submit_order = threading.Thread(target=self.submit_order,
                                 args=[position.symbol,
                                       abs(int(float(position.qty))), side,
                                      respSO])

                t_submit_order.start()
                t_submit_order.join()

            elif pos_in_long:

                if position.side == 'short':
                    # Position changes from short to long. Clear short position
                    # to prepare for long position
                    respSO = []
                    t_submit_order = threading.Thread(target=self.submit_order,
                                     args=[position.symbol, abs(int(float(position.qty))),
                                            'buy', respSO])
                    t_submit_order.start()
                    t_submit_order.join()
                else:
                    pos_qty = abs(int(float(position.qty)))
                    diff = pos_qty - self.qty_long

                    # diff > 0 -> Too many longs, sell some.
                    # diff < 0 -> Too little longs, buy some.

                    side = 'sell' if diff > 0 else 'buy'

                    respSO = []
                    t_submit_order = threading.Thread(target=self.submit_order,
                                     args=[position.symbol, abs(diff), side,
                                           respSO])
                executed[0].append(position.symbol)
                self.blacklist.add(position.symbol)

            elif pos_in_short:

                if position.side == 'long':
                    side = 'sell'
                    respSO= []
                    t_submit_order = threading.Thread(target=self.submit_order,
                                     args=[position.symbol,
                                           abs(int(float(position.qty))),
                                           side, respSO])

                else:

                    pos_qty = abs(int(float(position.qty)))

                    diff = pos_qty - self.qty_short
                    # diff > 0 -> too many shorts. Buy some.
                    # diff < 0 -> too little shorts. Sell some.

                    side = 'buy' if diff > 0 else 'sell'
                    respSO= []
                    t_submit_order = threading.Thread(target=self.submit_order,
                                         args=[position.symbol, diff,
                                               side, respSO])
                    t_submit_order.start()
                    t_submit_order.join()

                executed[1].append(position.symbol)
                self.blacklist.add(position.symbol)


        # Send orders to all remaining stocks in the long and short list.
        respSendBOLong = []
        t_batch_order_l = threading.Thread(target=self.submit_batch_order,
                         args=[self.qty_long, self.long, 'buy', respSendBOLong])
        t_batch_order_l.start()
        t_batch_order_l.join()
        respSendBOLong[0][0] += executed[0]

        if len(respSendBOLong[0][1]) > 0:
            # Handle rejected/incomplete orders and determine new quantities to purchase.
            get_tp_long = []
            t_get_tp_long = threading.Thread(target=self.get_total_price, args=[respSendBOLong[0][0], get_tp_long])
            t_get_tp_long.start()
            t_get_tp_long.join()

            if get_tp_long[0] > 0:
                self.adjusted_qty_long = self.long_amount // get_tp_long[0]
            else:
                self.adjusted_qty_long = -1
        else:
            self.adjusted_qty_long = -1

        respSendBOShort = []
        t_batch_order_sh = threading.Thread(target=self.submit_batch_order,
                         args=[self.qty_short, self.short, 'sell', respSendBOShort])
        t_batch_order_sh.start()
        t_batch_order_sh.join()
        respSendBOShort[0][0] += executed[1]

        if len(respSendBOShort[0][1]) > 0:
            # Handle rejected/incomplete orders and determine new quantities to purchase.
            get_tp_short = []
            t_get_tp_short = threading.Thread(target=self.get_total_price, args=[respSendBOShort[0][0], get_tp_short])
            t_get_tp_short.start()
            t_get_tp_short.join()
            if get_tp_short[0] > 0:
                self.adjusted_qty_short = self.short_amount // get_tp_short[0]
            else:
                self.adjusted_qty_short = -1
        else:
            self.adjusted_qty_short = -1



       # Reorder stocks that didn't throw an error so that the equity quota is reached.
        if self.adjusted_qty_long > -1:
            self.qty_long = int(self.adjusted_qty_long - self.qty_long)
            for stock in respSendBOLong[0][0]:
              respResendBOLong = []
              tResendBOLong = threading.Thread(target=self.submit_order, args=[stock, self.qty_long, "buy", respResendBOLong])
              tResendBOLong.start()
              tResendBOLong.join()

        if self.adjusted_qty_short > -1:
            self.qty_short = int(self.adjusted_qty_short - self.qty_short)
            for stock in respSendBOShort[0][0]:
              respResendBOShort = []
              tResendBOShort = threading.Thread(target=self.submit_order, args=[stock, self.qty_short, "sell", respResendBOShort])
              tResendBOShort.start()
              tResendBOShort.join()


    def rerank(self):
        tRank = threading.Thread(target=self.rank)
        tRank.start()
        tRank.join()

        # Grabs the top and bottom quarter of the sorted stock list to get the long and short lists.
        long_short_amount = len(self.all_stocks) // 4

        # Empty long and short list
        self.long = []
        self.short = []

        # Grab the bottom 20% of the stocks to short and the top 20% to long
        for i, stock_field in enumerate(self.all_stocks):
            if i < long_short_amount:
              self.short.append(stock_field[0])
            elif i > (len(self.all_stocks) - 1 - long_short_amount):
              self.long.append(stock_field[0])

        equity = int(float(self.__account.equity()))

        # Use 30% of equity for shorting and 70% for taking long positions
        self.short_amount = equity * 0.30
        self.long_amount = equity - self.short_amount

        get_tp_long = []
        t_get_tp_long = threading.Thread(target=self.get_total_price, args=[self.long, get_tp_long])
        t_get_tp_long.start()
        t_get_tp_long.join()

        get_tp_short = []
        t_get_tp_short = threading.Thread(target=self.get_total_price, args=[self.short, get_tp_short])
        t_get_tp_short.start()
        t_get_tp_short.join()

        self.qty_long = int(self.long_amount // get_tp_long[0])
        self.qty_short = int(self.short_amount // get_tp_short[0])



    def submit_order(self, symbol, qty, order_side, resp):

        side = order_side.capitalize()

        if qty > 0:
           try:
               self.alpaca.submit_order(symbol, qty, order_side, "market", "day")

               print("{0}ing {1} shares of {2} -> COMPLETED".format(side, str(qty), symbol))

               resp.append(True)
           except:
               print("{0}ing {1} shares of {2} -> FAILED".format(side, str(qty), symbol))

               resp.append(False)


    def submit_batch_order(self, qty, stocks, side, resp):

        completed = []
        incompleted = []

        for stock in stocks:
          if self.blacklist.isdisjoint({stock}):
            respSO = []
            tSubmitOrder = threading.Thread(target=self.submit_order,
                                            args=[stock, qty, side, respSO])
            tSubmitOrder.start()
            tSubmitOrder.join()

            if not respSO[0]:
              # Stock order did not go through, add it to incomplete.
              incompleted.append(stock)
            else:
              completed.append(stock)
            respSO.clear()

        resp.append([completed, incompleted])


    # Get the total price of the array of input stocks.
    def get_total_price(self, stocks, resp):
      totalPrice = 0
      for stock in stocks:
        bars = self.alpaca.get_barset(stock, "minute", 1)
        totalPrice += bars[stock][0].c
      resp.append(totalPrice)


    # Get percent changes of the stock prices over the past 10 minutes.
    def get_percent_changes(self):

      for i, stock in enumerate(self.all_stocks):

        bars = self.alpaca.get_barset(stock[0], 'minute', 10)

        close_price = bars[stock[0]][len(bars[stock[0]]) - 1].c
        open_price = bars[stock[0]][0].o

        self.all_stocks[i][1] = (close_price - open_price) / open_price


    # Mechanism used to rank the stocks, the basis of the Long-Short Equity Strategy.
    def rank(self):
      # Ranks all stocks by percent change over the past 10 minutes (higher is better).
      tGetPC = threading.Thread(target=self.get_percent_changes)
      tGetPC.start()
      tGetPC.join()

      # Sort the stocks in place by the percent change field (marked by pc).
      self.all_stocks.sort(key=lambda x: x[1])

