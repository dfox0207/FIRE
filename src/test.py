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
    626350:0.37,
    626351:0.37
}


for b in brackets.keys():
    tax = income_real*brackets[b]
    print(f"{b}= {tax}")
