import config
import concurrent.futures as cf
from connection.alpaca_connection import *


class Account:

    def __init__(self):

        conn = AlpacaConnection(config.api_key, config.api_secret, config.ACCOUNT_URL)

        with cf.ThreadPoolExecutor() as executor:
            t1 = executor.submit(conn.retrieve_account)
            t2 = executor.submit(conn.retrieve_portfolio)

            for _ in range(2):
                self.account = t1.result()
                self.portfolio = t2.result()

        self.__status = self.account.status
        self.__buying_power = float(self.account.buying_power)
        self.__equity = float(self.account.equity)
        self.__gain_loss = self.__equity - float(self.account.last_equity)
        self.__cash = float(self.account.cash)
        self.__portfolio_value = float(self.account.portfolio_value)

    def account_status(self):
        return self.__status

    def list_positions(self):

        return self.portfolio

    def has_position(self, symbol):
        has_pos = False
        positions = self.list_positions()
        position = None

        for pos in positions:
            if pos.symbol == symbol and int(pos.qty) > 0:
                has_pos = True
                position = pos
                break

        return has_pos, position

    def portfolio_value(self):
        return self.__portfolio_value

    def buying_power(self):

        return self.__buying_power

    def gain_loss(self):

        return self.__gain_loss

    def equity(self):
        return self.__equity

    def __str__(self):

        print("[Retrieving Data]")

        status = "Account Status: {}\n".format(self.account_status())
        equity = "Equity: ${:,}\n".format(self.equity())
        buying_power = "Buying Power: ${:,}\n".format(self.buying_power())
        balance_change = "Today's change: {:.2f}\n".format(self.gain_loss())
        portfolio_value = "Total portfolio value: ${:,}\n".format(self.portfolio_value())
        positions = self.portfolio

        if len(positions) == 0:
            portfolio = "You portfolio is empty."
        else:
            portfolio = "\n~+~+~+~+~+~+~+~+~+~+~+~+~+~+~\n\n"
            portfolio += "Your portfolio: \n\n"

            for index, pos in enumerate(positions, start=1):
                portfolio += "{}. {} shares of {}\n".format(index, pos.qty,
                                                            pos.symbol)

            portfolio += portfolio_value

            portfolio += "\n~+~+~+~+~+~+~+~+~+~+~+~+~+~+~\n\n"

        return status + portfolio + equity + buying_power + balance_change
