from pathlib import Path
import json
import pandas as pd

scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order= cfg["order"]
balances = cfg["balances"]
balances_df = pd.DataFrame.from_records(balances)


print("b457", "b403", "tsp", "ROTH")
print(b457, b403, tsp, ROTH)
for m in range(8):
    withdrawal = 60
    for acct in order:
        bal = df.at[-1, acct]
        if acct<= withdrawal
            remaining = withdrawal-bal
            bal = 0
            bal[?acct+1?] -=  remaining
        else:
            bal -= withdrawal
    

    print(b457, b403, tsp, ROTH) 
