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
 
    def plot_losing_interest_alert(self, alert_row):
        import numpy as np

        client_id = alert_row['Client_ID']
        family = alert_row['Product_Family']
        reason = alert_row['Reason']
        WINDOW_QUARTERS = 6
        
        # Pull authoritative metrics from the engine's alert (computed at simulated date)
        alert_slope = alert_row.get('Slope', None)
        alert_r2 = alert_row.get('R_Squared', None)
        alert_decay = alert_row.get('Decay_Rate', None)
        alert_drop = alert_row.get('Drop_From_Peak', None)
        alert_peak = alert_row.get('Peak_Quarter', None)
        alert_qtrs_to_zero = alert_row.get('Quarters_To_Zero', None)
        
        # Get history
        client_data = self.df[(self.df['Id. Cliente'] == client_id) & (self.df['Familia_H'] == family)].copy()
        client_data = client_data.sort_values('Fecha')
        
        # Resample into QUARTERLY volume buckets (same as engine)
        quarterly = client_data.set_index('Fecha').resample('QS')['Valores_H'].sum()
        quarterly = quarterly[quarterly.index <= self.current_date]
        
        all_y = quarterly.values.astype(float)
        all_labels = quarterly.index
        
        # Analysis window: last N quarters
        window = quarterly.tail(WINDOW_QUARTERS)
        w_y = window.values.astype(float)
        w_x = np.arange(len(w_y), dtype=float)
        w_labels = window.index
        
        # Fit OLS on the window (for chart overlay only)
        slope, intercept = np.polyfit(w_x, w_y, 1)
        y_pred = slope * w_x + intercept
        ss_res = np.sum((w_y - y_pred) ** 2)
        ss_tot = np.sum((w_y - np.mean(w_y)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        mean_volume = np.mean(w_y)
        decay_rate = slope / mean_volume if mean_volume > 0 else 0.0
        
        # Use alert metadata when available (authoritative, computed at simulated date)
        if alert_slope is not None and not np.isnan(alert_slope):
            slope = alert_slope
            # Recompute y_pred with alert slope for chart consistency
            intercept = np.mean(w_y) - slope * np.mean(w_x)
            y_pred = slope * w_x + intercept
        if alert_r2 is not None and not np.isnan(alert_r2):
            r_squared = alert_r2
        if alert_decay is not None and not np.isnan(alert_decay):
            decay_rate = alert_decay
        
        # Peak from full history (or from alert)
        peak_quarter = alert_peak if (alert_peak is not None and not np.isnan(alert_peak)) else quarterly.max()
        recent_quarter = w_y[-1]
        drop_from_peak = alert_drop if (alert_drop is not None and not np.isnan(alert_drop)) else (1.0 - (recent_quarter / peak_quarter) if peak_quarter > 0 else 0.0)
        
        # Quarters to zero
        quarters_to_zero = alert_qtrs_to_zero if (alert_qtrs_to_zero is not None and not np.isnan(alert_qtrs_to_zero)) else (min(12.0, abs(w_y[-1] / slope)) if slope < 0 and w_y[-1] > 0 else 12.0)
        
        # Rolling 2-quarter average on the full history
        quarterly_series = pd.Series(all_y, index=all_labels)
        rolling_avg = quarterly_series.rolling(window=2, min_periods=1).mean()
        
        # ============================================================
        # 3-PANEL FIGURE
        # ============================================================
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 0.8], hspace=0.35, wspace=0.3)
        
        # ---- PANEL 1: Quarterly Volume Bars + Trendline (window only) ----
        ax1 = fig.add_subplot(gs[0, 0])
        
        # Determine which bars are inside the analysis window
        window_start = w_labels[0]
        bar_colors = []
        bar_alpha = []
        for i, (date, vol) in enumerate(zip(all_labels, all_y)):
            if date >= window_start:
                # Inside analysis window — color by relative volume
                ratio = vol / peak_quarter if peak_quarter > 0 else 0
                if ratio > 0.6:
                    bar_colors.append('#00e676')
                elif ratio > 0.3:
                    bar_colors.append('#ffab00')
                else:
                    bar_colors.append('#ff1744')
                bar_alpha.append(0.85)
            else:
                # Outside window — grey, faded
                bar_colors.append('#555555')
                bar_alpha.append(0.3)
        
        for i, (date, vol) in enumerate(zip(all_labels, all_y)):
            ax1.bar(date, vol, width=60, color=bar_colors[i], alpha=bar_alpha[i],
                    edgecolor='#444444', linewidth=0.5)
        
        # Peak baseline reference line
        ax1.axhline(y=peak_quarter, color='#00e676', linewidth=1.5, linestyle='--', alpha=0.5,
                     label=f'Peak quarter: {peak_quarter:,.0f}€')
        
        # OLS trendline (only on window)
        ax1.plot(w_labels, y_pred, color='#ff6e40', linewidth=3, linestyle='--',
                 label=f'Trendline: {slope:+,.0f} €/qtr', zorder=5)
        
        # Window boundary
        ax1.axvline(x=window_start, color='#ffffff', linewidth=1.5, linestyle=':',
                     alpha=0.5, label=f'Analysis window start')
        ax1.axvspan(all_labels[0], window_start, color='#ffffff', alpha=0.03)
        
        # Zero line projection
        if slope < 0 and quarters_to_zero < 12:
            future_date = w_labels[-1] + pd.DateOffset(months=int(quarters_to_zero * 3))
            ax1.plot([w_labels[-1], future_date], [w_y[-1], 0],
                     color='#ff1744', linewidth=1.5, linestyle=':', alpha=0.6,
                     label=f'Zero in {quarters_to_zero:.0f} qtrs')
        
        ax1.set_title('Quarterly Volume + Trendline (analysis window)', fontsize=14, color='#e0e0e0', pad=10)
        ax1.set_ylabel('Volume (€)', fontsize=11, color='#aaaaaa')
        ax1.legend(loc='upper right', frameon=True, facecolor='#1e1e1e', edgecolor='#333333', fontsize=8)
        ax1.grid(True, linestyle=':', alpha=0.2)
        ax1.tick_params(axis='x', rotation=45, labelsize=8)
        
        # Slope annotation
        mid_idx = len(w_x) // 2
        ax1.annotate(f'slope = {slope:+,.0f} €/qtr\nR² = {r_squared:.2f}',
                     xy=(w_labels[mid_idx], y_pred[mid_idx]),
                     xytext=(20, 30), textcoords='offset points',
                     fontsize=11, color='#ff6e40', fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color='#ff6e40', lw=1.5),
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e1e1e', edgecolor='#ff6e40', alpha=0.9))
        
        # ---- PANEL 2: Full History Rolling Average with Peak Reference ----
        ax2 = fig.add_subplot(gs[0, 1])
        
        # Full history line
        ax2.plot(rolling_avg.index, rolling_avg.values, color='#00b0ff', linewidth=2.5,
                 label='2-Quarter Rolling Avg', zorder=4)
        ax2.scatter(all_labels, all_y, color='#ffffff', s=25, alpha=0.4, zorder=3, label='Quarterly values')
        
        # Peak reference
        ax2.axhline(y=peak_quarter, color='#00e676', linewidth=1.5, linestyle='--', alpha=0.4,
                     label=f'Peak: {peak_quarter:,.0f}€')
        
        # Shade the analysis window
        ax2.axvspan(window_start, all_labels[-1], color='#ff6e40', alpha=0.08, label='Analysis window')
        ax2.axvline(x=window_start, color='#ffffff', linewidth=1.5, linestyle=':', alpha=0.5)
        
        # Drop annotation at the end
        if len(rolling_avg) >= 2:
            last_val = rolling_avg.iloc[-1]
            ax2.annotate(f'↘ {drop_from_peak*100:.0f}% below peak',
                        xy=(rolling_avg.index[-1], last_val),
                        xytext=(-80, 25), textcoords='offset points',
                        fontsize=11, color='#ff1744', fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color='#ff1744', lw=2),
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1e1e1e', edgecolor='#ff1744', alpha=0.9))
        
        ax2.set_title('Full History — Rolling Average vs Peak', fontsize=14, color='#e0e0e0', pad=10)
        ax2.set_ylabel('Volume (€)', fontsize=11, color='#aaaaaa')
        ax2.legend(loc='upper right', frameon=True, facecolor='#1e1e1e', edgecolor='#333333', fontsize=8)
        ax2.grid(True, linestyle=':', alpha=0.2)
        ax2.tick_params(axis='x', rotation=45, labelsize=8)
        
        # ---- PANEL 3: Scorecard (uses authoritative alert values) ----
        ax3 = fig.add_subplot(gs[1, :])
        ax3.set_xlim(0, 10)
        ax3.set_ylim(0, 4)
        ax3.axis('off')
        
        from matplotlib.patches import FancyBboxPatch
        card = FancyBboxPatch((0.1, 0.2), 9.8, 3.5, boxstyle="round,pad=0.3",
                              facecolor='#1a1a2e', edgecolor='#333355', linewidth=2)
        ax3.add_patch(card)
        
        ax3.text(5, 3.4, f'⚠ LOSING INTEREST SCORECARD — Client {client_id} ({family})',
                fontsize=14, color='#ff6e40', fontweight='bold', ha='center', va='center',
                family='sans-serif')
        
        ax3.plot([0.5, 9.5], [3.0, 3.0], color='#333355', linewidth=1)
        
        metrics = [
            ('Decay Rate', f'{decay_rate*100:.1f}%/qtr', '#ff1744' if decay_rate < -0.15 else '#ffab00'),
            ('Slope', f'{slope:+,.0f} €/qtr', '#ff6e40'),
            ('R² Confidence', f'{r_squared:.2f}', '#00e676' if r_squared > 0.5 else '#ffab00'),
            ('Drop from Peak', f'{drop_from_peak*100:.0f}%', '#ff1744' if drop_from_peak > 0.5 else '#ffab00'),
            ('Peak Quarter', f'{peak_quarter:,.0f} €', '#00e676'),
            ('Recent Quarter', f'{recent_quarter:,.0f} €', '#ff1744' if recent_quarter < peak_quarter * 0.5 else '#ffffff'),
        ]
        
        col_positions = [1.2, 3.0, 4.8, 6.6, 8.0, 9.4]
        for idx, ((label, value, color), xpos) in enumerate(zip(metrics, col_positions)):
            ax3.text(xpos, 2.5, label, fontsize=9, color='#888888', ha='center', va='center')
            ax3.text(xpos, 1.9, value, fontsize=14, color=color, ha='center', va='center', fontweight='bold')
        
        formula_str = alert_row.get('Formula', 'N/A') if 'Formula' in alert_row.index else 'N/A'
        ax3.text(5, 0.9, f'FORMULA: {formula_str}',
                fontsize=8, color='#aaaaaa', ha='center', va='center', family='monospace',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#121212', edgecolor='#333333', alpha=0.8))
        
        priority = alert_row['Priority_Score']
        ax3.text(5, 0.4, f'PRIORITY SCORE: {priority:,.0f}',
                fontsize=12, color='#ff6e40', ha='center', va='center', fontweight='bold')
        
        fig.suptitle(f'Losing Interest Analysis — Client {client_id} ({family})',
                    fontsize=20, color='#00b0ff', fontweight='bold', y=0.98)

        filename = f"alert_viz_interest_{client_id}_{family.replace(' ', '_')}.png"
        save_path = os.path.join(self.plots_dir, filename)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved losing interest plot to {save_path}")
        plt.close()

    def run(self, num_alerts=10):
        self.load_data()
        
        # Try to find at least one of each type if available in top 50
        candidates = self.alerts_df.head(50)
        
        types_to_plot = ['Replenishment', 'Losing Interest', 'Churn Risk']
        plotted_count = 0
        
        for alert_type in types_to_plot:
            type_alerts = candidates[candidates['Type'] == alert_type]
            if not type_alerts.empty:
                alert = type_alerts.iloc[0]
                print(f"Plotting sample for {alert_type}...")
                if alert_type == 'Replenishment':
                    self.plot_replenishment_alert(alert)
                elif alert_type == 'Losing Interest':
                    self.plot_losing_interest_alert(alert)
                else:
                    self.plot_churn_risk_alert(alert)
                plotted_count += 1
        
        # Fill remaining with top alerts
        for i in range(min(num_alerts - plotted_count, len(self.alerts_df))):
            alert = self.alerts_df.iloc[i]
            # Skip if already plotted
            if any((candidates.iloc[:plotted_count]['Client_ID'] == alert['Client_ID']) & 
                   (candidates.iloc[:plotted_count]['Product_Family'] == alert['Product_Family'])):
                continue
                
            if alert['Type'] == 'Replenishment':
                self.plot_replenishment_alert(alert)
            elif alert['Type'] == 'Losing Interest':
                self.plot_losing_interest_alert(alert)
            else:
                self.plot_churn_risk_alert(alert)

if __name__ == "__main__":
    visualizer = AlertVisualizer()
    visualizer.run(num_alerts=2)
