import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from prioritization_engine import PrioritizationEngine

class TestPrioritizationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PrioritizationEngine(data_dir="../data", output_dir="../outputs")
        
    def test_ltv_multiplier(self):
        df = pd.DataFrame({
            'Id. Cliente': [1, 2, 3, 4],
            'Valores_H': [100, 500, 2000, 10000] # LTVs
        })
        # 0.75 quantile = 2000 * 0.25 + 10000 * 0.75 = ... wait
        # pd.quantile interpolates. 
        # q75 is around 4000. q90 is around 7600.
        # Let's just check the logic.
        ltv_df = self.engine.calculate_ltv_multipliers(df)
        self.assertEqual(len(ltv_df), 4)
        self.assertIn('LTV_Multiplier', ltv_df.columns)
        
        # ID 4 should have highest multiplier 5.0 (it's the top 99th percentile in this small sample)
        mult_4 = ltv_df[ltv_df['Id. Cliente'] == 4]['LTV_Multiplier'].values[0]
        self.assertEqual(mult_4, 5.0)
        
        # ID 1 should have base multiplier 0.2 (it's below the median)
        mult_1 = ltv_df[ltv_df['Id. Cliente'] == 1]['LTV_Multiplier'].values[0]
        self.assertEqual(mult_1, 0.2)
        
    def test_potencial_bonus(self):
        df_pot = pd.DataFrame({
            'Id.Cliente': [1],
            'Familia': ['Fam_A'],
            'Potencial_H': [1000]
        })
        
        bonus_match = self.engine.get_potencial_bonus(1, 'Fam_A', df_pot, annualized_spend=100)
        self.assertEqual(bonus_match, 2.0) # 1000 potential vs 100 spend -> >2x -> 2.0
        
        bonus_nomatch = self.engine.get_potencial_bonus(2, 'Fam_A', df_pot, annualized_spend=100)
        self.assertEqual(bonus_nomatch, 1.0)

    def test_commodities_logic(self):
        current_date = datetime(2024, 6, 1)
        # Create a df with one client buying every 30 days
        df_com = pd.DataFrame({
            'Id. Cliente': [1, 1, 1, 1],
            'Familia_H': ['Fam_A']*4,
            'Fecha': [
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
                datetime(2024, 3, 2), # 31 days
                datetime(2024, 4, 1)  # 30 days
            ],
            'Valores_H': [100, 100, 100, 100]
        })
        # Last purchase is April 1. Current date is June 1. DSLP = 61 days.
        # Median IPT = 30.5. Threshold = 30.5 * 1.5 = 45.75.
        # DSLP > Threshold. Should alert.
        
        ltv_df = pd.DataFrame({'Id. Cliente': [1], 'LTV_Multiplier': [1.0], 'LTV': [400]})
        df_pot = pd.DataFrame({'Id.Cliente': [], 'Familia': [], 'Potencial_H': []})
        
        alerts = self.engine.process_commodities(df_com, current_date, ltv_df, df_pot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['Type'], 'Replenishment')
        
        # Test August seasonality
        current_date_aug = datetime(2024, 9, 15)
        # Last purchase mid-July. Expected mid-August. 
        df_com_aug = pd.DataFrame({
            'Id. Cliente': [2, 2, 2, 2],
            'Familia_H': ['Fam_A']*4,
            'Fecha': [
                datetime(2024, 4, 15),
                datetime(2024, 5, 15),
                datetime(2024, 6, 15),
                datetime(2024, 7, 15)
            ],
            'Valores_H': [100, 100, 100, 100]
        })
        # Median IPT = 30. Last purchase July 15. Expected mid-August (Month=8).
        # Threshold should be 30 + 30 = 60.
        # Current date Sep 15. DSLP = 62. Should alert.
        alerts_aug = self.engine.process_commodities(df_com_aug, current_date_aug, ltv_df, df_pot)
        self.assertEqual(len(alerts_aug), 1)
        
    def test_technical_logic(self):
        current_date = datetime(2024, 6, 1)
        # Create a client that bought 1000 in prev 6M, and 0 in recent 6M
        df_tech = pd.DataFrame({
            'Id. Cliente': [3, 3],
            'Familia_H': ['Fam_T', 'Fam_T'],
            'Fecha': [
                current_date - timedelta(days=20), # Recent
                current_date - timedelta(days=250), # Prev 6M (age = 230 days)
            ],
            'Valores_H': [100, 1000] # Vol drop from 1000 to 100
        })
        
        ltv_df = pd.DataFrame({'Id. Cliente': [3], 'LTV_Multiplier': [1.0], 'LTV': [1100]})
        df_pot = pd.DataFrame({'Id.Cliente': [], 'Familia': [], 'Potencial_H': []})
        
        alerts = self.engine.process_technical(df_tech, current_date, ltv_df, df_pot)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['Type'], 'Churn Risk')
        self.assertTrue('Vol drop >50%' in alerts[0]['Reason'])

    # End to end test
    def test_e2e_run(self):
        # We assume data is available in the original path.
        # Since this is a test, we run generate_alerts directly to see if it doesn't crash.
        # Note: this requires actual data to be there. 
        engine = PrioritizationEngine(data_dir=os.path.join(os.path.dirname(__file__), "..", "data"), output_dir=os.path.join(os.path.dirname(__file__), "..", "outputs"))
        alerts_df = engine.generate_alerts()
        self.assertIsInstance(alerts_df, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
