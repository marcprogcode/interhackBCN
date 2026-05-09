import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import timedelta
from data_loader import DataLoader

# Set style for a premium look
plt.style.use('dark_background')
sns.set_palette("husl")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.facecolor'] = '#121212'
plt.rcParams['figure.facecolor'] = '#121212'
plt.rcParams['grid.color'] = '#333333'

class AlertVisualizer:
    def __init__(self, data_dir="data", output_dir="outputs", plots_dir="plots"):
        self.loader = DataLoader(data_dir=data_dir)
        self.output_dir = output_dir
        self.plots_dir = plots_dir
        if not os.path.exists(plots_dir):
            os.makedirs(plots_dir)

    def load_data(self):
        self.df = self.loader.get_merged_data()
        self.alerts_df = pd.read_csv(os.path.join(self.output_dir, 'daily_alerts.csv'))
        self.current_date = self.df['Fecha'].max()

    def plot_replenishment_alert(self, alert_row, top_n=1):
        client_id = alert_row['Client_ID']
        family = alert_row['Product_Family']
        reason = alert_row['Reason']
        
        # Get history
        client_data = self.df[(self.df['Id. Cliente'] == client_id) & (self.df['Familia_H'] == family)].copy()
        client_data = client_data.sort_values('Fecha')
        
        # Extract details from reason string if possible, or recalculate
        # Reason format: "Overdue by 377 days (Expected IPT: 70)"
        try:
            expected_ipt = float(reason.split('Expected IPT: ')[1].split(')')[0])
        except:
            expected_ipt = client_data['Fecha'].diff().dt.days.median()

        last_purchase = client_data['Fecha'].iloc[-1]
        expected_date = last_purchase + timedelta(days=expected_ipt)
        
        plt.figure(figsize=(14, 7))
        
        # Plot historical purchases
        plt.scatter(client_data['Fecha'], client_data['Valores_H'], 
                    s=100, alpha=0.6, edgecolors='white', label='Past Purchases', color='#00f2ff')
        
        # Plot current date line
        plt.axvline(x=self.current_date, color='#ff0055', linestyle='--', linewidth=2, label='Alert Triggered (Today)')
        
        # Plot expected date line
        plt.axvline(x=expected_date, color='#ffaa00', linestyle=':', linewidth=2, label='Expected Purchase Date')
        
        # Fill the "Overdue" area
        plt.axvspan(expected_date, self.current_date, color='#ff0055', alpha=0.1, label='Overdue Window')
        
        # Annotations
        plt.annotate(f"Last Purchase\n{last_purchase.strftime('%Y-%m-%d')}", 
                     xy=(last_purchase, client_data['Valores_H'].iloc[-1]),
                     xytext=(10, 20), textcoords='offset points',
                     arrowprops=dict(arrowstyle='->', color='white'),
                     fontsize=10, color='white')
        
        plt.title(f"Alert: {alert_row['Type']} - Client {client_id} ({family})", fontsize=18, color='#00f2ff', pad=20)
        plt.xlabel("Date", fontsize=12, color='#888888')
        plt.ylabel("Transaction Value (€)", fontsize=12, color='#888888')
        plt.legend(loc='upper left', frameon=True, facecolor='#1e1e1e', edgecolor='#333333')
        plt.grid(True, linestyle=':', alpha=0.3)
        
        # Add "Why" text box
        textstr = f"WHY TRIGGERED:\n\n{reason}\n\nAvg Value: {alert_row['Expected_Value']:.2f}€\nPriority Score: {alert_row['Priority_Score']:.0f}"
        props = dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.8, edgecolor='#ff0055')
        plt.text(0.98, 0.05, textstr, transform=plt.gca().transAxes, fontsize=11,
                verticalalignment='bottom', horizontalalignment='right', bbox=props, color='white')

        filename = f"alert_viz_{client_id}_{family.replace(' ', '_')}.png"
        save_path = os.path.join(self.plots_dir, filename)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        print(f"Saved plot to {save_path}")
        plt.close()

    def plot_churn_risk_alert(self, alert_row):
        client_id = alert_row['Client_ID']
        family = alert_row['Product_Family']
        reason = alert_row['Reason']
        
        # Get history
        client_data = self.df[(self.df['Id. Cliente'] == client_id) & (self.df['Familia_H'] == family)].copy()
        client_data = client_data.sort_values('Fecha')
        
        recent_start = self.current_date - timedelta(days=180)
        previous_start = self.current_date - timedelta(days=360)
        
        recent_vol = client_data[(client_data['Fecha'] > recent_start) & (client_data['Fecha'] <= self.current_date)]['Valores_H'].sum()
        prev_vol = client_data[(client_data['Fecha'] > previous_start) & (client_data['Fecha'] <= recent_start)]['Valores_H'].sum()
        
        # Create comparison plot
        plt.figure(figsize=(10, 6))
        periods = ['Previous 6 Months', 'Recent 6 Months']
        volumes = [prev_vol, recent_vol]
        
        colors = ['#00f2ff', '#ff0055']
        bars = plt.bar(periods, volumes, color=colors, alpha=0.8, edgecolor='white', width=0.6)
        
        plt.title(f"Alert: Churn Risk - Client {client_id} ({family})", fontsize=18, color='#ff0055', pad=20)
        plt.ylabel("Total Volume (€)", fontsize=12, color='#888888')
        
        # Add labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 10,
                    f'{height:.0f}€', ha='center', va='bottom', color='white', fontsize=12, fontweight='bold')

        # Add "Why" text box
        textstr = f"WHY TRIGGERED:\n\n{reason}\n\nPriority Score: {alert_row['Priority_Score']:.0f}"
        props = dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.8, edgecolor='#ff0055')
        plt.text(0.5, -0.2, textstr, transform=plt.gca().transAxes, fontsize=11,
                verticalalignment='top', horizontalalignment='center', bbox=props, color='white')

        filename = f"alert_viz_{client_id}_{family.replace(' ', '_')}.png"
        save_path = os.path.join(self.plots_dir, filename)
        plt.tight_layout(rect=[0, 0.1, 1, 1])
        plt.savefig(save_path, dpi=150)
        print(f"Saved plot to {save_path}")
        plt.close()

    def run(self, num_alerts=3):
        self.load_data()
        for i in range(min(num_alerts, len(self.alerts_df))):
            alert = self.alerts_df.iloc[i]
            if alert['Type'] == 'Replenishment':
                self.plot_replenishment_alert(alert)
            else:
                self.plot_churn_risk_alert(alert)

if __name__ == "__main__":
    visualizer = AlertVisualizer()
    visualizer.run(num_alerts=2)
