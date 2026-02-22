import pandas as pd
from pathlib import Path
import os

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

    #print latest net worth
    latest = df.sort_values("Date").iloc[-1]
    print(f"Date: {latest['Date']}")
    print(f"Net Worth: ${latest['net_worth']:,.2f}")

if __name__ == "__main__":
    main()