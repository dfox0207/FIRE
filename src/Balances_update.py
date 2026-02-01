from __future__ import annotations

import csv
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List

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
    
CSV_Path = get_csv_path()

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
    Returns a month-start date string in M/D/YYYY format (e.g., 2/1/2026).

    Input accepted:
      - blank (uses current month)
      - YYYY-MM
      - YYYY-MM-DD
      - M/D/YYYY or MM/DD/YYYY

    The stored/appended date is normalized to the *first* day of the month.
    """
    today = date.today()
    default_dt = date(today.year, today.month, 1)
    default = f"{default_dt.month}/{default_dt.day}/{default_dt.year}"

    raw = input(
        f"Date for this entry (month start) [default {default}]: "
    ).strip()

    if raw == "":
        return default

    # Allow YYYY-MM -> YYYY-MM-01
    if re.match(r"^\d{4}-\d{2}$", raw):
        raw = raw + "-01"

    # Try supported formats
    dt = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(raw, fmt).date()
            break
        except ValueError:
            continue

    if dt is None:
        raise ValueError(
            "Date must be YYYY-MM, YYYY-MM-DD, or M/D/YYYY (e.g., 2026-02, 2026-02-01, 2/1/2026)."
        )

    # Normalize to first of month
    dt = date(dt.year, dt.month, 1)
    return f"{dt.month}/{dt.day}/{dt.year}"

def read_existing_dates(path: Path) -> set[str]:
    """
    Returns existing Date values normalized to M/D/YYYY.
    This lets you detect duplicates even if older rows were saved as YYYY-MM-DD.
    """
    if not path.exists():
        return set()

    def _normalize_date_str(s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(s, fmt).date()
                dt = date(dt.year, dt.month, 1)
                return f"{dt.month}/{dt.day}/{dt.year}"
            except ValueError:
                continue
        return s  # unknown format; keep as-is

    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if "Date" not in (reader.fieldnames or []):
            raise ValueError(f"{path} is missing required 'Date' column.")
        return {
            _normalize_date_str(row.get("Date", ""))
            for row in reader
            if row.get("Date")
        }

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

def ensure_trailing_newline(path: Path) -> None:
    """
    Ensure the file ends with a newline before appending.

    If a CSV file's last line does not end with a newline character, appending a
    new row will appear to continue on the same line (i.e., "to the right" of
    the last entry). This fixes that by adding a newline when needed.
    """
    if not path.exists():
        return
    try:
        with path.open("rb") as fb:
            fb.seek(0, os.SEEK_END)
            if fb.tell() == 0:
                return  # empty file
            fb.seek(-1, os.SEEK_END)
            last = fb.read(1)
        if last not in (b"\n", b"\r"):
            # Force a newline so the next writerow starts on a fresh line.
            with path.open("a", newline="") as f:
                f.write("\n")
    except OSError:
        # If we can't read/seek for some reason, fall back to no-op.
        return

def append_row(path: Path, row: Dict[str, object], fieldnames: List[str]) -> None:
    ensure_trailing_newline(path)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

def main():
    fieldnames= ["Date"] + ACCOUNTS
    ensure_csv_header(CSV_Path, fieldnames)

    entry_date = prompt_date()
    existing_dates = read_existing_dates(CSV_Path)

    if entry_date in existing_dates:
        print(f"\n An entry for {entry_date} already exists in {CSV_Path}.")
        ans = input("Do you want to append anyway? (type YES to force append): ").strip()
        if ans != "YES":
            print("Aborted (no changes made).")
            return
    print("\nEnter balances (you can values like $437,133.95):")
    balances = prompt_balances(ACCOUNTS)

    row: Dict[str, object] = {"Date": entry_date, **balances}

    print("\nAbout to append this row:")
    for k in fieldnames:
        v = row[k]
        if k =="Date":
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
    