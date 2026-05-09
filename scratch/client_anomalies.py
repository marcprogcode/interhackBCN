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

# Calculate Average Baseline (Active clients only to have a meaningful comparison)
avg_active = client_monthly.replace(0, np.nan).mean(axis=0).fillna(0)
plot_dates = client_monthly.columns.to_timestamp()

# Define Anomalies
# 1. High-Spend Outliers: Clients who spent more than 10x the monthly average at least once
high_threshold = avg_active * 10
is_high_anomaly = (client_monthly > high_threshold).any(axis=1)

# 2. Sudden Drop Outliers: Clients who were spending > 1000 and dropped to < 100
# (excluding the universal August drop)
is_drop_anomaly = []
for client_id in client_monthly.index:
    row = client_monthly.loc[client_id]
    # Check for a drop of 90% in the last 6 months (excluding August)
    recent = row.iloc[-6:]
    historical = row.iloc[:-6]
    if historical.mean() > 1000 and recent.mean() < historical.mean() * 0.1:
        is_drop_anomaly.append(True)
    else:
        is_drop_anomaly.append(False)

is_drop_anomaly = pd.Series(is_drop_anomaly, index=client_monthly.index)

# Plotting
plt.figure(figsize=(15, 10))

# Plot Baseline
plt.plot(plot_dates, avg_active, label='AVERAGE ACTIVE CLIENT (Baseline)', color='black', linewidth=4, zorder=10)

# Plot Sudden Drops
# Get all drop anomalies
drop_spenders = client_monthly[is_drop_anomaly]
# Plot up to 15 to keep it readable but comprehensive
for cid in drop_spenders.head(15).index:
    plt.plot(plot_dates, client_monthly.loc[cid], alpha=0.5, linewidth=1.5, label=f'Dropped Client {cid}')

plt.title('Critical Drop Anomalies: High Spenders who stopped buying in 2025')
plt.ylabel('Monthly Expense')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig('c:\\Users\\hugca\\OneDrive\\Escriptori\\interhackBCN\\scratch\\client_drops.png')
print("Drop anomaly plot saved to scratch/client_drops.png")

print(f"\nTotal Critical Drop Anomalies found: {len(drop_spenders)}")
print("These are clients who averaged >€1000/mo historically but dropped to <10% in the last 6 months.")
