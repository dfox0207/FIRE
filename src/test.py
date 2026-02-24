scenario_path = Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order: cfg["order"]

print(type(order))
print(order)