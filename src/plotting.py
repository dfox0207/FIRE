import pandas as pd
import matplotlib.dates as mdates
import matplotlib.ticker as ticker


def plot_networth(df, ax):
    
    #read BALANCES.CSV
    df_bal = pd.read_csv(BALANCES_CSV, parse_dates=["Date"])       

    #identify balance columns (everything except date)
    balance_cols = [c for c in df_bal.columns if c != "Date"]

    #compute net worth per row
    df_bal["net_worth"] = df_bal[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df_bal['Date'] = pd.to_datetime(df_bal['Date'])
    ax.plot(df_bal['Date'],df_bal['net_worth'], label='Actual Balances', linestyle='-', color='b')

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Net_Worth'], label='Projected Nominal Balances', linestyle='dotted', color='r')

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Net_Worth_Real'], label='Projected Real Balances', linestyle='dotted', color='g')

    # Format Chart Title and Axises
    ax.set_title('Net Worth')
    ax.set_xlabel('Date')
    ax.set_ylabel('Net Worth ($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

def plot_accounts(df, accounts, ax):              

    #plot Account Nominal Balances
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    for acct in accounts:
        ax.plot(df['Date'],df[acct], label=f"{acct} Balances")

    # Format Chart Title and Axises
    ax.set_title('Account Balances')
    ax.set_xlabel('Date')
    ax.set_ylabel('Balance ($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()

def plot_income(df, ax):

    #plot Projected Income
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Income_Real'], label='Real Income')
    ax.plot(df['Date'],df['Income'], label='Nominal Income')
    ax.plot(df['Date'],df['Net_Income_Real'], label='Net Real Income')
    
    # Format Chart Title and Axises
    ax.set_title('Income')
    ax.set_xlabel('Date')
    ax.set_ylabel('($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()
    
def plot_tax(df, ax):

    #plot Projected Income
    df['Date'] = pd.to_datetime(df['Date'])
    ax.plot(df['Date'],df['Total Tax'], label='Taxes')
    
    
    # Format Chart Title and Axises
    ax.set_title('Taxes- Real (2025)')
    ax.set_xlabel('Date')
    ax.set_ylabel('($)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e3:.2f}k"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True)
    ax.legend()