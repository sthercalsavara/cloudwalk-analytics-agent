import pandas as pd
import subprocess

class PandasAgent:
    def __init__(self, csv_path):
        """Inicializa o agente carregando os dados"""
        print("📊 Carregando dados...")
        self.df = pd.read_csv(csv_path)
        
        # Corrigir nome da coluna com erro
        self.df.rename(columns={'quantitu_of_merchants': 'quantity_of_merchants'}, inplace=True)
        
        # Converter coluna de data
        self.df['day'] = pd.to_datetime(self.df['day'], format='mixed', dayfirst=True)
        
        print(f"✅ Dados carregados: {len(self.df):,} linhas")
        
    def _preparar_contexto(self):
        """Prepara contexto sobre os dados para o LLM"""
        contexto = f"""
Você é um assistente de análise de dados. Tenho um DataFrame pandas chamado 'df' com dados de transações.

COLUNAS DISPONÍVEIS:
- day (datetime): data da transação
- entity (str): 'PJ' ou 'PF' (Pessoa Jurídica ou Física)
- product (str): 'pix', 'pos', 'tap', 'link', 'bank_slip'
- price_tier (str): 'normal', 'intermediary', 'aggressive', 'domination'
- anticipation_method (str): 'Pix', 'D1Anticipation', 'Bank Slip', 'D0/Nitro'
- nitro_or_d0 (str): 'D0', 'Nitro', 'Nitro Anticipation' (muitos valores nulos)
- payment_method (str): 'credit', 'debit', 'uninformed'
- installments (int): número de parcelas (1-12)
- amount_transacted (float): valor transacionado em BRL
- quantity_transactions (int): quantidade de transações
- quantity_of_merchants (int): quantidade de comerciantes

DEFINIÇÕES DE KPIs:
- TPV (Total Payment Volume): soma de amount_transacted
- Ticket Médio: amount_transacted / quantity_transactions

O DataFrame já está carregado na variável 'df'.
"""
        return contexto

    def _gerar_codigo(self, pergunta):
        """Usa Ollama para gerar código pandas"""
        contexto = self._preparar_contexto()
        
        prompt = f"""{contexto}

PERGUNTA DO USUÁRIO: {pergunta}

INSTRUÇÕES:
1. Gere código Python usando pandas para responder a pergunta
2. Use APENAS a variável 'df' que já existe
3. O código deve retornar um resultado claro (número, DataFrame pequeno, ou dicionário)
4. Armazene o resultado final em uma variável chamada 'resultado'
5. Não use print(), apenas calcule e armazene em 'resultado'
6. Retorne APENAS o código Python, sem explicações antes ou depois
7. Não use markdown, não use ```python, apenas o código puro

EXEMPLO DE RESPOSTA:
resultado = df.groupby('product')['amount_transacted'].sum().sort_values(ascending=False).head(1)

AGORA GERE O CÓDIGO PARA A PERGUNTA DO USUÁRIO:"""

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
            
            codigo_gerado = result.stdout.strip()
            
            # Limpar o código (remover markdown se houver)
            codigo_gerado = codigo_gerado.replace('```python', '').replace('```', '').strip()
            
            print(f"\n💻 Código gerado:\n{codigo_gerado}\n")
            
            return codigo_gerado
            
        except subprocess.TimeoutExpired:
            print("⏱️ Timeout ao consultar Ollama")
            return None
        except Exception as e:
            print(f"❌ Erro ao consultar Ollama: {e}")
            return None

    def _executar_codigo(self, codigo):
        """Executa o código gerado de forma segura"""
        try:
            # Criar namespace local com o DataFrame
            local_vars = {'df': self.df, 'pd': pd}
            
            # Se o código não define 'resultado', adicionar automaticamente
            if 'resultado' not in codigo and '=' not in codigo:
                codigo = f"resultado = {codigo}"
            
            # Executar o código
            exec(codigo, {"__builtins__": __builtins__, "pd": pd}, local_vars)
            
            # Retornar o resultado
            if 'resultado' in local_vars:
                return local_vars['resultado']
            else:
                return "⚠️ O código não definiu a variável 'resultado'"
                
        except Exception as e:
            return f"❌ Erro ao executar código: {str(e)}"

    def perguntar(self, pergunta):
        """Método principal: recebe pergunta e retorna resposta"""
        print(f"\n❓ Pergunta: {pergunta}")
        
        # Gerar código
        codigo = self._gerar_codigo(pergunta)
        
        if not codigo:
            return "❌ Não foi possível gerar código para essa pergunta"
        
        # Executar código
        resultado = self._executar_codigo(codigo)
        
        # Formatar resultado
        print("\n📊 Resultado:")
        if isinstance(resultado, pd.DataFrame):
            print(resultado.to_string())
        elif isinstance(resultado, pd.Series):
            print(resultado.to_string())
        else:
            print(resultado)
        
        return resultado


# Exemplo de uso
if __name__ == "__main__":
    # Inicializar agente
    agente = PandasAgent('data/operational_intelligence_transactions_db.csv')
    
    # Testar com uma pergunta
    agente.perguntar("Qual produto tem o maior TPV total?")