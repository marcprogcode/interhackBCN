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

# Group by Client and Month
sales['Month'] = sales['Fecha'].dt.to_period('M')
client_monthly = sales.groupby(['Id. Cliente', 'Month'])['Valores_H'].sum().unstack(fill_value=0)

# Convert period index to timestamp for plotting
plot_dates = client_monthly.columns.to_timestamp()

plt.figure(figsize=(15, 12))

# 1. Spending Tendency of ALL Clients
plt.subplot(2, 1, 1)
# Using very low alpha to see the density of 8000+ clients
for client_id in client_monthly.index:
    plt.plot(plot_dates, client_monthly.loc[client_id], color='gray', alpha=0.01, linewidth=0.5)
plt.title('Spending Tendency of ALL Clients (Density Plot)')
plt.ylabel('Monthly Expense')
plt.yscale('log') # Log scale helps see the distribution across different spending tiers
plt.grid(True, which="both", ls="-", alpha=0.2)

# 2. Spending Tendency of the AVERAGE Client
plt.subplot(2, 1, 2)
# Average of ALL clients (including those who spent 0 in a month)
average_spending = client_monthly.mean(axis=0)
# Average of only ACTIVE clients (excluding 0s)
active_only = client_monthly.replace(0, np.nan).mean(axis=0)

plt.plot(plot_dates, average_spending, label='Average (All Clients)', color='blue', linewidth=2)
plt.plot(plot_dates, active_only, label='Average (Active Clients only)', color='red', linestyle='--', linewidth=2)
plt.title('Average Client Spending Over Time')
plt.ylabel('Avg Monthly Expense')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('c:\\Users\\hugca\\OneDrive\\Escriptori\\interhackBCN\\scratch\\client_averages.png')
print("Average analysis plot saved.")

# Summary statistics for explanation
print("\n--- Summary Stats ---")
print(f"Overall Average Spending (incl. inactive): {average_spending.mean():.2f}")
print(f"Overall Average Spending (active only): {active_only.mean():.2f}")
print(f"Max individual monthly spend: {client_monthly.max().max():.2f}")
