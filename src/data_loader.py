import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore')

def clean_currency(x):
    """Converts Spanish formatted currency string to float."""
    if isinstance(x, str):
        x = x.replace('.', '').replace(',', '.')
    try:
        return float(x)
    except:
        return 0.0

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def load_ventas(self):
        ventas_path = os.path.join(self.data_dir, "Datasets.xlsx - Ventas.csv")
        df = pd.read_csv(ventas_path, low_memory=False)
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=False)
        df['Valores_H'] = df['Valores_H'].apply(clean_currency)
        return df

    def load_productos(self):
        productos_path = os.path.join(self.data_dir, "Datasets.xlsx - Productos.csv")
        df = pd.read_csv(productos_path, low_memory=False)
        return df

    def load_clientes(self):
        clientes_path = os.path.join(self.data_dir, "Datasets.xlsx - Clientes.csv")
        df = pd.read_csv(clientes_path, low_memory=False)
        return df

    def load_potencial(self):
        potencial_path = os.path.join(self.data_dir, "Datasets.xlsx - Potencial.csv")
        df = pd.read_csv(potencial_path, low_memory=False)
        df['Potencial_H'] = df['Potencial_H'].apply(clean_currency)
        return df

    def get_merged_data(self):
        df_ventas = self.load_ventas()
        df_productos = self.load_productos()
        
        # Merge Ventas with Productos to get 'Bloque analítico' and 'Familia_H'
        merged = pd.merge(df_ventas, df_productos, left_on='Id. Producto', right_on='Id.Prod', how='left')
        return merged
