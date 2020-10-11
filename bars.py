import config, requests, json, pprint
from datetime import datetime

#minute_bars_url = config.bars_url + "/5Min?symbols=MSFT"
#day_bars_url = "{}/day?symbols={}&limit=100".format(config.bars_url, "AAPL,MSFT")
bars_url = ''

#r = requests.get(day_bars_url, headers=config.HEADERS)
#
#data = r.json()

#for symbol in data:
#    filename = "data/ohlc/{}.txt".format(symbol)
#    file = open(filename, "w+")
#    file.write("Date,Open,High,Low,Close,Volume,OpenInterest\n")
#
#    for bar in data[symbol]:
#        t = datetime.fromtimestamp(bar['t'])
#        day = t.strftime('%Y-%m-%d')
#        line = "{},{},{},{},{},{},{}\n".format(day, bar['o'], bar['h'], bar['l'], bar['c'], bar['v'], 0.00)
#        file.write(line)

def get_historical_data(symbol, number_of_lines, timeframe):
    ''' Timeframe could be 1Min (or minute), 5Min, 15Min, day (or 1D) '''

    bars_url = "{0}/{1}?symbols={2}&limit={3}".format(config.bars_url,
                                                      timeframe, symbol,
                                                      number_of_lines)

    req = requests.get(bars_url, headers=config.HEADERS)

    # This is a dictionary!
    data = req.json()

    # Convert timestamp to regular date
    for row in data[symbol]:
        row['t'] = datetime.fromtimestamp(row['t']).strftime("%Y-%m-%d")


    pp = pprint.PrettyPrinter(indent=4)

    #pp.pprint(data['SPY'])

    return data

    #data = json.dumps(req.json(), indent=4)
    #print(data)
