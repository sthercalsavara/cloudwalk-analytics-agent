import pandas as pd

df = pd.read_csv('data/operational_intelligence_transactions_db.csv')

print("=== ENTIDADES ===")
print(df['entity'].unique())

print("\n=== PRODUTOS ===")
print(df['product'].unique())

print("\n=== PRICE TIERS ===")
print(df['price_tier'].unique())

print("\n=== MÉTODOS DE ANTECIPAÇÃO ===")
print(df['anticipation_method'].unique())

print("\n=== MÉTODOS DE PAGAMENTO ===")
print(df['payment_method'].unique())

print("\n=== NITRO OR D0 (valores não nulos) ===")
print(df['nitro_or_d0'].dropna().unique())