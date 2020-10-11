import warnings, bars
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from helper.CSVReadWrite import CSVReadWrite

plt.style.use("fivethirtyeight")
warnings.filterwarnings('ignore')

symbol = 'SPY'
period = 14

# Load the stock data
bars_dict = bars.get_historical_data(symbol, 1000, 'day')[symbol]

csvfile = CSVReadWrite("data/ohlc/{}.csv".format(symbol),
                       "Date,Open,High,Low,Close,Volume")
csvfile.write_file(bars_dict, 't', 'o', 'h', 'l', 'c', 'v')

# Get the data
df = pd.read_csv("data/ohlc/{}.csv".format(symbol))

# Set the index
df = df.set_index(pd.DatetimeIndex(df['Date'].values))

# Visualize data
#plt.figure(figsize=(12.2, 4.5))
#plt.plot(df['Close'], label="Close Price")
#plt.title("{} Close Price".format(symbol))
#plt.xlabel("Date")
#plt.ylabel("Close Price USD ($)")
#plt.legend(df.columns.values, loc='upper left')
#plt.show()

# Calculate the typical price
typical_price = (df['Close'] + df['High'] + df['Low']) / 3

# Calculate the money flow
money_flow = typical_price * df['Volume']

# Get positive and negative money flows:
positive_flow = []
negative_flow = []

# Loop through the typical price
for i in range(1, len(typical_price)):
    if typical_price[i] > typical_price[i-1]:
        positive_flow.append(money_flow[i-1])
        negative_flow.append(0)
    elif typical_price[i] < typical_price[i-1]:
        positive_flow.append(0)
        negative_flow.append(money_flow[i-1])
    else:
        positive_flow.append(0)
        negative_flow.append(0)

# Get positive and negative money flows in time period
positive_mf = []
negative_mf = []

for i in range(period-1, len(positive_flow)):
    positive_mf.append(sum(positive_flow[i+1-period:i+1]))

for i in range(period - 1, len(negative_flow)):
    negative_mf.append(sum(negative_flow[i+1-period:i+1]))

# Calculate the money flow index
mfi = 100 * (np.array(positive_mf) / (np.array(positive_mf) +
             np.array(negative_mf)))

# Create MFI dataframe
mfi_df = pd.DataFrame()
mfi_df['MFI'] = mfi

# Visualize MFI
plt.figure(figsize=(12.2, 4.5))
plt.plot(mfi_df['MFI'], label="MFI")
plt.axhline(10, linestyle='--', color="orange")
plt.axhline(20, linestyle='--', color="blue")
plt.axhline(80, linestyle='--', color="blue")
plt.axhline(90, linestyle='--', color="orange")
plt.title("MFI")
plt.ylabel("MFI values")
#plt.show()

# Create a new dataframe
new_df = pd.DataFrame()
new_df = df[period:]
new_df['MFI'] = mfi

# Create a function to get the buy and sell signals
def get_signal(data, high, low):
   buy_signal = []
   sell_signal = []

   for i in range(len(data['MFI'])):

       if data['MFI'][i] > high:
           buy_signal.append(np.nan)
           sell_signal.append(data['Close'][i])
       elif data['MFI'][i] < low:
           buy_signal.append(data['Close'][i])
           sell_signal.append(np.nan)
       else:
           buy_signal.append(np.nan)
           sell_signal.append(np.nan)

   return (buy_signal, sell_signal)

new_df['Buy'] = get_signal(new_df, 80, 20)[0]
new_df['Sell'] = get_signal(new_df, 80, 20)[1]


# Show data

# Plot the data
plt.figure(figsize=(12.2, 4.5))
plt.plot(new_df['Close'], label="Close Price", alpha=0.5)
plt.scatter(new_df.index, new_df['Buy'], color="green", label="Buy Signal",
            marker = '^', alpha=1)
plt.scatter(new_df.index, new_df['Sell'], color="red", label="SellSignal",
            marker = 'v', alpha=1)
plt.title("{} Close Price".format(symbol))
plt.xlabel("Date")
plt.ylabel("Close Price USD ($)")
plt.legend(loc='upper left')
plt.show()
