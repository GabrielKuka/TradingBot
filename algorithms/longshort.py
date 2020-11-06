import alpaca_trade_api as tradeapi
import threading
from market import *
from orders import *
from account import *


class LongShort:

    def __init__(self):
        self.alpaca = tradeapi.REST(config.api_key, config.api_secret,
                                    config.ACCOUNT_URL)
        self.__market = Market()
        self.__orders = Orders()
        self.__account = Account()

        # List of stocks
        stock_universe = ['F', 'AAL', 'CCL', 'AGNC', 'IBIO', 'BAC', 'GM',
                          'SNAP', 'BA', 'TWTR']

        # List of stocks with the percentage change
        self.all_stocks = [[stock, 0] for stock in stock_universe]

        # List of stocks to go long or short
        self.long = []
        self.short = []

        # The amount of share to go long or short
        self.qty_long = 0
        self.qty_short = 0

        # The amount of shares to go long or short after uncompleted orders
        self.adjusted_qty_long = None
        self.adjusted_qty_short = None

        self.blacklist = set()
        self.long_amount = 0
        self.short_amount = 0

    def execute(self):

        # Cancel all existing orders
        self.__orders.cancel_opened_orders()

        # Wait for market to open
        t1 = threading.Thread(target=self.__market.await_market_open)
        t1.start()
        t1.join()
        print("[Market Opened]")

        # Rebalance portfolio every minute
        while True:

            # Find how much time till market close
            close_time = self.__market.get_close_time()
            current_time = self.__market.get_current_time()

            till_close = close_time - current_time

            if till_close < (60 * 15):

                # Close positions
                print("Market closing soon.")
                print("[Closing Positions].")

                positions = self.__account.list_positions()
                for position in positions:
                    order_side = 'sell' if position.side == 'long' else 'buy'

                    qty = abs(int(float(position.qty)))

                    t_order = threading.Thread(target=self.submit_order, args=[position.symbol, qty, order_side])
                    t_order.start()
                    t_order.join()

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
            thread = threading.Thread(target=self.__orders.cancel_order,
                                      args=[order.id])
            thread.start()
            thread.join()

        print("Going long on {}".format(str(self.long)))
        print("Going short on {}".format(str(self.short)))

        executed = [[], []]
        positions = self.__account.list_positions()
        self.blacklist.clear()

        for position in positions:

            pos_in_long = self.long.count(position.symbol) > 0
            pos_in_short = self.short.count(position.symbol) > 0

            if not pos_in_long and not pos_in_short:
                # Position neither in the long nor in the short. Clear it!

                side = 'sell' if position.side == 'long' else 'buy'

                t_submit_order = threading.Thread(target=self.submit_order,
                                                  args=[position.symbol,
                                                        abs(int(float(position.qty))), side])

                t_submit_order.start()
                t_submit_order.join()

            elif pos_in_long:

                if position.side == 'short':
                    # Go long!
                    t_submit_order = threading.Thread(target=self.submit_order,
                                                      args=[position.symbol, abs(int(float(position.qty))),
                                                            'buy'])
                    t_submit_order.start()
                    t_submit_order.join()
                else:
                    pos_qty = abs(int(float(position.qty)))
                    diff = pos_qty - self.qty_long

                    # diff > 0 -> Too many longs, sell some.
                    # diff < 0 -> Too little longs, buy some.

                    side = 'sell' if diff > 0 else 'buy'

                    t_submit_order = threading.Thread(target=self.submit_order,
                                                      args=[position.symbol, abs(diff), side])
                    t_submit_order.start()
                    t_submit_order.join()
                executed[0].append(position.symbol)
                self.blacklist.add(position.symbol)

            elif pos_in_short:

                if position.side == 'long':
                    side = 'sell'

                    t_submit_order = threading.Thread(target=self.submit_order,
                                                      args=[position.symbol,
                                                            abs(int(float(position.qty))),
                                                            side])
                    t_submit_order.start()
                    t_submit_order.join()
                else:

                    pos_qty = abs(int(float(position.qty)))

                    diff = pos_qty - self.qty_short
                    # diff > 0 -> too many shorts. Buy some.
                    # diff < 0 -> too little shorts. Sell some.

                    side = 'buy' if diff > 0 else 'sell'

                    t_submit_order = threading.Thread(target=self.submit_order,
                                                      args=[position.symbol, diff,
                                                            side])
                    t_submit_order.start()
                    t_submit_order.join()

                executed[1].append(position.symbol)
                self.blacklist.add(position.symbol)

        # Send orders to all remaining stocks in the long and short list.
        answer_bo_long = []
        t_bo_long = threading.Thread(target=self.submit_batch_order,
                                     args=[self.qty_long, self.long, 'buy', answer_bo_long])
        t_bo_long.start()
        t_bo_long.join()
        answer_bo_long[0][0] += executed[0]

        if len(answer_bo_long[0][1]) > 0:
            # Handle incomplete orders and find new quantities
            get_tp_long = []
            t_get_tp_long = threading.Thread(target=self.get_total_price, args=[answer_bo_long[0][0], get_tp_long])
            t_get_tp_long.start()
            t_get_tp_long.join()

            if get_tp_long[0] > 0:
                self.adjusted_qty_long = self.long_amount // get_tp_long[0]
            else:
                self.adjusted_qty_long = -1
        else:
            self.adjusted_qty_long = -1

        answer_bo_short = []
        t_batch_order_sh = threading.Thread(target=self.submit_batch_order,
                                            args=[self.qty_short, self.short, 'sell', answer_bo_short])
        t_batch_order_sh.start()
        t_batch_order_sh.join()
        answer_bo_short[0][0] += executed[1]

        # If there are failed orders
        if len(answer_bo_short[0][1]) > 0:
            # Handle them
            get_tp_short = []
            t_get_tp_short = threading.Thread(target=self.get_total_price, args=[answer_bo_short[0][0], get_tp_short])
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
            for stock in answer_bo_long[0][0]:
                answer = []
                t_resend_bo_long = threading.Thread(target=self.submit_order,
                                                    args=[stock, self.qty_long, "buy", answer])
                t_resend_bo_long.start()
                t_resend_bo_long.join()

        if self.adjusted_qty_short > -1:
            self.qty_short = int(self.adjusted_qty_short - self.qty_short)
            for stock in answer_bo_short[0][0]:
                answer = []
                t_resend_bo_short = threading.Thread(target=self.submit_order,
                                                     args=[stock, self.qty_short, "sell", answer])
                t_resend_bo_short.start()
                t_resend_bo_short.join()

    def rerank(self):

        # Rank stocks
        t_rank = threading.Thread(target=self.rank)
        t_rank.start()
        t_rank.join()

        # Grabs the top and bottom quarter of the sorted stock list.
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
        self.short_amount = equity * 0.45
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

    def rank(self):
        # Ranks all stocks by percent change over the past 10 minutes (higher is better).
        t_get_total_price = threading.Thread(target=self.get_percent_changes)
        t_get_total_price.start()
        t_get_total_price.join()

        # Sort the stocks by percentage change
        self.all_stocks.sort(key=lambda k: k[1])

    def submit_order(self, symbol, qty, order_side, answer=None):
        if answer is None:
            answer = []

        side = order_side.capitalize()

        if qty > 0:
            try:
                self.alpaca.submit_order(symbol, qty, order_side, "market", "day")

                print("{0}ing {1} shares of {2} -> COMPLETED".format(side, str(qty), symbol))

                answer.append(True)
            except:
                print("{0}ing {1} shares of {2} -> FAILED".format(side, str(qty), symbol))

                answer.append(False)

    def submit_batch_order(self, qty, stocks, side, resp):

        completed = []
        uncompleted = []

        for stock in stocks:
            if self.blacklist.isdisjoint({stock}):
                answer = []
                t_submit_order = threading.Thread(target=self.submit_order,
                                                  args=[stock, qty, side, answer])
                t_submit_order.start()
                t_submit_order.join()

                if not answer[0]:
                    # Stock order did not go through, add it to incomplete.
                    uncompleted.append(stock)
                else:
                    completed.append(stock)
                answer.clear()

        resp.append([completed, uncompleted])

    # Get the total price of all the stocks
    def get_total_price(self, stocks, ans):
        total_price = 0
        for stock in stocks:
            bars = self.alpaca.get_barset(stock, "minute", 1)
            total_price += bars[stock][0].c
        ans.append(total_price)

    # Get percent changes of the stock prices over the past 10 minutes.
    def get_percent_changes(self):

        for i, stock in enumerate(self.all_stocks):
            bars = self.alpaca.get_barset(stock[0], 'minute', 10)

            close_price = bars[stock[0]][len(bars[stock[0]]) - 1].c
            open_price = bars[stock[0]][0].o

            self.all_stocks[i][1] = (close_price - open_price) / open_price
