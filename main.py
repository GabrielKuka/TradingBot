from algorithms.bollinger_bands import BollingerBands
from algorithms.rsi import *
from algorithms.dual_avg_crossover import DualAverageCrossover
from algorithms.mfi import MoneyFlowIndex
from algorithms import mfi
from algorithms.longshort import *
from config import *


def begin():
    print("Welcome!")

    #   print(str(Account()))

    handle_mode_command()


def handle_mode_command():
    while True:

        print("Enter bot mode: ")
        print("0. Exit\n1. Testing Mode\n2. Action Mode\n\n")
        mode = input("=> ")

        if mode.isdigit():
            mode = int(mode)

            if mode == 0:
                print("\n[EXITING]")
                exit()

            if mode == 1:

                handle_test_mode()
                break

            elif mode == 2:
                handle_active_mode()
                break

            else:
                print("Invalid input.\n")
        else:
            print("You can either select 1 or 2.\n")


def handle_active_mode():
    while True:
        print("\n[ACTIVE MODE]\n")
        print("Choose one of the algorithms: ")

        list_algos()

        algo = input("\n=> ")

        if algo.isdigit():
            algo = int(algo)

            if algo == 0:
                print("\n[EXITING]\n")
                handle_mode_command()
                break
            elif algo == 1:
                rsi = RSI('active')
                rsi.execute()
            elif algo == 2:
                dac = DualAverageCrossover('active')
                dac.execute()
            elif algo == 3:
                mfi = MoneyFlowIndex('active')
                mfi.execute()
            elif algo == 4:
                # Long Short strategy
                ls = LongShort()
                ls.execute()
            elif algo == 5:
                # Bollinger Bands
                bb = BollingerBands('active')
                bb.execute()
            else:
                print("\n[UNKNOWN COMMAND]\n")


def handle_test_mode():
    while True:
        print("\n[TESTING MODE]\n")
        print("Choose one of the algorithms: ")

        list_algos()

        algo = input("\n=> ")

        if algo.isdigit():

            algo = int(algo)

            if algo == 0:
                print("\n[EXITING]\n")
                handle_mode_command()
                break
            elif algo == 1:
                # RSI
                algo = RSI('test')
                algo.execute()

            elif algo == 2:
                dac = DualAverageCrossover('test')
                dac.execute()

            elif algo == 3:
                algo = mfi.MoneyFlowIndex('test')
                algo.execute()

            elif algo == 4:
                pass

            elif algo == 5:
                algo = BollingerBands('test')
                algo.execute()
            else:
                print("\n[UNKNOWN COMMAND]\n")


def list_algos():
    for key, algo in ALGORITHMS.items():
        print("{0}. {1}".format(key, algo))


if __name__ == '__main__':
    begin()
