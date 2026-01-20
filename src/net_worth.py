import pandas as pd

csv_path = "data/Balances.csv"
  
def main():
    #read CSV
    df = pd.read_csv(csv_path, parse_dates=["Date"])

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #compute net worth per row
    df["net_worth"] = df[balance_cols].sum(axis=1)

    #print latest net worth
    latest = df.sort_values("Date").iloc[-1]
    print(f"Date: {latest['Date'].date()}")
    print(f"Net Worth: ${latest['net_worth']:,.2f}")

if __name__ == "__main__":
    main()