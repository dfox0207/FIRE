from pathlib import Path
import json
import pandas as pd

#def compute_taxes(annual_income):
annual_income = 10000

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
        tax = income_real * brackets[b]-std_deduct/12