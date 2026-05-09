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

# Get latest date in dataset
latest_date = sales['Fecha'].max()
print(f"Dataset ends at: {latest_date}")

# Group by Client and Month
sales['Month'] = sales['Fecha'].dt.to_period('M')
client_monthly = sales.groupby(['Id. Cliente', 'Month'])['Valores_H'].sum().unstack(fill_value=0)

# 1. Identify Churned Clients
# Definition: No transactions in the last 4 months (excluding August)
# Let's check the last 4 months present in the data
last_months = client_monthly.columns[-4:]
print(f"Analyzing last months: {list(last_months)}")

# Clients who were active before but have 0 in all last 4 months
active_before = client_monthly.iloc[:, :-4].sum(axis=1) > 0
inactive_recently = client_monthly.iloc[:, -4:].sum(axis=1) == 0
lost_clients = client_monthly[active_before & inactive_recently]

# 2. Identify Falling Clients
# Definition: Spending in the last 3 months is significantly lower than their previous average
recent_avg = client_monthly.iloc[:, -3:].mean(axis=1)
historical_avg = client_monthly.iloc[:, :-3].mean(axis=1)
# Only consider clients with significant historical spending
falling_clients = client_monthly[(historical_avg > 100) & (recent_avg < historical_avg * 0.5)]

print(f"\nTotal Clients: {len(client_monthly)}")
print(f"Lost Clients: {len(lost_clients)}")
print(f"Falling Clients: {len(falling_clients)}")

# 3. Plotting
plt.figure(figsize=(15, 10))

# Plot a sample of Lost Clients
plt.subplot(2, 1, 1)
sample_lost = lost_clients.head(10)
for client_id in sample_lost.index:
    plt.plot(client_monthly.columns.to_timestamp(), client_monthly.loc[client_id], label=f'Lost {client_id}', alpha=0.7)
plt.title('Spending Trends of Lost Clients (Sample)')
plt.ylabel('Monthly Expense')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Plot a sample of Falling Clients
plt.subplot(2, 1, 2)
sample_falling = falling_clients.head(10)
for client_id in sample_falling.index:
    plt.plot(client_monthly.columns.to_timestamp(), client_monthly.loc[client_id], label=f'Falling {client_id}', alpha=0.7)
plt.title('Spending Trends of Falling Clients (Sample)')
plt.ylabel('Monthly Expense')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
plt.savefig('c:\\Users\\hugca\\OneDrive\\Escriptori\\interhackBCN\\scratch\\client_churn.png')
print("\nClient analysis plot saved to scratch/client_churn.png")

# Output some details for explanation
print("\n--- Example Lost Clients (Avg Historical Spending) ---")
print(historical_avg.loc[sample_lost.index])

print("\n--- Example Falling Clients (Historical vs Recent) ---")
comparison = pd.DataFrame({
    'Hist_Avg': historical_avg.loc[sample_falling.index],
    'Recent_Avg': recent_avg.loc[sample_falling.index]
})
print(comparison)
