class MinuteBar:
    """ Stores data about a bar """

    def __init__(self, symbol, closing_price):
        self.symbol = symbol
        self.closing_price = closing_price

    def __str__(self):
        return "Symbol: {0}\tClosing Price: ${1}".format(self.symbol,
                                                         self.closing_price)
