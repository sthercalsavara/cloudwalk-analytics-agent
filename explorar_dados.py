import pandas as pd

# Carregar o CSV
print("Carregando dados...")
df = pd.read_csv('data/operational_intelligence_transactions_db.csv')

# Informações básicas
print("\n=== INFORMAÇÕES GERAIS ===")
print(f"Total de linhas: {len(df):,}")
print(f"Total de colunas: {len(df.columns)}")

print("\n=== COLUNAS ===")
print(df.columns.tolist())

print("\n=== PRIMEIRAS 5 LINHAS ===")
print(df.head())

print("\n=== TIPOS DE DADOS ===")
print(df.dtypes)

print("\n=== ESTATÍSTICAS ===")
print(df.describe())

print("\n=== VALORES ÚNICOS POR COLUNA ===")
for col in df.columns:
    print(f"{col}: {df[col].nunique()} valores únicos")