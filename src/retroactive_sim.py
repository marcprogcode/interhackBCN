import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import timedelta
from data_loader import DataLoader

# Style
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.facecolor'] = '#121212'
plt.rcParams['figure.facecolor'] = '#121212'
plt.rcParams['grid.color'] = '#333333'

class RetroactiveSimulator:
    def __init__(self, data_dir="data", plots_dir="plots"):
        self.loader = DataLoader(data_dir=data_dir)
        self.plots_dir = plots_dir
        if not os.path.exists(plots_dir):
            os.makedirs(plots_dir)

    def run_simulation(self, client_id, family):
        print(f"Running retroactive simulation for Client {client_id} ({family})...")
        df = self.loader.get_merged_data()
        
        # Filter data for this specific client and family
        client_data = df[(df['Id. Cliente'] == client_id) & (df['Familia_H'] == family)].copy()
        client_data = client_data.sort_values('Fecha')
        
        if len(client_data) < 3:
            print("Not enough history for this client to calculate patterns.")
            return
            
        start_date = client_data['Fecha'].iloc[0] + timedelta(days=180) # Start after 6 months of data
        end_date = df['Fecha'].max()
        
        simulation_results = []
        trigger_dates = []
        currently_triggered = False
        
        # Iterate day by day
        current_sim_date = start_date
        while current_sim_date <= end_date:
            # Data available to the model at this specific point in time
            history = client_data[client_data['Fecha'] < current_sim_date]
            unique_dates = history['Fecha'].drop_duplicates().sort_values()
            
            if len(unique_dates) >= 3:
                # Calculate metrics exactly like the prioritization engine
                history_ipt = unique_dates.diff().dt.days.dropna()
                # Use recent history to adapt over time (e.g. last 5 intervals)
                median_ipt = history_ipt.tail(5).median()
                
                last_purchase = unique_dates.iloc[-1]
                dslp = (current_sim_date - last_purchase).days
                
                # Threshold logic
                expected_date = last_purchase + timedelta(days=median_ipt)
                if expected_date.month == 8:
                    threshold = median_ipt + 30
                else:
                    threshold = median_ipt * 1.5
                
                is_triggered = dslp > threshold
                
                if is_triggered and not currently_triggered:
                    trigger_dates.append(current_sim_date)
                    currently_triggered = True
                elif not is_triggered:
                    currently_triggered = False
                
                simulation_results.append({
                    'Date': current_sim_date,
                    'DSLP': dslp,
                    'Threshold': threshold,
                    'Triggered': is_triggered
                })
            
            current_sim_date += timedelta(days=1)
            
        self.plot_results(client_id, family, client_data, simulation_results, trigger_dates)

    def plot_results(self, client_id, family, client_data, sim_results, trigger_dates):
        sim_df = pd.DataFrame(sim_results)
        
        plt.figure(figsize=(15, 8))
        
        # Plot 1: DSLP vs Threshold
        ax1 = plt.gca()
        ax1.plot(sim_df['Date'], sim_df['DSLP'], color='#00f2ff', label='Days Since Last Purchase', linewidth=2)
        ax1.plot(sim_df['Date'], sim_df['Threshold'], color='#ffaa00', linestyle='--', label='Alert Threshold', alpha=0.7)
        
        # Highlight trigger points
        for i, t_date in enumerate(trigger_dates):
            label = 'TRIGGER POINT' if i == 0 else ""
            ax1.axvline(x=t_date, color='#ff0055', linewidth=2, label=label, alpha=0.8)
            ax1.scatter(t_date, sim_df[sim_df['Date'] == t_date]['DSLP'].values[0], 
                       color='#ff0055', s=150, zorder=5, edgecolors='white')
            
            # Label the trigger date
            plt.annotate(f"{t_date.strftime('%Y-%m-%d')}", 
                         xy=(t_date, sim_df[sim_df['Date'] == t_date]['DSLP'].values[0]),
                         xytext=(-40, 30), textcoords='offset points',
                         arrowprops=dict(arrowstyle='->', color='#ff0055', lw=1.5),
                         fontsize=10, color='#ff0055', fontweight='bold',
                         bbox=dict(boxstyle='round', facecolor='#121212', edgecolor='#ff0055'))

        # Add purchases as markers on the x-axis or at the bottom
        for _, row in client_data.iterrows():
            if row['Fecha'] >= sim_df['Date'].min():
                plt.axvline(x=row['Fecha'], color='white', alpha=0.2, linestyle=':')
                plt.scatter(row['Fecha'], 0, color='white', marker='^', s=50, alpha=0.5)

        plt.title(f"Retroactive Simulation: When would Client {client_id} have triggered?", fontsize=20, color='#00f2ff', pad=25)
        plt.xlabel("Simulation Date", fontsize=12, color='#888888')
        plt.ylabel("Days Since Last Purchase", fontsize=12, color='#888888')
        
        # Prevent duplicate labels in legend
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys(), loc='upper left', frameon=True, facecolor='#1e1e1e', edgecolor='#333333')
        
        plt.grid(True, alpha=0.1)
        
        # Add "When & Why" explanation for the first trigger
        if trigger_dates:
            first_t = trigger_dates[0]
            days_overdue = sim_df[sim_df['Date'] == first_t]['DSLP'].values[0]
            thresh = sim_df[sim_df['Date'] == first_t]['Threshold'].values[0]
            explanation = (f"FIRST TRIGGER: {first_t.strftime('%B %d, %Y')}\n\n"
                          f"WHY: Client missed their usual pattern.\n"
                          f"They reached {days_overdue:.0f} days without\n"
                          f"purchasing, crossing the threshold of {thresh:.0f}\n"
                          f"days (1.5x their recent median interval).\n"
                          f"Total triggers: {len(trigger_dates)}")
            
            props = dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.9, edgecolor='#00f2ff')
            plt.text(0.98, 0.05, explanation, transform=plt.gca().transAxes, fontsize=12,
                    verticalalignment='bottom', horizontalalignment='right', bbox=props, color='white')

        filename = f"retro_alert_{client_id}.png"
        save_path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        print(f"Saved retroactive plot to {save_path}")
        plt.close()

if __name__ == "__main__":
    # Ensure src is in path if running from root
    import sys
    sys.path.append('src')
    from data_loader import DataLoader
    
    sim = RetroactiveSimulator()
    # Test top clients
    sim.run_simulation(30696, "Familia C2")
    sim.run_simulation(35217, "Familia C1")
