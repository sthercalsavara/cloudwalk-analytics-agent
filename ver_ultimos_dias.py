from src.alerts import AlertSystem
import pandas as pd

sistema = AlertSystem()
kpis = sistema.calcular_kpis_diarios()

# Últimos 10 dias
ultimos_10 = kpis.tail(10)[['day', 'tpv']]
ultimos_10['day'] = ultimos_10['day'].dt.date
ultimos_10['tpv_formatado'] = ultimos_10['tpv'].apply(lambda x: f"R$ {x:,.2f}")

print("\n📊 TPV dos Últimos 10 Dias:\n")
print(ultimos_10[['day', 'tpv_formatado']].to_string(index=False))

# Calcular variações entre dias consecutivos
ultimos_10['variacao_pct'] = ultimos_10['tpv'].pct_change() * 100

print("\n📈 Variações Diárias (%):\n")
for idx, row in ultimos_10.iterrows():
    if pd.notna(row['variacao_pct']):
        print(f"{row['day']}: {row['variacao_pct']:+.2f}%")