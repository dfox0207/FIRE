from pathlib import Path
import json

scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order= cfg["order"]

withdrawal = 60

b457 = 100
b403 = 100
tsp = 100
ROTH = 100
print("b457", "b403", "tsp", "ROTH")
for m in range(8):
    if b457 >0:
        if b457 < withdrawal:
            b457 = 0
            b457_rm = withdrawal-b457
            b403 -= b457_rm
        else:
            b457 -= withdrawal
    print(b457, b403, tsp, ROTH)
    elif b403 > 0:
        if b403 < withdrawal:
            b403 = 0
            b403_rm = withdrawal-b403
            tsp -= b403_rm
        else:
            b403 -= (withdrawal)
            
    print(b457, b403, tsp, ROTH)
    elif tsp >0:
        if tsp < withdrawal:
            tsp = 0
            tsp_rm = withdrawal-tsp
            ROTH -= tsp_rm
        else:
            tsp -= (withdrawal)
            
    print(b457, b403, tsp, ROTH)
    else:
        ROTH -= withdrawal
        b403_rm=0

    print(b457, b403, tsp, ROTH) 
