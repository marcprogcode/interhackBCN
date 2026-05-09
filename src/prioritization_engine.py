import pandas as pd
import numpy as np
from datetime import timedelta
import os
from data_loader import DataLoader
import warnings

warnings.filterwarnings('ignore')

class PrioritizationEngine:
    def __init__(self, data_dir="data", output_dir="outputs"):
        self.loader = DataLoader(data_dir=data_dir)
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def calculate_ltv_multipliers(self, df):
        """Calculates LTV per client and assigns a multiplier."""
        ltv = df.groupby('Id. Cliente')['Valores_H'].sum().reset_index()
        ltv.columns = ['Id. Cliente', 'LTV']
        
        # Calculate quantiles
        q99 = ltv['LTV'].quantile(0.99)
        q95 = ltv['LTV'].quantile(0.95)
        q90 = ltv['LTV'].quantile(0.90)
        q75 = ltv['LTV'].quantile(0.75)
        
        def get_multiplier(val):
            if val >= q99: return 3.0
            if val >= q95: return 2.0
            if val >= q90: return 1.5
            if val >= q75: return 1.2
            return 1.0
            
        ltv['LTV_Multiplier'] = ltv['LTV'].apply(get_multiplier)
        return ltv[['Id. Cliente', 'LTV', 'LTV_Multiplier']]

    def get_potencial_bonus(self, client_id, family, df_potencial):
        """Returns a 1.05 multiplier if potential > actual spend, 1.0 otherwise."""
        # Simple lookup: Since this is highly noisy, we'll just return a static bonus if potential > 0
        # A more robust implementation could compare to actual annualized spend.
        # For this iteration, we keep it simple as requested (low priority, high noise).
        pot = df_potencial[(df_potencial['Id.Cliente'] == client_id) & (df_potencial['Familia'] == family)]
        if not pot.empty and pot['Potencial_H'].values[0] > 0:
            return 1.05
        return 1.0

    def process_commodities(self, df_com, current_date, ltv_df, df_potencial):
        alerts = []
        # Group by Client and Family
        for (client, family), group in df_com.groupby(['Id. Cliente', 'Familia_H']):
            group = group.sort_values('Fecha')
            
            # Need to use unique dates to avoid zero intervals from same-day purchases
            unique_dates = group['Fecha'].dt.normalize().drop_duplicates()
            if len(unique_dates) < 4:
                continue # Need enough history for BoS confidence
                
            # Inter-Purchase Times (IPT)
            ipts = unique_dates.diff().dt.days.dropna()
            
            # 1. Confidence calculation
            real_cycles = len(ipts[ipts >= 7])
            confidence = min(1.0, real_cycles / 10.0) # 0.0 to 1.0
            
            # Robust Peak-Tracking: 85th Percentile of recent cycles
            recent_ipts = ipts.tail(15)
            base_cycle = recent_ipts.quantile(0.85)
            
            if pd.isna(base_cycle) or base_cycle <= 0:
                continue
                
            last_purchase_date = group['Fecha'].iloc[-1]
            dslp = (current_date - last_purchase_date).days
            
            # 2. Dynamic margin & Threshold
            margin = 0.30 - (0.15 * confidence) # Scales from 30% down to 15%
            
            expected_date = last_purchase_date + timedelta(days=base_cycle)
            # August seasonality adjustment
            if expected_date.month == 8:
                adjusted_threshold = base_cycle + 30
            else:
                adjusted_threshold = base_cycle * (1.0 + margin)
                
            if dslp > adjusted_threshold:
                avg_tx_value = group['Valores_H'].mean()
                if avg_tx_value <= 0:
                    continue
                    
                urgency = min(dslp / max(1, base_cycle), 5.0) # Cap urgency to avoid extreme scores
                
                ltv_mult = ltv_df[ltv_df['Id. Cliente'] == client]['LTV_Multiplier'].values
                ltv_mult = ltv_mult[0] if len(ltv_mult) > 0 else 1.0
                
                pot_bonus = self.get_potencial_bonus(client, family, df_potencial)
                
                # 3. Score application
                conf_multiplier = 0.5 + (0.5 * confidence) # Penalize newcomers
                priority_score = avg_tx_value * urgency * ltv_mult * pot_bonus * conf_multiplier
                
                alerts.append({
                    'Client_ID': client,
                    'Product_Family': family,
                    'Type': 'Replenishment',
                    'Priority_Score': priority_score,
                    'Reason': f'Overdue by {dslp} days (Typical Max Cycle: {base_cycle:.0f}, Conf: {confidence:.2f})',
                    'Expected_Value': avg_tx_value
                })
        return alerts

    def process_technical(self, df_tech, current_date, ltv_df, df_potencial):
        alerts = []
        # Define recent and previous 6 months
        recent_start = current_date - timedelta(days=180)
        previous_start = current_date - timedelta(days=360)
        
        for (client, family), group in df_tech.groupby(['Id. Cliente', 'Familia_H']):
            recent_vol = group[(group['Fecha'] > recent_start) & (group['Fecha'] <= current_date)]['Valores_H'].sum()
            prev_vol = group[(group['Fecha'] > previous_start) & (group['Fecha'] <= recent_start)]['Valores_H'].sum()
            
            if prev_vol > 0 and recent_vol <= (prev_vol * 0.5):
                # 50% drop in volume
                avg_tx_value = group['Valores_H'].mean()
                urgency = 1.5 # Fixed urgency for churn risk
                
                ltv_mult = ltv_df[ltv_df['Id. Cliente'] == client]['LTV_Multiplier'].values
                ltv_mult = ltv_mult[0] if len(ltv_mult) > 0 else 1.0
                pot_bonus = self.get_potencial_bonus(client, family, df_potencial)
                
                priority_score = prev_vol * urgency * ltv_mult * pot_bonus
                
                alerts.append({
                    'Client_ID': client,
                    'Product_Family': family,
                    'Type': 'Churn Risk',
                    'Priority_Score': priority_score,
                    'Reason': f'Volume dropped >50% (Prev 6M: {prev_vol:.0f}€ -> Recent 6M: {recent_vol:.0f}€)',
                    'Expected_Value': prev_vol
                })
        return alerts

    def generate_alerts(self, simulated_date=None):
        print("Loading data...")
        df = self.loader.get_merged_data()
        df_potencial = self.loader.load_potencial()
        
        # Determine current date
        if simulated_date:
            current_date = pd.to_datetime(simulated_date)
            # PREVENT DATA LEAKAGE: Filter strictly to data before or on current_date
            df = df[df['Fecha'] <= current_date]
        else:
            current_date = df['Fecha'].max()
            
        print(f"Running simulation for date: {current_date.strftime('%Y-%m-%d')}")
        
        ltv_df = self.calculate_ltv_multipliers(df)
        
        bloque_col = [c for c in df.columns if 'loque' in c][0]
        df_com = df[df[bloque_col] == 'Commodities']
        df_tech = df[df[bloque_col] == 'Technical']
        
        print("Processing commodities...")
        com_alerts = self.process_commodities(df_com, current_date, ltv_df, df_potencial)
        
        print("Processing technical products...")
        tech_alerts = self.process_technical(df_tech, current_date, ltv_df, df_potencial)
        
        all_alerts = com_alerts + tech_alerts
        alerts_df = pd.DataFrame(all_alerts)
        
        if not alerts_df.empty:
            alerts_df = alerts_df.sort_values('Priority_Score', ascending=False)
            
            output_path = os.path.join(self.output_dir, 'daily_alerts.csv')
            alerts_df.to_csv(output_path, index=False)
            print(f"Generated {len(alerts_df)} alerts. Saved to {output_path}")
            return alerts_df
        else:
            print("No alerts generated.")
            return pd.DataFrame()

if __name__ == "__main__":
    engine = PrioritizationEngine()
    engine.generate_alerts()
