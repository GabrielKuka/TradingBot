# Keys used to authenticate to Alpaca Platform
api_key="PKEMGP5998C3OM6N3JU7"
api_secret = "daGGEAtMFt3R6uSNv5XlSBU5irJEAnE1z5mOwU74"

HEADERS = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
        }

ALGORITHMS = {
    0: 'EXIT',
    1: 'RSI',
    2: 'Dual Average Crossover',
    3: 'Money Flow Index'
}

BASE_URL = "https://data.alpaca.markets"

ACCOUNT_URL = "https://paper-api.alpaca.markets"

# Url to retrieve historical data
BARS_URL = "{}/v1/bars".format(BASE_URL)

# Url to retrieve live stream market data
SOCKET_URL = "wss://{}/stream".format(BASE_URL[9:])
