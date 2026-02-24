scenario_path = Path(sys.argv[1]) if len(sys.argv) >1 else Path("Config/test.json")
cfg = json.loads(scenario_path.read_text(encoding="utf-8"))

#2. Convert config values to proper Python types
order: cfg["order"]

print(type(order))
print(order)