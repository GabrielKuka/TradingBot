import config, requests, json
from datetime import datetime


def get_historical_data(symbol, number_of_lines, timeframe):
    ''' Timeframe could be 1Min (or minute), 5Min, 15Min, day (or 1D) '''

    request_url = "{0}/{1}?symbols={2}&limit={3}".format(config.BARS_URL,
                                                      timeframe, symbol,
                                                      number_of_lines)

    req_errors = requests.exceptions

    try:
        req = requests.get(request_url, headers=config.HEADERS)

    except req_errors.Timeout:
        # Request timed out. Maybe connection error?
        print("Request Timeout. Do you have a stable connection?")
        return False

    except req_errors.TooManyRedirects:
       # Bad URL
       print("Bad URL. Try a different one.")
       return False

    except req_errors.HTTPError as http_error:
       raise SystemError(http_error)

    except req_errors.RequestException:
       print("There was an error. Are you connected?")
       return False

    else:
       # This is a dictionary!
       data = req.json()

       # Convert timestamp to regular date
       for row in data[symbol]:
           row['t'] = datetime.fromtimestamp(row['t']).strftime("%Y-%m-%d")


       return data[symbol]


