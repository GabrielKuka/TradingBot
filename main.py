from algorithms.bollinger_bands import BollingerBands
from algorithms.rsi import *
from algorithms.dual_avg_crossover import DualAverageCrossover
from algorithms.mfi import MoneyFlowIndex
from algorithms import mfi
from algorithms.high_speed.rsi import RSI
from algorithms.high_speed.bollinger import BollingerBands
from algorithms.longshort import *
from authentication import Auth

auth = Auth()


def begin():
    print("Welcome!")

    auth.execute()

    handle_mode_command()


def handle_mode_command():
    while True:

        print("Enter bot mode: ")
        print("0. Exit\n1. Testing\n2. Live Trading\n3. High Speed Trading\n4. Switch to Another Account\n5. Print Account Data\n")
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

            elif mode == 3:
                handle_high_speed_mode()
                break

            elif mode == 4:
                auth.change_credentials()

            elif mode == 5:
                print(Account())

            else:
                print("Invalid input.\n")
        else:
            print("You can either select 1 or 2.\n")


def handle_active_mode():
    while True:
        print("\n[LIVE TRADING MODE]\n")
        print("Choose one of the algorithms: ")

        list_algos('live')

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


def handle_high_speed_mode():
    while True:
        print('\n[HIGH SPEED MODE]\n')
        print('Choose one of the algorithms: ')

        list_algos('high_speed')

        algo = input('\n=> ')

        if algo.isdigit():
            algo = int(algo)

            if algo == 0:
                handle_mode_command()
                break
            elif algo == 1:
                # RSI
                rsi = RSI()
                rsi.execute()
            elif algo == 2:
                # Bollinger
                bb = BollingerBands()
                bb.execute()
            else:
                print('Invalid input')

        else:
            print('Invalid input')


def handle_test_mode():
    while True:
        print("\n[TESTING MODE]\n")
        print("Choose one of the algorithms: ")

        list_algos('test')

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
                algo = BollingerBands('test')
                algo.execute()

            else:
                print("\n[UNKNOWN COMMAND]\n")


def list_algos(which):
    from config import LIVE_ALGORITHMS, TEST_ALGORITHMS, HIGH_SPEED_ALGORITHMS

    if which == 'live':
        for key, algo in LIVE_ALGORITHMS.items():
            print("{0}. {1}".format(key, algo))
    elif which == 'test':
        for key, algo in TEST_ALGORITHMS.items():
            print("{0}. {1}".format(key, algo))
    elif which == 'high_speed':
        for key, algo in HIGH_SPEED_ALGORITHMS.items():
            print("{0}. {1}".format(key, algo))


if __name__ == '__main__':
    begin()
