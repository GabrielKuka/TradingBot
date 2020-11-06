# Keys used to authenticate to Alpaca Platform
api_key="PK3NLNARB24PPO809FF9"
api_secret = "atx0JpIGRw6KZ3NP5rxkCudRE3kSU52D3HHfdzAJ"

HEADERS = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
        }

ALGORITHMS = {
    0: 'EXIT',
    1: 'RSI',
    2: 'Dual Average Crossover',
    3: 'Money Flow Index',
    4: 'Long Short'
}

BASE_URL = "https://data.alpaca.markets"

ACCOUNT_URL = "https://paper-api.alpaca.markets"

# Url to retrieve historical data
BARS_URL = "{}/v1/bars".format(BASE_URL)

# Url to retrieve live stream market data
SOCKET_URL = "wss://{}/stream".format(BASE_URL[8:])
