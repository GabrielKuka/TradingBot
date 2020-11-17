# Keys used to authenticate to Alpaca Platform

content = open('files/credentials.txt', 'r').read().splitlines()

api_key = '' if not content else content[0]
api_secret = '' if not content else content[1]

# api_key="PK3NLNARB24PPO809FF9"
# api_secret = "atx0JpIGRw6KZ3NP5rxkCudRE3kSU52D3HHfdzAJ"

HEADERS = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
        }

LIVE_ALGORITHMS = {
    0: 'EXIT',
    1: 'RSI',
    2: 'Dual Average Crossover',
    3: 'Money Flow Index',
    4: 'Long Short',
    5: 'Bollinger Bands'
}

TEST_ALGORITHMS = {
    0: 'EXIT',
    1: 'RSI',
    2: 'Dual Average Crossover',
    3: 'Money Flow Index',
    4: 'Bollinger Bands'
}

HIGH_SPEED_ALGORITHMS = {
    0: 'EXIT',
    1: 'RSI',
    2: 'Bollinger Bands'
}

BASE_URL = "https://data.alpaca.markets"

ACCOUNT_URL = "https://paper-api.alpaca.markets"

# Url to retrieve historical data
BARS_URL = "{}/v1/bars".format(BASE_URL)

# Url to retrieve live stream market data
SOCKET_URL = "wss://{}/stream".format(BASE_URL[8:])
