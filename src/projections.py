import pandas as pd
from pathlib import Path
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def get_csv_path() -> Path:
    """
    Priority order:
    1) BALANCES_CSV env var (works local + Colab)
    2) Colab default Google Drive location
    3) Repo local fallback (data/Balances.csv)
    """
    env = os.environ.get("BALANCES_CSV")
    if env:
        return Path(env)
    
    #Colab Drive mount default
    colab_drive = Path("/content/drive/My Drive/Finances/FIRE/Balances.csv")
    if colab_drive.exists():
        return colab_drive

    # Local / repo fallback
    return Path("data/Balances.csv")
    
csv_path = get_csv_path()

def main():
    #read CSV
    df = pd.read_csv(csv_path, parse_dates=["Date"])

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #compute net worth per row
    df["net_worth"] = df[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['net_worth'], marker='o', linestyle='-', color='b')
    plt.title('Net Worth')
    plt.xlabel('Date')
    plt.ylabel('Net Worth ($)')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()