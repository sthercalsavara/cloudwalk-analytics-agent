import pandas as pd
import sqlite3
import subprocess
import os

class SQLAgent:
    def __init__(self, csv_path, db_path='data/transactions.db'):
        """Inicializa o agente criando banco SQLite"""
        self.db_path = db_path
        
        print("📊 Carregando dados no SQLite...")
        
        # Carregar CSV
        df = pd.read_csv(csv_path)
        
        # Corrigir nome da coluna com erro
        df.rename(columns={'quantitu_of_merchants': 'quantity_of_merchants'}, inplace=True)
        
        # Converter data para formato ISO
        df['day'] = pd.to_datetime(df['day'], format='mixed', dayfirst=True)
        df['day'] = df['day'].dt.strftime('%Y-%m-%d')
        
        # Criar banco SQLite e inserir dados
        conn = sqlite3.connect(self.db_path)
        df.to_sql('transactions', conn, if_exists='replace', index=False)
        conn.close()
        
        print(f"✅ Banco SQLite criado: {len(df):,} linhas")
        
    def _preparar_contexto(self):
        """Prepara contexto sobre a estrutura da tabela para o LLM"""
        contexto = """
Você é um assistente que gera queries SQL para análise de dados.

TABELA DISPONÍVEL: transactions

COLUNAS:
- day (DATE): data da transação (formato YYYY-MM-DD)
- entity (TEXT): 'PJ' ou 'PF' (Pessoa Jurídica ou Física)
- product (TEXT): 'pix', 'pos', 'tap', 'link', 'bank_slip'
- price_tier (TEXT): 'normal', 'intermediary', 'aggressive', 'domination'
- anticipation_method (TEXT): 'Pix', 'D1Anticipation', 'Bank Slip', 'D0/Nitro'
- nitro_or_d0 (TEXT): 'D0', 'Nitro', 'Nitro Anticipation' (muitos nulos)
- payment_method (TEXT): 'credit', 'debit', 'uninformed'
- installments (INTEGER): número de parcelas (1-12)
- amount_transacted (REAL): valor transacionado em BRL
- quantity_transactions (INTEGER): quantidade de transações
- quantity_of_merchants (INTEGER): quantidade de comerciantes

DEFINIÇÕES DE KPIs:
- TPV (Total Payment Volume): SUM(amount_transacted)
- Ticket Médio: amount_transacted / quantity_transactions

IMPORTANTE: Use SQLite, então funções como EXTRACT não existem. Use strftime() para datas.
"""
        return contexto

    def _gerar_sql(self, pergunta):
        """Usa Ollama para gerar SQL"""
        contexto = self._preparar_contexto()
        
        prompt = f"""{contexto}

PERGUNTA DO USUÁRIO: {pergunta}

INSTRUÇÕES:
1. Gere uma query SQL válida para SQLite
2. A query deve ser eficiente e retornar resultado claro
3. Use aliases descritivos nas colunas
4. Para agregações, use GROUP BY apropriado
5. Ordene resultados de forma lógica (DESC para valores grandes)
6. Retorne APENAS o SQL, sem explicações antes ou depois
7. Não use markdown, não use ```sql, apenas o SQL puro

EXEMPLO DE RESPOSTA:
SELECT product, SUM(amount_transacted) as tpv 
FROM transactions 
GROUP BY product 
ORDER BY tpv DESC 
LIMIT 1;

AGORA GERE O SQL PARA A PERGUNTA DO USUÁRIO:"""

        print("\n🤖 Consultando Ollama...")
        
        try:
            result = subprocess.run(
                ['ollama', 'run', 'llama3.2'],
                input=prompt,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=60
            )
            
            sql_gerado = result.stdout.strip()
            
            # Limpar o SQL (remover markdown se houver)
            sql_gerado = sql_gerado.replace('```sql', '').replace('```', '').strip()
            
            # Remover ponto e vírgula final se houver múltiplas linhas com ;
            if sql_gerado.count(';') > 1:
                sql_gerado = sql_gerado.split(';')[0] + ';'
            
            print(f"\n💻 SQL gerado:\n{sql_gerado}\n")
            
            return sql_gerado
            
        except subprocess.TimeoutExpired:
            print("⏱️ Timeout ao consultar Ollama")
            return None
        except Exception as e:
            print(f"❌ Erro ao consultar Ollama: {e}")
            return None

    def _executar_sql(self, sql):
        """Executa SQL e retorna resultado como DataFrame"""
        try:
            conn = sqlite3.connect(self.db_path)
            resultado = pd.read_sql_query(sql, conn)
            conn.close()
            return resultado
        except Exception as e:
            return f"❌ Erro ao executar SQL: {str(e)}"

    def perguntar(self, pergunta):
        """Método principal: recebe pergunta e retorna resposta"""
        print(f"\n❓ Pergunta: {pergunta}")
        
        # Gerar SQL
        sql = self._gerar_sql(pergunta)
        
        if not sql:
            return "❌ Não foi possível gerar SQL para essa pergunta"
        
        # Executar SQL
        resultado = self._executar_sql(sql)
        
        # Formatar resultado
        print("\n📊 Resultado:")
        if isinstance(resultado, pd.DataFrame):
            print(resultado.to_string(index=False))
        else:
            print(resultado)
        
        return resultado


# Exemplo de uso
if __name__ == "__main__":
    # Inicializar agente
    agente = SQLAgent('data/operational_intelligence_transactions_db.csv')
    
    # Testar com uma pergunta
    agente.perguntar("Qual produto tem o maior TPV total?")