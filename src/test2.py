import pandas as pd

rows =[]
row = {}

#add account balances to dictionary
row["b457"]= 100
row["b403"]= 100
row["tsp"] = 100
row["roth"]= 100

print(row)

#add row to list
rows.append(row)    

print(rows)

#convert list to dataframe
proj = pd.DataFrame(rows)

print(proj)