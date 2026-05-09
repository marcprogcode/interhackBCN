import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
sales_path = r'c:\Users\hugca\OneDrive\Escriptori\interhackBCN\datasets\Datasets.xlsx - Ventas.csv'

# Load data
sales = pd.read_csv(sales_path)

# Clean Valores_H
def clean_currency(x):
    if isinstance(x, str):
        x = x.replace('.', '').replace(',', '.')
    return float(x)

sales['Valores_H'] = sales['Valores_H'].apply(clean_currency)
sales['Fecha'] = pd.to_datetime(sales['Fecha'], format='mixed')

# Aggregate by month
sales['Month'] = sales['Fecha'].dt.to_period('M')
monthly_stats = sales.groupby('Month').agg({
    'Valores_H': 'sum',
    'Id. Cliente': 'nunique'
}).rename(columns={'Id. Cliente': 'Active_Clients'})

# Plot
fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.set_xlabel('Month')
ax1.set_ylabel('Total Revenue', color='tab:blue')
ax1.plot(monthly_stats.index.to_timestamp(), monthly_stats['Valores_H'], color='tab:blue', label='Revenue')
ax1.tick_params(axis='y', labelcolor='tab:blue')

ax2 = ax1.twinx()
ax2.set_ylabel('Active Clients', color='tab:red')
ax2.plot(monthly_stats.index.to_timestamp(), monthly_stats['Active_Clients'], color='tab:red', linestyle='--', label='Active Clients')
ax2.tick_params(axis='y', labelcolor='tab:red')

plt.title('Total Revenue vs Active Clients Over Time')
plt.tight_layout()
plt.savefig('c:\\Users\\hugca\\OneDrive\\Escriptori\\interhackBCN\\scratch\\revenue_vs_clients.png')
print("Revenue vs Clients plot saved.")
print("\n--- Monthly Stats ---")
print(monthly_stats.tail(12))
