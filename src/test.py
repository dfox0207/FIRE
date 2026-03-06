from pathlib import Path
import json
import pandas as pd

#def compute_taxes(annual_income):
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
    print(f"{b}={brackets[b]}")