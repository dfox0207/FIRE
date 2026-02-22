import json
import sys
from pathlib import Path

from engine import project_balance

sys.path.insert(0, str(Path(__file__).resolve().parent))

def load_scenario(path: Path) -> dict:
    with path.open("r", encoding= "utf-8") as f:
        return json.load(f)

def main():
    #Choose scenario file from command line, default to base.json
    scenario_path = Path(sys.argv[1]) if len(sys.argv) >1 else Path("Config/base.json")

    cfg = load_scenario(scenario_path)

    balances = project_balance(
        start_balance = cfg["start_balance"],
        monthly_contribution = cfg["monthly_contribution"],
        annual_return = cfg["annual_return"],
        months = cfg["months"],
    )

    print(f"Scenario: {scenario_path}")
    print(f"Start:    {balances[0]:,.2f}")
    print(f"End:      {balances[-1]:,.2f}")
    print(f"Months:   {cfg['months']}")
    print(f"Last 5 balances: {[round(x,2) for x in balances[-5:]]}")

if __name__ == "__main__":
     main()
