import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
products_path = r'c:\Users\hugca\OneDrive\Escriptori\interhackBCN\datasets\Datasets.xlsx - Productos.csv'
sales_path = r'c:\Users\hugca\OneDrive\Escriptori\interhackBCN\datasets\Datasets.xlsx - Ventas.csv'

# Load data
products = pd.read_csv(products_path)
sales = pd.read_csv(sales_path)

# Merge
df = sales.merge(products, left_on='Id. Producto', right_on='Id.Prod')

# Clean Valores_H: " -1.142,11" -> -1142.11
def clean_currency(x):
    if isinstance(x, str):
        x = x.replace('.', '').replace(',', '.')
    return float(x)

df['Valores_H'] = df['Valores_H'].apply(clean_currency)

# Convert Date
df['Fecha'] = pd.to_datetime(df['Fecha'], format='mixed')

# Group by Family
family_summary = df.groupby('Familia_H').agg({
    'Unidades': 'sum',
    'Valores_H': 'sum',
    'Num.Fact': 'count'
}).rename(columns={'Num.Fact': 'Transacciones'})

family_summary['Avg_Value_Per_Trans'] = family_summary['Valores_H'] / family_summary['Transacciones']
family_summary['Avg_Units_Per_Trans'] = family_summary['Unidades'] / family_summary['Transacciones']

# Filter out August (summer holidays)
df_filtered = df[df['Fecha'].dt.month != 8].copy()

# Group by Family (Filtered)
family_summary_filt = df_filtered.groupby('Familia_H').agg({
    'Unidades': 'sum',
    'Valores_H': 'sum',
    'Num.Fact': 'count'
}).rename(columns={'Num.Fact': 'Transacciones'})

# Monthly revenue (Filtered)
df_filtered['Month'] = df_filtered['Fecha'].dt.to_period('M')
monthly_sales_filt = df_filtered.groupby(['Month', 'Familia_H'])['Valores_H'].sum().unstack(fill_value=0)

# Correlation Matrix
corr_matrix = monthly_sales_filt.corr()

print("\n--- Correlation Matrix (Excluding August) ---")
print(corr_matrix)

# Plotting
plt.figure(figsize=(15, 12))

# 1. Monthly Revenue Trends (Excluding August)
plt.subplot(2, 2, 1)
monthly_sales_filt.plot(ax=plt.gca())
plt.title('Monthly Revenue Trends (Excluding August)')
plt.ylabel('Revenue')
plt.legend(title='Family', bbox_to_anchor=(1.05, 1), loc='upper left')

# 2. Correlation Heatmap (using matplotlib since seaborn is missing)
plt.subplot(2, 2, 2)
im = plt.imshow(corr_matrix, cmap='coolwarm')
plt.colorbar(im)
tick_marks = [i for i in range(len(corr_matrix.columns))]
plt.xticks(tick_marks, corr_matrix.columns, rotation=45)
plt.yticks(tick_marks, corr_matrix.index)

# Annotate values
for i in range(len(corr_matrix.columns)):
    for j in range(len(corr_matrix.index)):
        plt.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}', ha='center', va='center', color='black')

plt.title('Correlation Between Families (Excluding August)')

# 3. Normalized Trends (Excluding August)
plt.subplot(2, 2, 3)
(monthly_sales_filt / monthly_sales_filt.max()).plot(ax=plt.gca())
plt.title('Normalized Monthly Revenue (No August)')
plt.ylabel('Relative Revenue (0-1)')
plt.legend(title='Family', bbox_to_anchor=(1.05, 1), loc='upper left')

# 4. Total Revenue by Family (Filtered)
plt.subplot(2, 2, 4)
family_summary_filt['Valores_H'].sort_values().plot(kind='barh', color='lightgreen')
plt.title('Total Revenue (Excluding August)')
plt.xlabel('Revenue')

plt.tight_layout()
plt.savefig('c:\\Users\\hugca\\OneDrive\\Escriptori\\interhackBCN\\scratch\\buying_tendencies_filtered.png')
print("\nFiltered plot saved to scratch/buying_tendencies_filtered.png")
