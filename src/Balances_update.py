from __future__ import annotations

import csv
import os
import re
from datetime import datetime, datetime
from pathlib import Path
from typing import Dict, List, Optional

CSV_Path = Path("data/Balances.csv")

ACCOUNTS = ["TSP", "SERS", "403(b)", "457(b)", "ROTH IRA", "Brokerage"]

def parse_money(s:str) -> float:
    """
    Accepts inputs like:
        437133.95
        437,133.95
        $437,133.95
        (1,234.56) -> -1234.56
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty input")

    #Convert parentheses negative: (1,234.56) -> -1234.56
    m = re.match(r"^\((.*)\)$", s)
    if m:
        s = "-" + m.group(1)
    
    #Remove $, commas, and spaces
    s = re.sub(r"[\$, ]", "", s)

    # Basic sanity check
    if not re.match(r"^-?\d+(\.\d+)?$", s):
        raise ValueError(f"Not a valid number: {s!r}")

    return float(s)

def prompt_date() -> str:
    """
    Returns YYYY-MM-01.
    Default: current month (local time).
    """

    today = date.today()
    default = date(today.year, today.month, 1).strftime("%Y-%m-%d")

    raw = input(f"Date for this entry (YYYY-MM-01) [default {default}]: ").strip()
    if raw =="":
        return default

    # Allow YYYY-MM or YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}$", raw):
        raw = raw + "-01"

    try:
        dt = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError("Date must be YYYY-MMM-01 (or YYYY-MM, or YYYY-MM-DD).") from ValueError
    
    #Normalize to first of Month
    dt = date(dt.year, dt.month, 1)
    return dt.strftime("%Y-%m-%d")

def read_existing_dates(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if "date" not in (reader.fieldnames or []):
            raise ValueError(f"{path} is missing required 'date' column.")
        return {row["date"] for row in reader if row.get("date")}

def ensure_csv_header(path: Path, fieldnames: List[str]) -> None:
    """
    Create file with header if it doesn't exist.
    If it exists, validate header contains required columns.
    """

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return

    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        existing = reader.fieldnames or []
    missing = [c for c in fieldnames if c not in existing]
    if missing:
        raise ValueError(
            f"{path} header missing columns: {missing}. "
            f"Existing columns: {existing}"
        )

def prompt_balances(accounts: List[str]) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for acct in accounts:
        while True:
            raw = input(f"{acct} balance: ").strip()
            try:
                values[acct] = parse_money(raw)
                break
            except ValueError as e:
                print(f"  {e}. Try again (examples: 1234.56, $1,234.56).")
    return values

def append_row(path: Path, row: Dict[str, object], fieldnames: List[str]) -> None:
    with path.open("a", newline= "") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

def main():
    fieldnames= ["date"] + ACCOUNTS
    ensure_csv_header(CSV_Path, fieldnames)

    entry_date = prompt_date()
    existing_dates = read_existing_dates(CSV_Path)

    if entry_date in existing_dates:
        print(f"\n An entry for {entry_date} already exists in {CSV_Path}.")
        ans = input("Do you want to append anyway? (type YES to force append): ").strip()
        if ans != "YES":
            print("Aborted (no changes made).")
            return
    print("n\Enter balances (you can values like $437,133.95):")
    balances = prompt_balances(ACCOUNTS)

    row: Dict[str, object] = {"date": entry_date, **balances}

    print("\nAbout to append this row:")
    for k in fieldnames:
        v = row[k]
        if k =="date":
            print(f"  {k}:  {v}")
        else:
            print(f"  {k}: {float(v):,.2f}")
    
    confirm = input("\nAppend to CSV? (y/N): ").strip().lower()
    if confirm !="y":
        print("Aborted (no changes made).")
        return

    append_row(CSV_Path, row, fieldnames)
    print(f"\n Append to {CSV_Path}")

if __name__ == "__main__":
    main()    
    



