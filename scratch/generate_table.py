import pandas as pd

def generate_table():
    df = pd.read_csv('outputs/daily_alerts.csv')
    top_100 = df.head(100)
    
    table = "| Rank | Client ID | Family | Score | Reason | Formula |\n"
    table += "|------|-----------|--------|-------|--------|----------|\n"
    
    for i, row in top_100.iterrows():
        # Escape any pipes in the fields just in case
        reason = str(row['Reason']).replace('|', '\\|')
        formula = str(row.get('Formula', 'N/A')).replace('|', '\\|')
        table += f"| {i+1} | {row['Client_ID']} | {row['Product_Family']} | {row['Priority_Score']:,.2f} | {reason} | {formula} |\n"
        
    with open('top_100_alerts_table.md', 'w', encoding='utf-8') as f:
        f.write(table)

if __name__ == "__main__":
    generate_table()
