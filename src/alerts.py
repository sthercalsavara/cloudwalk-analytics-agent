import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class AlertSystem:
    def __init__(self, csv_path='data/operational_intelligence_transactions_db.csv'):
        """Inicializa sistema de alertas carregando dados"""
        print("📊 Carregando dados para sistema de alertas...")
        self.df = pd.read_csv(csv_path)
        
        # Corrigir coluna
        self.df.rename(columns={'quantitu_of_merchants': 'quantity_of_merchants'}, inplace=True)
        
        # Converter data
        self.df['day'] = pd.to_datetime(self.df['day'], format='mixed', dayfirst=True)
        
        print(f"✅ Dados carregados: {len(self.df):,} linhas")
        print(f"📅 Período: {self.df['day'].min().date()} a {self.df['day'].max().date()}")
    
    def calcular_kpis_diarios(self):
        """Calcula KPIs agregados por dia"""
        kpis = self.df.groupby('day').agg({
            'amount_transacted': 'sum',  # TPV
            'quantity_transactions': 'sum',
            'quantity_of_merchants': 'sum'
        }).reset_index()
        
        kpis.columns = ['day', 'tpv', 'total_transactions', 'total_merchants']
        
        # Ticket médio
        kpis['avg_ticket'] = kpis['tpv'] / kpis['total_transactions']
        
        return kpis.sort_values('day')
    
    def calcular_kpis_por_segmento(self, dia=None):
        """Calcula KPIs segmentados por produto, entity, payment_method"""
        if dia:
            df_dia = self.df[self.df['day'] == dia]
        else:
            # Usar último dia disponível
            dia = self.df['day'].max()
            df_dia = self.df[self.df['day'] == dia]
        
        segmentos = {}
        
        # Por produto
        segmentos['produto'] = df_dia.groupby('product').agg({
            'amount_transacted': 'sum',
            'quantity_transactions': 'sum'
        }).reset_index()
        segmentos['produto']['avg_ticket'] = (
            segmentos['produto']['amount_transacted'] / 
            segmentos['produto']['quantity_transactions']
        )
        
        # Por entity
        segmentos['entity'] = df_dia.groupby('entity').agg({
            'amount_transacted': 'sum',
            'quantity_transactions': 'sum'
        }).reset_index()
        segmentos['entity']['avg_ticket'] = (
            segmentos['entity']['amount_transacted'] / 
            segmentos['entity']['quantity_transactions']
        )
        
        # Por payment_method
        segmentos['payment_method'] = df_dia.groupby('payment_method').agg({
            'amount_transacted': 'sum',
            'quantity_transactions': 'sum'
        }).reset_index()
        segmentos['payment_method']['avg_ticket'] = (
            segmentos['payment_method']['amount_transacted'] / 
            segmentos['payment_method']['quantity_transactions']
        )
        
        return segmentos, dia
    
    def calcular_variacoes(self, dia=None):
        """
        Calcula variações do TPV comparando com períodos anteriores
        D-1, D-7, D-30
        """
        kpis = self.calcular_kpis_diarios()
        
        if dia:
            dia = pd.to_datetime(dia)
        else:
            dia = kpis['day'].max()
        
        # Obter TPV do dia
        tpv_dia = kpis[kpis['day'] == dia]['tpv'].values
        
        if len(tpv_dia) == 0:
            return None
        
        tpv_dia = tpv_dia[0]
        
        # Calcular variações
        variacoes = {
            'dia': dia,
            'tpv_atual': tpv_dia
        }
        
        # D-1 (dia anterior)
        dia_d1 = dia - timedelta(days=1)
        tpv_d1 = kpis[kpis['day'] == dia_d1]['tpv'].values
        if len(tpv_d1) > 0:
            variacoes['tpv_d1'] = tpv_d1[0]
            variacoes['var_d1_pct'] = ((tpv_dia - tpv_d1[0]) / tpv_d1[0]) * 100
        else:
            variacoes['tpv_d1'] = None
            variacoes['var_d1_pct'] = None
        
        # D-7 (semana passada)
        dia_d7 = dia - timedelta(days=7)
        tpv_d7 = kpis[kpis['day'] == dia_d7]['tpv'].values
        if len(tpv_d7) > 0:
            variacoes['tpv_d7'] = tpv_d7[0]
            variacoes['var_d7_pct'] = ((tpv_dia - tpv_d7[0]) / tpv_d7[0]) * 100
        else:
            variacoes['tpv_d7'] = None
            variacoes['var_d7_pct'] = None
        
        # D-30 (mês passado) - usa média dos últimos 30 dias
        inicio_janela = dia - timedelta(days=30)
        fim_janela = dia - timedelta(days=1)
        tpv_30d = kpis[
            (kpis['day'] >= inicio_janela) & 
            (kpis['day'] <= fim_janela)
        ]['tpv'].mean()
        
        if not np.isnan(tpv_30d):
            variacoes['tpv_avg_30d'] = tpv_30d
            variacoes['var_30d_pct'] = ((tpv_dia - tpv_30d) / tpv_30d) * 100
        else:
            variacoes['tpv_avg_30d'] = None
            variacoes['var_30d_pct'] = None
        
        return variacoes
    
    def detectar_anomalias(self, threshold_pct=15, threshold_zscore=2):
        """
        Detecta anomalias significativas
        
        Args:
            threshold_pct: % de variação para considerar anomalia (default 15%)
            threshold_zscore: z-score mínimo para anomalia (default 2)
        """
        variacoes = self.calcular_variacoes()
        
        if not variacoes:
            return []
        
        alertas = []
        
        # Verificar variação D-1
        if variacoes['var_d1_pct'] is not None:
            if abs(variacoes['var_d1_pct']) > threshold_pct:
                tipo = "QUEDA" if variacoes['var_d1_pct'] < 0 else "ALTA"
                alertas.append({
                    'tipo': tipo,
                    'metrica': 'TPV',
                    'variacao_pct': variacoes['var_d1_pct'],
                    'periodo': 'D-1',
                    'severidade': 'ALTA' if abs(variacoes['var_d1_pct']) > 20 else 'MÉDIA'
                })
        
        # Verificar variação D-7
        if variacoes['var_d7_pct'] is not None:
            if abs(variacoes['var_d7_pct']) > threshold_pct:
                tipo = "QUEDA" if variacoes['var_d7_pct'] < 0 else "ALTA"
                alertas.append({
                    'tipo': tipo,
                    'metrica': 'TPV',
                    'variacao_pct': variacoes['var_d7_pct'],
                    'periodo': 'D-7',
                    'severidade': 'ALTA' if abs(variacoes['var_d7_pct']) > 20 else 'MÉDIA'
                })
        
        # Verificar variação média 30 dias
        if variacoes['var_30d_pct'] is not None:
            if abs(variacoes['var_30d_pct']) > threshold_pct:
                tipo = "QUEDA" if variacoes['var_30d_pct'] < 0 else "ALTA"
                alertas.append({
                    'tipo': tipo,
                    'metrica': 'TPV',
                    'variacao_pct': variacoes['var_30d_pct'],
                    'periodo': 'média 30 dias',
                    'severidade': 'ALTA' if abs(variacoes['var_30d_pct']) > 20 else 'MÉDIA'
                })
        
        # Detectar qual segmento causou a anomalia
        if alertas:
            segmentos, dia = self.calcular_kpis_por_segmento()
            
            for alerta in alertas:
                # Encontrar maior variação por produto
                produtos = segmentos['produto'].sort_values('amount_transacted', ascending=False)
                alerta['detalhes'] = {
                    'top_produto': produtos.iloc[0]['product'],
                    'tpv_produto': produtos.iloc[0]['amount_transacted']
                }
        
        return alertas, variacoes
    
    def formatar_alerta(self, alerta, variacoes):
        """Formata alerta em texto legível"""
        emoji = "⚠️" if alerta['severidade'] == 'ALTA' else "ℹ️"
        sinal = "+" if alerta['variacao_pct'] > 0 else ""
        
        mensagem = f"{emoji} ALERTA [{alerta['severidade']}]: "
        mensagem += f"{alerta['tipo']} de {alerta['metrica']} "
        mensagem += f"{sinal}{alerta['variacao_pct']:.1f}% vs {alerta['periodo']}\n"
        
        if 'detalhes' in alerta:
            mensagem += f"   • Principal produto: {alerta['detalhes']['top_produto']} "
            mensagem += f"(TPV: R$ {alerta['detalhes']['tpv_produto']:,.2f})\n"
        
        mensagem += f"   • TPV atual: R$ {variacoes['tpv_atual']:,.2f}\n"
        
        return mensagem
    
    def gerar_relatorio_diario(self, dia=None):
        """
        Gera relatório completo de KPIs + alertas para um dia
        """
        print("=" * 70)
        print("📊 RELATÓRIO DIÁRIO DE KPIs E ALERTAS")
        print("=" * 70)
        
        # Calcular variações
        variacoes = self.calcular_variacoes(dia)
        
        if not variacoes:
            print("❌ Não há dados suficientes para o dia especificado")
            return
        
        print(f"\n📅 Data: {variacoes['dia'].date()}")
        print(f"\n💰 TPV Atual: R$ {variacoes['tpv_atual']:,.2f}")
        
        # Mostrar variações
        if variacoes['var_d1_pct'] is not None:
            sinal = "+" if variacoes['var_d1_pct'] > 0 else ""
            print(f"   • vs D-1: {sinal}{variacoes['var_d1_pct']:.2f}%")
        
        if variacoes['var_d7_pct'] is not None:
            sinal = "+" if variacoes['var_d7_pct'] > 0 else ""
            print(f"   • vs D-7: {sinal}{variacoes['var_d7_pct']:.2f}%")
        
        if variacoes['var_30d_pct'] is not None:
            sinal = "+" if variacoes['var_30d_pct'] > 0 else ""
            print(f"   • vs média 30 dias: {sinal}{variacoes['var_30d_pct']:.2f}%")
        
        # Detectar e mostrar anomalias
        alertas, _ = self.detectar_anomalias()
        
        if alertas:
            print("\n🚨 ALERTAS DETECTADOS:")
            print("-" * 70)
            for alerta in alertas:
                print(self.formatar_alerta(alerta, variacoes))
        else:
            print("\n✅ Nenhuma anomalia detectada")
        
        # Mostrar top segmentos
        segmentos, _ = self.calcular_kpis_por_segmento(dia)
        
        print("\n📊 TOP 3 PRODUTOS POR TPV:")
        top_produtos = segmentos['produto'].sort_values('amount_transacted', ascending=False).head(3)
        for idx, row in top_produtos.iterrows():
            print(f"   {idx+1}. {row['product']}: R$ {row['amount_transacted']:,.2f}")
        
        print("\n" + "=" * 70)


# Exemplo de uso
if __name__ == "__main__":
    # Inicializar sistema
    sistema = AlertSystem()
    
    # Gerar relatório para o último dia disponível
    print("\n🔍 TESTANDO SISTEMA DE ALERTAS\n")
    sistema.gerar_relatorio_diario()
    
    print("\n" + "="*70)
    print("💡 Para agendar alertas diários, use APScheduler ou cron:")
    print("   Exemplo: schedule.every().day.at('09:00').do(sistema.gerar_relatorio_diario)")
    print("="*70)