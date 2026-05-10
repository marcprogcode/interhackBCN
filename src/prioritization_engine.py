import pandas as pd
import numpy as np
import math
import json
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
        q50 = ltv['LTV'].quantile(0.50)
        
        def get_multiplier(val):
            if val >= q99: return 5.0
            if val >= q95: return 3.0
            if val >= q90: return 2.0
            if val >= q75: return 1.5
            if val >= q50: return 1.0
            return 0.2  # Strongly penalize low-value clients
            
        ltv['LTV_Multiplier'] = ltv['LTV'].apply(get_multiplier)
        return ltv[['Id. Cliente', 'LTV', 'LTV_Multiplier']]

    def get_potencial_bonus(self, client_id, family, df_potencial, annualized_spend):
        """Returns a multiplier if potential > actual spend, targeting promiscuous clients."""
        pot = df_potencial[(df_potencial['Id.Cliente'] == client_id) & (df_potencial['Familia'] == family)]
        if not pot.empty:
            pot_val = pot['Potencial_H'].values[0]
            if pot_val > annualized_spend * 2.0:
                return 2.0  # High potential for capture (highly promiscuous)
            elif pot_val > annualized_spend * 1.2:
                return 1.5  # Some potential
        return 1.0

    def process_commodities(self, df_com, current_date, ltv_df, df_potencial):
        alerts = []
        from tqdm import tqdm
        # Group by Client and Family
        groups = df_com.groupby(['Id. Cliente', 'Familia_H'])
        for (client, family), group in tqdm(groups, desc="Processing Commodities"):
            group = group.sort_values('Fecha')
            
            # Need to use unique dates to avoid zero intervals from same-day purchases
            unique_dates = group['Fecha'].dt.normalize().drop_duplicates()
            if len(unique_dates) < 4:
                continue # Need enough history for BoS confidence
                
            # Inter-Purchase Times (IPT)
            ipts = unique_dates.diff().dt.days.dropna()
            
            # 1. Confidence and Longevity calculation
            real_cycles = len(ipts[ipts >= 7])
            confidence = min(1.0, real_cycles / 10.0) # 0.0 to 1.0
            
            client_age_days = (group['Fecha'].iloc[-1] - group['Fecha'].iloc[0]).days
            if client_age_days < 90:
                longevity_mult = 0.1 # Heavily penalize clients with barely any history
            elif client_age_days < 365:
                longevity_mult = 0.5
            elif client_age_days < 1095:
                longevity_mult = 1.2
            else:
                longevity_mult = 1.5
                
            annualized_spend = group['Valores_H'].sum() / max(1, client_age_days / 365.0)
            
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
                
                # 3. Urgency: logarithmic scaling instead of linear
                # In real-time, dslp/base_cycle ≈ 1.0-2.0; log dampens extreme retroactive values
                urgency = min(1.0 + math.log(max(1.0, dslp / base_cycle)), 2.5)
                
                # 4. Recoverability: clients far past threshold are probably lost
                # Decays as they get further past their expected date
                overdue_beyond = max(0, dslp - adjusted_threshold)
                recoverability = 1.0 / (1.0 + 0.5 * (overdue_beyond / base_cycle))
                
                # 5. LTV with family relevance
                ltv_row = ltv_df[ltv_df['Id. Cliente'] == client]
                global_ltv_mult = ltv_row['LTV_Multiplier'].values[0] if len(ltv_row) > 0 else 1.0
                global_ltv = ltv_row['LTV'].values[0] if len(ltv_row) > 0 else 1.0
                family_spend = group['Valores_H'].sum()
                family_share = min(1.0, family_spend / max(1, global_ltv))
                # Blend: full multiplier if family is >50% of spend, dampened otherwise
                ltv_mult = global_ltv_mult * (0.5 + 0.5 * min(1.0, family_share * 2))
                
                pot_bonus = self.get_potencial_bonus(client, family, df_potencial, annualized_spend)
                
                # 6. Score: value × urgency × recoverability × modifiers
                conf_multiplier = 0.5 + (0.5 * confidence) # Penalize newcomers further
                priority_score = avg_tx_value * urgency * recoverability * ltv_mult * pot_bonus * conf_multiplier * longevity_mult
                
                formula_str = (f'avg_val({avg_tx_value:.1f}) × urg({urgency:.2f}) × '
                               f'recov({recoverability:.2f}) × ltv({ltv_mult:.1f}) × '
                               f'pot({pot_bonus:.1f}) × conf({conf_multiplier:.2f}) × '
                               f'long({longevity_mult:.1f}) = {priority_score:.1f}')
                reason_str = (f'Overdue {dslp}d (cycle:{base_cycle:.0f}, thresh:{adjusted_threshold:.0f}, '
                              f'conf:{confidence:.2f}, age:{client_age_days}d, txns:{len(unique_dates)})')
                
                # Generate Interpretability Data
                history = []
                purchase_dates = set(unique_dates.dt.date)
                
                # Window size: proportional to cycle length, ensuring we see the last purchase
                window_days = int(max(base_cycle * 3, dslp + base_cycle * 1.5))
                start_date = current_date - timedelta(days=window_days)
                
                # Precalculate thresholds to reflect realtime evolution
                threshold_history = {}
                sorted_dates_dt = sorted(list(unique_dates))
                for idx in range(len(sorted_dates_dt)):
                    p_date = sorted_dates_dt[idx].date()
                    if idx < 3:
                        threshold_history[p_date] = (base_cycle, adjusted_threshold)
                        continue
                    past_series = pd.Series(sorted_dates_dt[:idx+1])
                    past_ipts = past_series.diff().dt.days.dropna()
                    hist_bc = past_ipts.tail(15).quantile(0.85)
                    if pd.isna(hist_bc) or hist_bc <= 0:
                        threshold_history[p_date] = (base_cycle, adjusted_threshold)
                    else:
                        hist_conf = min(1.0, len(past_ipts[past_ipts >= 7]) / 10.0)
                        hist_marg = 0.30 - (0.15 * hist_conf)
                        hist_exp = p_date + timedelta(days=hist_bc)
                        hist_adj = hist_bc + 30 if hist_exp.month == 8 else hist_bc * (1.0 + hist_marg)
                        threshold_history[p_date] = (hist_bc, hist_adj)
                
                past_dates = [d for d in purchase_dates if d <= start_date.date()]
                current_last_purchase = max(past_dates) if past_dates else None
                
                for i in range(window_days, -1, -1):
                    d = (current_date - timedelta(days=i)).date()
                    if d in purchase_dates:
                        current_last_purchase = d
                        
                    days_since_purchase = (d - current_last_purchase).days if current_last_purchase else 0
                    
                    if current_last_purchase and current_last_purchase in threshold_history:
                        hist_base_cycle, hist_adjusted_threshold = threshold_history[current_last_purchase]
                    else:
                        hist_base_cycle, hist_adjusted_threshold = base_cycle, adjusted_threshold
                    
                    point = {
                        "date": d.strftime('%Y-%m-%d'),
                        "days_since_purchase": days_since_purchase,
                        "moving_threshold": int(hist_base_cycle),
                        "frozen_threshold": int(hist_adjusted_threshold)
                    }
                    
                    if i == 0:
                        point["is_current_date"] = True
                        point["is_alert_evaluated"] = True
                        
                    if days_since_purchase == int(hist_adjusted_threshold):
                        point["is_overdue_date"] = True
                        point["event"] = "Overdue"
                    elif days_since_purchase == int(hist_base_cycle):
                        point["is_past_triggered"] = True
                        point["event"] = "Soft Alert Triggered"
                        
                    if d in purchase_dates:
                        point["event"] = "Purchase"
                        
                    history.append(point)
                    
                interpretability = {
                    "company_id": str(client),
                    "typical_purchase_cadence": f"El client compra habitualment cada {int(base_cycle)} dies",
                    "timeseries": history
                }
                
                alerts.append({
                    'Client_ID': client,
                    'Product_Family': family,
                    'Type': 'Replenishment',
                    'Priority_Score': priority_score,
                    'Reason': reason_str,
                    'Formula': formula_str,
                    'Expected_Value': avg_tx_value,
                    'Confidence': confidence,
                    'Interpretability_JSON': json.dumps(interpretability)
                })
        return alerts

    def process_technical(self, df_tech, current_date, ltv_df, df_potencial):
        alerts = []
        # Define recent and previous 6 months
        recent_start = current_date - timedelta(days=180)
        previous_start = current_date - timedelta(days=360)
        
        from tqdm import tqdm
        groups = df_tech.groupby(['Id. Cliente', 'Familia_H'])
        for (client, family), group in tqdm(groups, desc="Processing Technical"):
            client_age_days = (group['Fecha'].max() - group['Fecha'].min()).days
            if client_age_days < 180:
                continue # Cannot reliably determine churn with < 6 months of history
                
            if client_age_days < 365:
                longevity_mult = 0.5
            elif client_age_days < 1095:
                longevity_mult = 1.2
            else:
                longevity_mult = 1.5
                
            recent_vol = group[(group['Fecha'] > recent_start) & (group['Fecha'] <= current_date)]['Valores_H'].sum()
            prev_vol = group[(group['Fecha'] > previous_start) & (group['Fecha'] <= recent_start)]['Valores_H'].sum()
            
            if prev_vol > 0 and recent_vol <= (prev_vol * 0.5):
                # 50% drop in volume
                avg_tx_value = group['Valores_H'].mean()
                urgency = 1.5 # Fixed urgency for churn risk
                
                # Family-relevant LTV
                ltv_row = ltv_df[ltv_df['Id. Cliente'] == client]
                global_ltv_mult = ltv_row['LTV_Multiplier'].values[0] if len(ltv_row) > 0 else 1.0
                global_ltv = ltv_row['LTV'].values[0] if len(ltv_row) > 0 else 1.0
                family_spend = group['Valores_H'].sum()
                family_share = min(1.0, family_spend / max(1, global_ltv))
                ltv_mult = global_ltv_mult * (0.5 + 0.5 * min(1.0, family_share * 2))
                
                annualized_spend = group['Valores_H'].sum() / max(1, client_age_days / 365.0)
                pot_bonus = self.get_potencial_bonus(client, family, df_potencial, annualized_spend)
                
                priority_score = prev_vol * urgency * ltv_mult * pot_bonus * longevity_mult
                
                formula_str = (f'prev_vol({prev_vol:.0f}) × urgency({urgency:.1f}) × '
                               f'ltv({ltv_mult:.1f}) × pot({pot_bonus:.1f}) × long({longevity_mult:.1f}) = {priority_score:.1f}')
                reason_str = (f'Vol drop >50% (prev6m:{prev_vol:.0f}€→recent6m:{recent_vol:.0f}€, age:{client_age_days}d)')
                
                # Generate Interpretability Data (Empty timeseries with descriptive text)
                interpretability = {
                    "company_id": str(client),
                    "typical_purchase_cadence": f"Caiguda de volum del >50%. Volum previ 6m: {int(prev_vol)}€, Volum recent 6m: {int(recent_vol)}€",
                    "timeseries": []
                }
                
                alerts.append({
                    'Client_ID': client,
                    'Product_Family': family,
                    'Type': 'Churn Risk',
                    'Priority_Score': priority_score,
                    'Reason': reason_str,
                    'Formula': formula_str,
                    'Expected_Value': prev_vol,
                    'Confidence': 0.85, # High confidence for clear volume drops
                    'Interpretability_JSON': json.dumps(interpretability)
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
