import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import timedelta
import sys

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prioritization_engine import PrioritizationEngine
from data_loader import DataLoader

# Style
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.facecolor'] = '#121212'
plt.rcParams['figure.facecolor'] = '#121212'
plt.rcParams['grid.color'] = '#333333'

def run_test():
    TEST_DATE_STR = '2025-06-01'
    TEST_DATE = pd.to_datetime(TEST_DATE_STR)
    PLOT_DIR = 'plots/retro_test_v3'
    
    if not os.path.exists(PLOT_DIR):
        os.makedirs(PLOT_DIR)
        
    print(f"--- Running Retroactive Test V3 for Date: {TEST_DATE_STR} ---")
    
    # 1. Generate Alerts with strict filtering
    engine = PrioritizationEngine()
    alerts = engine.generate_alerts(simulated_date=TEST_DATE_STR)
    
    if alerts.empty:
        print("No alerts generated on this date.")
        return
        
    # Get top 5 replenishment alerts (already ranked by our new Confidence and LTV rules)
    replenishment_alerts = alerts[alerts['Type'] == 'Replenishment']
    top_5 = replenishment_alerts.head(5)
    
    print("\nTop 5 Alerts Generated (No Future Leakage):")
    print(top_5[['Client_ID', 'Product_Family', 'Priority_Score', 'Reason']])
    
    # 2. Plot Full Data Timeline vs the Threshold generated on TEST_DATE
    loader = DataLoader()
    full_df = loader.get_merged_data()
    
    for i, row in top_5.iterrows():
        client_id = row['Client_ID']
        family = row['Product_Family']
        
        # Get full data for this client
        client_data = full_df[(full_df['Id. Cliente'] == client_id) & (full_df['Familia_H'] == family)].copy()
        client_data = client_data.sort_values('Fecha')
        
        if len(client_data) == 0:
            continue
            
        start_date = client_data['Fecha'].iloc[0] + timedelta(days=180)
        end_date = full_df['Fecha'].max()
        
        sim_results = []
        trigger_dates = []
        currently_triggered = False
        
        frozen_threshold = None
        frozen_base_cycle = None
        frozen_confidence = None
        frozen_margin = None
        frozen_last_purchase = None
        test_dslp = None
        
        curr_date = start_date
        while curr_date <= end_date:
            past_purchases = client_data[client_data['Fecha'] <= curr_date]
            if not past_purchases.empty:
                last_p = past_purchases['Fecha'].dt.normalize().iloc[-1]
                dslp = (curr_date - last_p).days
            else:
                dslp = 0
                last_p = None
                
            threshold = None
            is_triggered = False
            
            # The engine only updates its knowledge up to min(curr_date, TEST_DATE)
            knowledge_date = min(curr_date, TEST_DATE)
            history = client_data[client_data['Fecha'] <= knowledge_date]
            unique_dates = history['Fecha'].dt.normalize().drop_duplicates().sort_values()
            
            if len(unique_dates) >= 4:
                ipts = unique_dates.diff().dt.days.dropna()
                real_cycles = len(ipts[ipts >= 7])
                confidence = min(1.0, real_cycles / 10.0)
                margin = 0.30 - (0.15 * confidence)
                base_cycle = ipts.tail(15).quantile(0.85)
                
                if curr_date <= TEST_DATE:
                    expected_date = unique_dates.iloc[-1] + timedelta(days=base_cycle)
                    if expected_date.month == 8:
                        threshold = base_cycle + 30
                    else:
                        threshold = base_cycle * (1.0 + margin)
                    
                    if dslp > threshold:
                        is_triggered = True
                        if not currently_triggered:
                            trigger_dates.append(curr_date)
                            currently_triggered = True
                    else:
                        currently_triggered = False
                        
                    # Save state exactly AT test date to freeze it
                    if curr_date == TEST_DATE:
                        frozen_threshold = threshold
                        frozen_base_cycle = base_cycle
                        frozen_confidence = confidence
                        frozen_margin = margin
                        frozen_last_purchase = unique_dates.iloc[-1]
                        test_dslp = dslp
                else:
                    # In the future (curr_date > TEST_DATE), the threshold is frozen
                    threshold = frozen_threshold
                    
            sim_results.append({
                'Date': curr_date,
                'DSLP': dslp,
                'Threshold': threshold,
            })
            curr_date += timedelta(days=1)
            
        sim_df = pd.DataFrame(sim_results)
        
        # Plot
        plt.figure(figsize=(15, 8))
        ax1 = plt.gca()
        
        # Cyan line: DSLP
        ax1.plot(sim_df['Date'], sim_df['DSLP'], color='#00f2ff', label='Days Since Last Purchase', linewidth=2)
        
        # Orange dashed line: Moving Threshold (past)
        past_sim = sim_df[sim_df['Date'] <= TEST_DATE]
        ax1.plot(past_sim['Date'], past_sim['Threshold'], color='#ffaa00', linestyle='--', label='Moving Threshold (Past)', linewidth=2, alpha=0.9)
        
        # Orange solid line: Frozen Threshold (future)
        future_sim = sim_df[sim_df['Date'] >= TEST_DATE]
        ax1.plot(future_sim['Date'], future_sim['Threshold'], color='#ffaa00', linestyle='-', label='Frozen Threshold (Future)', linewidth=3, alpha=0.9)
        
        # Plot actual purchases
        for _, p_row in client_data.iterrows():
            if p_row['Fecha'] >= start_date:
                plt.axvline(x=p_row['Fecha'], color='white', alpha=0.2, linestyle=':')
                plt.scatter(p_row['Fecha'], 0, color='white', marker='^', s=50, alpha=0.5)
                
        # Vertical line for TEST_DATE
        ax1.axvline(x=TEST_DATE, color='#ff00ff', linewidth=3, linestyle='--', label=f'Test Date: {TEST_DATE_STR}', alpha=0.8)
                 
        # Highlight exact date they became overdue BEFORE test date
        if frozen_last_purchase is not None and frozen_threshold is not None:
            breach_date = frozen_last_purchase + timedelta(days=frozen_threshold)
            if breach_date <= TEST_DATE:
                ax1.scatter(breach_date, frozen_threshold, color='#ffaa00', s=300, marker='*', zorder=6, edgecolors='black', label='Became Overdue (Final)')
                 
        # Highlight past triggers
        first_past = True
        for t_date in trigger_dates:
            if t_date != TEST_DATE: # Don't overlap with evaluation dot
                t_dslp = sim_df[sim_df['Date'] == t_date]['DSLP'].values[0]
                label = 'Past Trigger' if first_past else ""
                ax1.scatter(t_date, t_dslp, color='red', s=100, zorder=4, edgecolors='white', label=label)
                first_past = False
                
        # Highlight the trigger point on TEST_DATE
        if test_dslp is not None:
            ax1.scatter(TEST_DATE, test_dslp, color='#ff0055', s=200, zorder=5, edgecolors='white', label='Alert Evaluated')
        
        plt.title(f"Retroactive Test V3: Client {client_id} | {family}", fontsize=20, color='#00f2ff', pad=25)
        plt.xlabel("Date", fontsize=12, color='#888888')
        plt.ylabel("Days Since Last Purchase", fontsize=12, color='#888888')
        
        handles, labels = ax1.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys(), loc='upper left', frameon=True, facecolor='#1e1e1e', edgecolor='#333333')
        
        plt.grid(True, alpha=0.1)
        
        # Add explanation box
        if frozen_threshold is not None:
            explanation = (f"TEST DATE: {TEST_DATE_STR}\n"
                          f"Engine only saw data to the left.\n"
                          f"Calculated Base Cycle: {frozen_base_cycle:.0f} days\n"
                          f"Confidence Score: {frozen_confidence:.2f} (Margin: {(1.0+frozen_margin):.2f}x)\n"
                          f"Threshold: {frozen_threshold:.0f} days\n"
                          f"Client was overdue by {test_dslp:.0f} days\n\n"
                          f"Past Triggers: {len(trigger_dates)}\n"
                          f"Look right to see if they bought later!")
            
            props = dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.9, edgecolor='#ff00ff')
            plt.text(0.98, 0.05, explanation, transform=ax1.transAxes, fontsize=12,
                    verticalalignment='bottom', horizontalalignment='right', bbox=props, color='white')
                
        filename = f"retro_test_v3_{client_id}_{family.replace(' ', '_')}.png"
        save_path = os.path.join(PLOT_DIR, filename)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        print(f"Saved test plot to {save_path}")
        plt.close()

if __name__ == "__main__":
    run_test()
