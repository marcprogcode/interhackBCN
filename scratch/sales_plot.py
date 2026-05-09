import pandas as pd
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
FILE_PATH = r'c:\Users\hugca\OneDrive\Escriptori\interhackBCN\datasets\Datasets.xlsx - Ventas.csv'
N_CLIENTS = 5000
MAX_INTERVAL_DIFF_DAYS = 60 

def load_and_clean_data(path):
    print("--- RUTHLESS DATA LOADING ---")
    df = pd.read_csv(path, low_memory=False)
    
    print("Cleaning values and dates...")
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    # Vectorized cleaning for speed
    df['Sales_Value'] = (df['Valores_H']
                         .str.replace('"', '', regex=False)
                         .str.replace('.', '', regex=False)
                         .str.replace(',', '.', regex=False)
                         .astype(float))
    return df

def detect_recurring_patterns(df):
    print(f"--- ANALYZING TOP {N_CLIENTS} CLIENTS ---")
    
    # Identify the Top N clients by total volume
    top_ids = df.groupby('Id. Cliente')['Sales_Value'].sum().nlargest(N_CLIENTS).index
    
    # Filter and pre-sort data for efficient iteration
    data = df[df['Id. Cliente'].isin(top_ids)].groupby(['Id. Cliente', 'Fecha'])['Sales_Value'].sum().reset_index()
    data = data.sort_values(['Id. Cliente', 'Fecha'])
    
    recurring_clients = []
    
    for client_id, group in data.groupby('Id. Cliente'):
        if len(group) < 3:
            continue
            
        # Calculate intervals in days
        intervals = group['Fecha'].diff().dt.days.dropna().values
        
        # Stability check
        interval_stability = abs(pd.Series(intervals).diff().dropna())
        
        if (interval_stability <= MAX_INTERVAL_DIFF_DAYS).all():
            recurring_clients.append({
                'id': client_id,
                'data': group,
                'avg_interval': intervals.mean(),
                'last_purchase': group['Fecha'].max(),
                'last_value': group.iloc[-1]['Sales_Value']
            })
            
    return recurring_clients

def plot_signals(recurring_clients, reference_date, top_n=15):
    print(f"--- GENERATING SIGNAL PLOT (Top {top_n} clients with signals) ---")
    
    clients_with_signals = []
    for c in recurring_clients:
        c_signals = []
        dates = c['data']['Fecha'].tolist()
        values = c['data']['Sales_Value'].tolist()
        
        margin = pd.Timedelta(days=MAX_INTERVAL_DIFF_DAYS)
        
        # Retroactive signals
        for j in range(len(dates) - 1):
            expected_date = dates[j] + pd.Timedelta(days=c['avg_interval'])
            if expected_date + margin < dates[j+1]:
                c_signals.append((dates[j], values[j], expected_date))
                
        # Current signal
        expected_date = c['last_purchase'] + pd.Timedelta(days=c['avg_interval'])
        if expected_date + margin < reference_date:
            c_signals.append((c['last_purchase'], c['last_value'], expected_date))
            
        if c_signals:
            c['signals'] = c_signals
            clients_with_signals.append(c)
            
    # Sort by how "recent" their last purchase was to show active churn
    clients_with_signals = sorted(clients_with_signals, key=lambda x: x['last_purchase'], reverse=True)
    
    # --- Generate Markdown of Alerts ---
    md_lines = ["# Sales Alerts\n", "| Client ID | Date of Alert |", "|-----------|---------------|"]
    has_alerts = False
    for client in clients_with_signals:
        for _, _, exp_date in client['signals']:
            md_lines.append(f"| {client['id']} | {exp_date.strftime('%Y-%m-%d')} |")
            has_alerts = True
            
    if has_alerts:
        md_path = os.path.join(os.path.dirname(__file__), 'sales_alerts.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines) + '\n')
        print(f"Alerts Markdown saved successfully at {md_path}")

    to_plot = clients_with_signals[:top_n]
    
    for i, client in enumerate(to_plot):
        plt.figure(figsize=(16, 9))
        
        # 1. Plot historical data
        plt.plot(client['data']['Fecha'], client['data']['Sales_Value'], 
                 label=f"Client {client['id']}", marker='o', markersize=4, alpha=0.7)
        
        # 2. Plot all signals (Historical & Current)
        for last_date, last_val, exp_date in client['signals']:
            # Plot the "Missing" interval (Dashed Red Line)
            plt.plot([last_date, exp_date], [last_val, last_val], 
                     linestyle='--', color='red', alpha=0.6)
            
            # Mark the Signal with an X
            plt.scatter(exp_date, last_val, color='red', marker='x', s=120, zorder=5)
            
            # Label the signal
            plt.text(exp_date, last_val, f"  Signal {client['id']}", verticalalignment='bottom', color='red', fontsize=9)

        # 3. Today line
        plt.axvline(x=reference_date, color='black', linestyle='-', linewidth=2, label=f"TODAY ({reference_date.date()})")

        plt.title(f"Sales Signals: Client {client['id']} Missed Cycle", fontsize=18, fontweight='bold')
        plt.xlabel("Date", fontsize=14)
        plt.ylabel("Sales Value", fontsize=14)
        plt.grid(True, linestyle=':', alpha=0.3)
        
        # Create a proxy for the legend signal marker
        from matplotlib.lines import Line2D
        custom_lines = [Line2D([0], [0], color='red', marker='x', linestyle='--', markersize=10, label='Lapsed Signal')]
        
        handles, labels = plt.gca().get_legend_handles_labels()
        handles.extend(custom_lines)
        
        plt.legend(handles=handles, bbox_to_anchor=(1.01, 1), loc='upper left')
        plt.tight_layout()
        
        output_path = os.path.join(os.path.dirname(__file__), f'sales_signal_plot_client_{client["id"]}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Signal plot saved successfully at {output_path}")

if __name__ == "__main__":
    try:
        raw_df = load_and_clean_data(FILE_PATH)
        today = raw_df['Fecha'].max()
        recurring_list = detect_recurring_patterns(raw_df)
        
        plot_signals(recurring_list, today)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
