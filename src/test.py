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

for m in range(8):
    if b457 >0:
        if b457 < withdrawal:
            b457 = 0
            b457_rm = withdrawal-b457
        else:
            b457 -= withdrawal
    elif b403 > 0:
        if b403 < withdrawal+b457_rm:
            b403 = 0
            b403_rm = withdrawal+b457_rm-b403
            b457_rm=0
        else:
            b403 -= (withdrawal+b403_rm)
            b457_rm=0
    elif tsp >0:
        if tsp < withdrawal+b403_rm:
            tsp = 0
            tsp_rm = withdrawal+b403-tsp
            b403_rm = 0
        else:
            tsp -= (withdrawal+b403)
            b403_rm = 0
    else:
        ROTH -= (withdrawal+b403_rm)
        b403_rm=0
