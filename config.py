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

# Url to retrieve historical data
BARS_URL = "https://data.alpaca.markets/v1/bars"

# Url to retrieve live stream market data
SOCKET_URL = "wss://data.alpaca.markets/stream"
