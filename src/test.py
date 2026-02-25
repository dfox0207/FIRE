from pathlib import Path
import json
import pandas as pd

scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order= cfg["order"]
balances = cfg["balances"]
print(balances)
print(type(blances))

# rows = []

# for m in range(8):
#     withdrawal = 60
#     row = {"Date": m}
#     for acct in order:
#         bal = balances_df.iloc[-1][acct]
#         if acct in row:
#             break
#         elif bal <= withdrawal:
#             remaining = withdrawal-bal
#             row[acct] = 0
#             row[acct+1] = balances_df.iloc[-1][acct+1] - remaining
#         elif bal == 0:
#             row[acct] = 0
#         else:
#             row[acct] = balances_df.iloc[-1][acct] - withdrawal
#     rows.append(row)

# proj = pd.DataFrame(rows)
# print(proj) 
