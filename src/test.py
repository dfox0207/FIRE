from pathlib import Path
import json
import pandas as pd

#def compute_taxes(annual_income):
annual_income = 10000
income_real = 5000

std_deduct = 15000
brackets = {
    0:0.10, 
    11925:0.12, 
    48475:0.22,
    103350:0.24,
    197300:0.32,
    250525:0.35,
    626350:0.37
    626351:0.37
}


for b in brackets.keys():
    if annual_income > b and annual_income<=b+1:
        taxable_income = income_real -std_deduct/12
        tax = taxable_income*brackets[b]

        break
print(f"bracket= {b}")
print(f"bracket= {brackets[b]}")
print(f"taxable income= {taxable_income}")
print(f"tax= {tax}")