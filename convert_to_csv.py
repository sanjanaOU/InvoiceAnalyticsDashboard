import pandas as pd

# Load Excel file
df = pd.read_excel("data/Online Retail.xlsx")

# Save as CSV
df.to_csv("data/online_retail.csv", index=False)

print(" Converted Excel to CSV successfully.")
