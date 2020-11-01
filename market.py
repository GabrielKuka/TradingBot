import config, datetime
from data.connection import *

class Market:

    def __init__(self):

        conn = Connection(config.api_key, config.api_secret, config.ACCOUNT_URL)

        self.__alpaca = conn.get_alpaca()


    def get_close_time(self):
        close_time = self.get_clock().next_close.replace(tzinfo=datetime.timezone.utc).timestamp()

        return close_time


    def get_current_time(self):
        current_time = self.get_clock().timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()

        return current_time


    def get_open_time(self):
        open_time = self.get_clock().next_open.replace(tzinfo=datetime.timezone.utc).timestamp()

        return open_time

    def get_clock(self):
        return self.__alpaca.get_clock()


    def is_market_opened(self):
        return self.get_clock().is_open
