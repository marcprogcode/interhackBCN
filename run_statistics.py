import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def clean_currency(x):
    if isinstance(x, str):
        x = x.replace('.', '').replace(',', '.')
    try:
        return float(x)
    except:
        return 0.0

def run_statistical_analysis():
    print("--- Loading Data ---")
    ventas_path = os.path.join("datasets", "Datasets.xlsx - Ventas.csv")
    df_ventas = pd.read_csv(ventas_path, low_memory=False)
    
    df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], dayfirst=False)
    df_ventas['Valores_H'] = df_ventas['Valores_H'].apply(clean_currency)
    
    print("\n--- 1. & 2. Lifetime Value & Tenure Statistics ---")
    client_stats = df_ventas.groupby('Id. Cliente').agg(
        Total_Value=('Valores_H', 'sum'),
        Num_Transactions=('Valores_H', 'count'),
        First_Date=('Fecha', 'min'),
        Last_Date=('Fecha', 'max')
    ).reset_index()
    
    client_stats['Tenure_Days'] = (client_stats['Last_Date'] - client_stats['First_Date']).dt.days
    
    ltv = client_stats['Total_Value']
    tenure = client_stats['Tenure_Days']
    
    print(f"Total Clients: {len(client_stats)}")
    
    print("\n[Lifetime Value (LTV)]")
    print(f"  Mean: {ltv.mean():.2f}")
    print(f"  Median: {ltv.median():.2f}")
    print(f"  Std Dev: {ltv.std():.2f}")
    print(f"  Skewness: {ltv.skew():.2f}")
    print(f"  Kurtosis: {ltv.kurtosis():.2f}")
    print(f"  Percentiles (25, 50, 75, 90): {np.percentile(ltv, [25, 50, 75, 90])}")

    print("\n[Tenure (Days)]")
    print(f"  Mean: {tenure.mean():.2f}")
    print(f"  Median: {tenure.median():.2f}")
    print(f"  Std Dev: {tenure.std():.2f}")
    print(f"  Percentiles (25, 50, 75, 90): {np.percentile(tenure, [25, 50, 75, 90])}")

    print("\n--- 3. Correlation: Tenure vs LTV ---")
    pearson_corr, p_val_p = stats.pearsonr(tenure, ltv)
    spearman_corr, p_val_s = stats.spearmanr(tenure, ltv)
    print(f"  Pearson Correlation: {pearson_corr:.4f} (p-value: {p_val_p:.4e})")
    print(f"  Spearman Correlation: {spearman_corr:.4f} (p-value: {p_val_s:.4e})")
    
    print("\n--- 4. Comparative Analysis (Top 25% vs Bottom 25%, >2yr Tenure) ---")
    client_stats['Avg_Purchase_Price'] = client_stats['Total_Value'] / client_stats['Num_Transactions']
    filtered_clients = client_stats[client_stats['Tenure_Days'] > 730].copy()
    
    q25 = filtered_clients['Avg_Purchase_Price'].quantile(0.25)
    q75 = filtered_clients['Avg_Purchase_Price'].quantile(0.75)
    
    bottom_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] <= q25]
    top_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] >= q75]
    
    sample_size = 500
    bottom_sample_ids = bottom_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    top_sample_ids = top_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    
    bottom_txs = df_ventas[df_ventas['Id. Cliente'].isin(bottom_sample_ids)]['Valores_H']
    top_txs = df_ventas[df_ventas['Id. Cliente'].isin(top_sample_ids)]['Valores_H']

    print("\n[Transaction Value Distributions]")
    print(f"  Bottom 25% Sample - Mean Tx Value: {bottom_txs.mean():.2f}, Variance: {bottom_txs.var():.2f}")
    print(f"  Top 25% Sample - Mean Tx Value: {top_txs.mean():.2f}, Variance: {top_txs.var():.2f}")
    
    # Mann-Whitney U test (non-parametric test for difference in distributions)
    u_stat, p_val_mw = stats.mannwhitneyu(bottom_txs, top_txs, alternative='two-sided')
    print(f"  Mann-Whitney U Test (Distribution difference): U={u_stat:.2f}, p-value={p_val_mw:.4e}")

    # Levene's test for equality of variances
    stat_levene, p_val_levene = stats.levene(bottom_txs, top_txs)
    print(f"  Levene's Test (Variance difference): W={stat_levene:.2f}, p-value={p_val_levene:.4e}")

    print("\n--- 5. Time Series Trend Comparison (Excluding August) ---")
    # Aggregate by month to compare shapes, explicitly excluding August
    def get_monthly_agg(sample_ids):
        txs = df_ventas[df_ventas['Id. Cliente'].isin(sample_ids)].copy()
        txs = txs[txs['Fecha'].dt.month != 8]
        txs['Month'] = txs['Fecha'].dt.to_period('M').dt.to_timestamp()
        monthly = txs.groupby('Month')['Valores_H'].sum().reset_index()
        return monthly

    bottom_monthly = get_monthly_agg(bottom_sample_ids)
    top_monthly = get_monthly_agg(top_sample_ids)

    # Merge on Month to ensure we compare the exact same time periods
    merged_monthly = pd.merge(bottom_monthly, top_monthly, on='Month', suffixes=('_Bottom', '_Top')).dropna()
    
    ts_pearson, ts_p_val = stats.pearsonr(merged_monthly['Valores_H_Bottom'], merged_monthly['Valores_H_Top'])
    print(f"  Pearson Correlation between monthly aggregates: {ts_pearson:.4f} (p-value: {ts_p_val:.4e})")

if __name__ == "__main__":
    run_statistical_analysis()
