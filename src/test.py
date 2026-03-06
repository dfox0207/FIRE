from pathlib import Path
import json
import pandas as pd

#def compute_taxes(annual_income):
annual_income = 10000
income_real = 5000

std_deduct = 15000
brackets = {
    11925:0.10, 
    48475:0.12, 
    103350:0.22,
    197300:0.24,
    250525:0.32,
    626350:0.35,
    626351:0.37
}


for b in brackets.keys():
    if annual_income <= b:
        taxable_income = income_real -std_deduct/12
        tax = taxable_income*brackets[b]

print(f"taxable income= {taxable_income}")
print(f"bracket= {b}")
print(f"bracket= {brackets[b]}")
print(f"tax= {tax}")