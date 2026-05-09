import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set aesthetic style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter', 'Roboto', 'Arial']

def clean_currency(x):
    """Converts Spanish formatted currency string to float."""
    if isinstance(x, str):
        # Remove thousands separator (dot) and replace decimal separator (comma) with dot
        # Example: "-3.931,91" -> "-3931.91"
        x = x.replace('.', '').replace(',', '.')
    try:
        return float(x)
    except:
        return 0.0

def analyze():
    print("Loading datasets...")
    ventas_path = os.path.join("data", "Datasets.xlsx - Ventas.csv")
    clientes_path = os.path.join("data", "Datasets.xlsx - Clientes.csv")
    
    if not os.path.exists(ventas_path):
        print(f"Error: {ventas_path} not found.")
        return

    # Read Ventas
    # Using low_memory=False to avoid DtypeWarning
    df_ventas = pd.read_csv(ventas_path, low_memory=False)
    
    print("Cleaning data...")
    # Convert dates
    df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], dayfirst=False)
    
    # Clean Valores_H
    df_ventas['Valores_H'] = df_ventas['Valores_H'].apply(clean_currency)
    
    # 1. Lifetime Purchasing Distribution
    ltv = df_ventas.groupby('Id. Cliente')['Valores_H'].sum().reset_index()
    ltv.columns = ['Id. Cliente', 'Lifetime_Value']
    
    # 2. Client Tenure Distribution
    tenure = df_ventas.groupby('Id. Cliente')['Fecha'].agg(['min', 'max']).reset_index()
    tenure['Tenure_Days'] = (tenure['max'] - tenure['min']).dt.days
    
    # Plotting
    print("Generating plots...")
    
    # Plot 1: Lifetime Value Distribution
    plt.figure(figsize=(12, 6))
    # We use log scale for LTV because it's usually very skewed (Pareto principle)
    # filter out negative or zero LTV for log scale if necessary, but here we just plot.
    # We'll use a histogram with a KDE
    sns.histplot(ltv['Lifetime_Value'], kde=True, bins=50, color='#4A90E2')
    plt.title('Distribution of Client Lifetime Purchasing Value', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Total Lifetime Value (€)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.tight_layout()
    plt.savefig('plots/lifetime_purchase_dist.png', dpi=300)
    print("Saved lifetime_purchase_dist.png")

    # Plot 2: Client Tenure Distribution
    plt.figure(figsize=(12, 6))
    sns.histplot(tenure['Tenure_Days'], kde=True, bins=50, color='#50C878')
    plt.title('Distribution of Client Tenure (Active Lifespan)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Days between First and Last Purchase', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.tight_layout()
    plt.savefig('plots/client_tenure_dist.png', dpi=300)
    print("Saved client_tenure_dist.png")

    # Bonus: Scatter plot of Tenure vs LTV
    plt.figure(figsize=(10, 8))
    merged = pd.merge(ltv, tenure, on='Id. Cliente')
    sns.scatterplot(data=merged, x='Tenure_Days', y='Lifetime_Value', alpha=0.5, color='#E94E77')
    plt.title('Relationship between Tenure and Lifetime Value', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Tenure (Days)', fontsize=12)
    plt.ylabel('Lifetime Value (€)', fontsize=12)
    plt.yscale('log') # Use log scale for Y as LTV varies wildly
    plt.tight_layout()
    plt.savefig('plots/tenure_vs_ltv.png', dpi=300)
    print("Saved tenure_vs_ltv.png")

    print("Analysis complete.")

def analyze_comparative():
    print("\nStarting comparative analysis (Top vs Bottom spenders)...")
    ventas_path = os.path.join("data", "Datasets.xlsx - Ventas.csv")
    df_ventas = pd.read_csv(ventas_path, low_memory=False)
    
    # Cleaning
    df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], dayfirst=False)
    df_ventas['Valores_H'] = df_ventas['Valores_H'].apply(clean_currency)
    
    # 1. Calculate Tenure and Avg Purchase Price
    client_stats = df_ventas.groupby('Id. Cliente').agg(
        Total_Value=('Valores_H', 'sum'),
        Num_Transactions=('Valores_H', 'count'),
        First_Date=('Fecha', 'min'),
        Last_Date=('Fecha', 'max')
    ).reset_index()
    
    client_stats['Tenure_Days'] = (client_stats['Last_Date'] - client_stats['First_Date']).dt.days
    client_stats['Avg_Purchase_Price'] = client_stats['Total_Value'] / client_stats['Num_Transactions']
    
    # 2. Filter tenure > 2 years (730 days)
    filtered_clients = client_stats[client_stats['Tenure_Days'] > 730].copy()
    print(f"Clients with > 2 years tenure: {len(filtered_clients)}")
    
    if len(filtered_clients) < 2:
        print("Not enough clients with > 2 years tenure.")
        return

    # 3. Define groups based on Avg_Purchase_Price
    q25 = filtered_clients['Avg_Purchase_Price'].quantile(0.25)
    q75 = filtered_clients['Avg_Purchase_Price'].quantile(0.75)
    
    bottom_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] <= q25]
    top_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] >= q75]
    
    print(f"Bottom 25% count: {len(bottom_25)} (Avg <= {q25:.2f}€)")
    print(f"Top 25% count: {len(top_25)} (Avg >= {q75:.2f}€)")
    
    # 4. Take a random sample from each group
    sample_size = min(100, len(bottom_25), len(top_25))
    bottom_sample_ids = bottom_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    top_sample_ids = top_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    
    # 5. Get all transactions for these sampled clients
    bottom_txs = df_ventas[df_ventas['Id. Cliente'].isin(bottom_sample_ids)]['Valores_H']
    top_txs = df_ventas[df_ventas['Id. Cliente'].isin(top_sample_ids)]['Valores_H']
    
    # 6. Plot Overlay
    plt.figure(figsize=(12, 7))
    
    # Use a log scale for the X axis because purchase prices can be very skewed
    # and handle potential zero/negative values for log scale
    bins = 100
    
    # Filter for positive values for a cleaner distribution plot if needed, 
    # but let's just plot the raw distribution first.
    sns.kdeplot(bottom_txs, label='Bottom 25% Spenders (Avg Price)', fill=True, color='#E94E77', alpha=0.5)
    sns.kdeplot(top_txs, label='Top 25% Spenders (Avg Price)', fill=True, color='#4A90E2', alpha=0.5)
    
    plt.title('Purchase Price Distribution Overlay (>2yr Tenure Clients)', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Individual Purchase Price (€)', fontsize=12)
    plt.ylabel('Density', fontsize=12)
    plt.legend()
    
    # Set x-axis limits to focus on the main distribution area
    # (assuming most transactions are in a certain range)
    all_sampled = pd.concat([bottom_txs, top_txs])
    plt.xlim(all_sampled.quantile(0.01), all_sampled.quantile(0.99))
    
    plt.tight_layout()
    plt.savefig('plots/spender_comparison_overlay.png', dpi=300)
    print("Saved spender_comparison_overlay.png")

def analyze_habits():
    print("\nStarting spending habits analysis (Line Chart)...")
    ventas_path = os.path.join("data", "Datasets.xlsx - Ventas.csv")
    df_ventas = pd.read_csv(ventas_path, low_memory=False)
    
    # Cleaning
    df_ventas['Fecha'] = pd.to_datetime(df_ventas['Fecha'], dayfirst=False)
    df_ventas['Valores_H'] = df_ventas['Valores_H'].apply(clean_currency)
    
    # 1. Identify Groups (reuse logic)
    client_stats = df_ventas.groupby('Id. Cliente').agg(
        Total_Value=('Valores_H', 'sum'),
        Num_Transactions=('Valores_H', 'count'),
        First_Date=('Fecha', 'min'),
        Last_Date=('Fecha', 'max')
    ).reset_index()
    
    client_stats['Tenure_Days'] = (client_stats['Last_Date'] - client_stats['First_Date']).dt.days
    client_stats['Avg_Purchase_Price'] = client_stats['Total_Value'] / client_stats['Num_Transactions']
    
    filtered_clients = client_stats[client_stats['Tenure_Days'] > 730].copy()
    q25 = filtered_clients['Avg_Purchase_Price'].quantile(0.25)
    q75 = filtered_clients['Avg_Purchase_Price'].quantile(0.75)
    
    bottom_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] <= q25]
    top_25 = filtered_clients[filtered_clients['Avg_Purchase_Price'] >= q75]
    
    # 2. Sample 100 from each
    sample_size = 100
    bottom_sample_ids = bottom_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    top_sample_ids = top_25.sample(n=sample_size, random_state=42)['Id. Cliente']
    
    # 3. Aggregate spending by month for these samples
    def get_monthly_agg(sample_ids):
        txs = df_ventas[df_ventas['Id. Cliente'].isin(sample_ids)].copy()
        txs['Month'] = txs['Fecha'].dt.to_period('M').dt.to_timestamp()
        # Aggregate by month: sum of values
        monthly = txs.groupby('Month')['Valores_H'].sum().reset_index()
        return monthly

    bottom_monthly = get_monthly_agg(bottom_sample_ids)
    top_monthly = get_monthly_agg(top_sample_ids)
    
    # 4. Plot Line Chart
    plt.figure(figsize=(14, 8))
    
    # We plot both on the same graph. To compare "shape", we might want to normalize, 
    # but the user said "to compare if their spending habits follow eachother", 
    # which usually implies seeing the relative trends.
    
    # We'll use dual Y axes or normalize to show shape better if the scales are too different.
    # Let's check the scales first by plotting. Actually, I'll normalize to "Percentage of Group Max" 
    # or just plot them on separate axes if needed.
    # But wait, "aggregate line chart... on the same graph" suggests one axis or two.
    
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    color_bottom = '#E94E77'
    color_top = '#4A90E2'
    
    ax1.set_xlabel('Time (Month)', fontsize=12)
    ax1.set_ylabel('Bottom 25% Aggregate Monthly Spending (€)', color=color_bottom, fontsize=12)
    line1 = ax1.plot(bottom_monthly['Month'], bottom_monthly['Valores_H'], color=color_bottom, linewidth=2.5, label='Bottom 25% Group (N=100)', marker='o', markersize=4)
    ax1.tick_params(axis='y', labelcolor=color_bottom)
    
    ax2 = ax1.twinx()
    ax2.set_ylabel('Top 25% Aggregate Monthly Spending (€)', color=color_top, fontsize=12)
    line2 = ax2.plot(top_monthly['Month'], top_monthly['Valores_H'], color=color_top, linewidth=2.5, label='Top 25% Group (N=100)', marker='s', markersize=4)
    ax2.tick_params(axis='y', labelcolor=color_top)
    
    plt.title('Spending Habits Comparison: Top vs Bottom Spenders Over Time', fontsize=16, fontweight='bold', pad=20)
    
    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('plots/spending_habits_line_chart.png', dpi=300)
    print("Saved spending_habits_line_chart.png")

if __name__ == "__main__":
    analyze()
    analyze_comparative()
    analyze_habits()
