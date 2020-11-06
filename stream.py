from algorithms.momentum.rsi.rsi_algo import *
from algorithms.momentum.dual_avg_crossover.dual_avg_crossover import DualAverageCrossover
from algorithms.momentum.mfi import mfi
from algorithms.longshort import *
from connection.websocket import *


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
                pass
            elif algo == 3:
                pass
            elif algo == 4:
                # Long Short strategy
                ls = LongShort()
                ls.execute()
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
                pass

            elif algo == 2:
                dac = DualAverageCrossover()
                dac.execute()

            elif algo == 3:
                algo = mfi.MoneyFlowIndex()
                algo.execute()
            else:
                print("\n[UNKNOWN COMMAND]\n")


def list_algos():
    for key, algo in ALGORITHMS.items():
        print("{0}. {1}".format(key, algo))


if __name__ == '__main__':
    begin()
