import alpaca_trade_api as trade_api
import datetime

class Connection:

    def __init__(self, public_key, secret_key, url):
        # Connect to ALPACA
        self._api = trade_api.REST(public_key, secret_key, url)

    def get_alpaca(self):

        return self._api


    def retrieve_account(self):
        self.account = self._api.get_account()

        return self.account

    def retrieve_portfolio(self):
        self.portfolio = self._api.list_positions()

        return self.portfolio

