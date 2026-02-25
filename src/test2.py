import pandas as pd

rows =[]
row = {'b457': 100, 'b403': 100, 'tsp': 100, 'roth': 100}
order = ['b457', 'b403', 'tsp', 'roth']

#update account balances in dictionary
for m in range(10):
    for acct in order:
        if row[acct] > 0:
            row[acct] -= 100


print(row)

#add row to list
rows.append(row)    

print(rows)

#convert list to dataframe
proj = pd.DataFrame(rows)

print(proj)