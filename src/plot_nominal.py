import pandas as pd
from pathlib import Path
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from dataclasses import dataclass
from typing import Dict, Optional, List


"""
Takes nominal net worth calculated from Balances.csv and plots it. 

"""

DRIVE_BASE = Path("/content/drive/MyDrive/Finances/FIRE")

BALANCES_CSV = DRIVE_BASE / "Balances.csv"

PROJ_NOM_CSV = DRIVE_BASE / "projection_nominal.csv"


def plot_balances():
    #read BALANCES.CSV
    df = pd.read_csv(BALANCES_CSV, parse_dates=["Date"])            #changed csv_path to BALANCES_CSV

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #compute net worth per row
    df["net_worth"] = df[balance_cols].sum(axis=1)

    #plot Net Worth Actuals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['net_worth'], label='actual', linestyle='-', color='b')
    plt.title('Net Worth- Nominal')
    plt.xlabel('Date')
    plt.ylabel('Net Worth ($)')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"${v/1e6:.2f}M"))
    plt.grid(True)
    plt.tight_layout()
    

def plot_proj_nom():
    #read projection_nominal.csv
    df = pd.read_csv(PROJ_NOM_CSV, parse_dates=["Date"])            

    #identify balance columns (everything except date)
    balance_cols = [c for c in df.columns if c != "Date"]

    #plot Prjected Net Worth Nominals
    df['Date'] = pd.to_datetime(df['Date'])
    plt.plot(df['Date'],df['Net_Worth'], label='projected', linestyle='dotted', color='r')
    # plt.title('Net Worth')
    # plt.xlabel('Date')
    # plt.ylabel('Net Worth ($)')
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    # plt.xticks(rotation=45)
    # plt.grid(True)
    # plt.tight_layout()
    plt.show()





def main():                     #this is the main function that runs the other helper functions
    plot_balances()
    plot_proj_nom()
   

if __name__ == "__main__":
    main()