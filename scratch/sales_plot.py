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

def plot_signals(recurring_clients, reference_date, top_n=5):
    print(f"--- GENERATING SIGNAL PLOT (Top {top_n} overdue clients) ---")
    plt.figure(figsize=(16, 9))
    
    # Filter for overdue clients
    overdue_clients = [c for c in recurring_clients if (c['last_purchase'] + pd.Timedelta(days=c['avg_interval'])) < reference_date]
    
    # Sort by how "recent" their last purchase was to show active churn
    overdue_clients = sorted(overdue_clients, key=lambda x: x['last_purchase'], reverse=True)
    
    to_plot = overdue_clients[:top_n]
    
    for i, client in enumerate(to_plot):
        # 1. Plot historical data
        plt.plot(client['data']['Fecha'], client['data']['Sales_Value'], 
                 label=f"Client {client['id']}", marker='o', markersize=4, alpha=0.7)
        
        # 2. Calculate Expected Date
        expected_date = client['last_purchase'] + pd.Timedelta(days=client['avg_interval'])
        
        # 3. Plot the "Missing" interval (Dashed Red Line)
        plt.plot([client['last_purchase'], expected_date], [client['last_value'], client['last_value']], 
                 linestyle='--', color='red', alpha=0.6)
        
        # 4. Mark the Signal with an X
        plt.scatter(expected_date, client['last_value'], color='red', marker='x', s=120, zorder=5)
        
        # Label the signal
        plt.text(expected_date, client['last_value'], f"  Signal {client['id']}", verticalalignment='bottom', color='red', fontsize=9)

    # 5. Today line
    plt.axvline(x=reference_date, color='black', linestyle='-', linewidth=2, label=f"TODAY ({reference_date.date()})")

    plt.title(f"Sales Signals: Recurring Clients who missed their Cycle", fontsize=18, fontweight='bold')
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
    
    output_path = os.path.join(os.path.dirname(__file__), 'sales_signal_plot.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Signal plot saved successfully at {output_path}")

if __name__ == "__main__":
    try:
        raw_df = load_and_clean_data(FILE_PATH)
        today = raw_df['Fecha'].max()
        recurring_list = detect_recurring_patterns(raw_df)
        
        plot_signals(recurring_list, today)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
