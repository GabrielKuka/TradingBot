import numpy, talib
import helper.file_manager as file_manager

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


def calc_rsi(closes, in_position):

    if len(closes) > RSI_PERIOD:

        np_closes = numpy.array(closes)
        rsi_values = talib.RSI(np_closes, RSI_PERIOD)

        rsi_values = list(filter(lambda x: not numpy.isnan(x), rsi_values))

        file_manager.apply_rsi_values("data/rsi.txt", str(rsi_values) + "\n\n")

        last_rsi = rsi_values[-1]

        print("Current RSI: {0}".format(last_rsi))

        if last_rsi > RSI_OVERBOUGHT:
#            if in_position:
#                print("Sell sell sell!")
#                in_position = False
#            else:
#                print("Nothing to sell")
            print("Sell sell sell!")

        elif last_rsi < RSI_OVERSOLD:
            #if not in_position:
            #    print("Buy buy buy")
            #    in_position = True
            #else:
            #    print("Already own the stock!")
            print("Buy Buy buy")
        else:
            print("Nothing to buy or sell.\nAsset's latest RSI is between 30 and 70.")

