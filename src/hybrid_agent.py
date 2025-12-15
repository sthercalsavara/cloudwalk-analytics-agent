from sql_agent import SQLAgent
from pandas_agent import PandasAgent
import pandas as pd
import subprocess

class HybridAgent:
    def __init__(self, csv_path='data/operational_intelligence_transactions_db.csv', mode='auto'):
        """
        Inicializa agente híbrido que pode usar SQL ou Pandas
        
        Args:
            csv_path: caminho do CSV
            mode: 'sql', 'pandas', ou 'auto' (escolhe automaticamente)
        """
        self.csv_path = csv_path
        self.mode = mode
        
        print(f"🚀 Inicializando Agente Híbrido (modo: {mode})")
        
        # Inicializar agentes conforme o modo
        if mode == 'sql':
            self.sql_agent = SQLAgent(csv_path)
            self.pandas_agent = None
        elif mode == 'pandas':
            self.pandas_agent = PandasAgent(csv_path)
            self.sql_agent = None
        elif mode == 'auto':
            # Inicializar ambos
            self.sql_agent = SQLAgent(csv_path)
            self.pandas_agent = PandasAgent(csv_path)
        else:
            raise ValueError("mode deve ser 'sql', 'pandas' ou 'auto'")
    
    def _escolher_engine(self, pergunta):
        """
        Escolhe qual engine usar baseado na pergunta (modo auto)
        
        Regras simples:
        - Perguntas com agregações simples: SQL (mais eficiente)
        - Perguntas com cálculos complexos ou temporais: Pandas
        """
        pergunta_lower = pergunta.lower()
        
        # Keywords que sugerem usar Pandas
        pandas_keywords = [
            'ticket médio', 'média de', 'proporção', 'percentual',
            'crescimento', 'variação', 'tendência', 'dia da semana',
            'comparar com', 'calcular', 'dividir'
        ]
        
        # Keywords que sugerem usar SQL
        sql_keywords = [
            'maior', 'menor', 'total', 'soma', 'count', 'quantos',
            'listar', 'mostrar', 'top', 'ranking'
        ]
        
        # Contar ocorrências
        pandas_score = sum(1 for kw in pandas_keywords if kw in pergunta_lower)
        sql_score = sum(1 for kw in sql_keywords if kw in pergunta_lower)
        
        # Decisão
        if pandas_score > sql_score:
            return 'pandas'
        else:
            return 'sql'  # SQL como padrão para agregações simples
    
    def _interpretar_resultado(self, pergunta, resultado):
        """
        Interpreta o resultado em linguagem natural usando LLM
        """
        # Preparar resultado para o LLM
        if isinstance(resultado, pd.DataFrame):
            resultado_str = resultado.to_string(index=False, max_rows=20)
        elif isinstance(resultado, pd.Series):
            resultado_str = resultado.to_string(max_rows=20)
        else:
            resultado_str = str(resultado)
        
        prompt = f"""Você é um analista de dados especializado em business intelligence.

PERGUNTA DO USUÁRIO: {pergunta}

RESULTADO DA ANÁLISE:
{resultado_str}

INSTRUÇÕES:
1. Analise o resultado e responda a pergunta de forma clara e objetiva
2. Inclua insights e padrões encontrados
3. Use números formatados (ex: R$ 8,14 bilhões ao invés de 8.140541e+09)
4. Se for análise temporal, identifique tendências
5. Se houver comparações, destaque diferenças principais
6. Termine com recomendações práticas se relevante
7. Responda em português brasileiro
8. Seja conciso mas informativo (máximo 150 palavras)

RESPOSTA:"""

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
            
            interpretacao = result.stdout.strip()
            return interpretacao
            
        except Exception as e:
            return f"Não foi possível gerar interpretação: {str(e)}"

    def perguntar(self, pergunta, force_mode=None, com_interpretacao=True):
        """
        Faz pergunta ao agente
        
        Args:
            pergunta: pergunta em linguagem natural
            force_mode: força usar 'sql' ou 'pandas' (sobrescreve mode)
            com_interpretacao: se True, gera interpretação textual do resultado
        """
        # Determinar qual engine usar
        if force_mode:
            engine = force_mode
        elif self.mode == 'auto':
            engine = self._escolher_engine(pergunta)
            print(f"🎯 Modo automático: usando {engine.upper()}")
        else:
            engine = self.mode
        
        # Executar com o engine escolhido
        if engine == 'sql':
            if not self.sql_agent:
                print("⚠️ SQL Agent não inicializado, usando Pandas")
                resultado = self.pandas_agent.perguntar(pergunta)
            else:
                resultado = self.sql_agent.perguntar(pergunta)
        else:
            if not self.pandas_agent:
                print("⚠️ Pandas Agent não inicializado, usando SQL")
                resultado = self.sql_agent.perguntar(pergunta)
            else:
                resultado = self.pandas_agent.perguntar(pergunta)
        
        # Gerar interpretação em linguagem natural
        if com_interpretacao and not isinstance(resultado, str):
            print("\n💬 Gerando interpretação...")
            interpretacao = self._interpretar_resultado(pergunta, resultado)
            print(f"\n📝 Interpretação:\n{interpretacao}\n")
            
            return {
                'resultado': resultado,
                'interpretacao': interpretacao
            }
        
        return resultado
    
    def comparar_engines(self, pergunta):
        """
        Executa a mesma pergunta em ambos engines e compara resultados
        (Útil para debugging e demonstração)
        """
        if self.mode != 'auto':
            print("⚠️ comparar_engines só funciona no modo 'auto'")
            return
        
        print("=" * 60)
        print("🔍 COMPARANDO SQL vs PANDAS")
        print("=" * 60)
        
        print("\n📌 Tentando com SQL:")
        resultado_sql = self.sql_agent.perguntar(pergunta)
        
        print("\n" + "=" * 60)
        print("\n📌 Tentando com Pandas:")
        resultado_pandas = self.pandas_agent.perguntar(pergunta)
        
        print("\n" + "=" * 60)
        print("✅ Comparação concluída!")
        
        return {
            'sql': resultado_sql,
            'pandas': resultado_pandas
        }


# Exemplo de uso
if __name__ == "__main__":
    # Teste 1: Modo automático
    print("=" * 60)
    print("TESTE 1: Modo Automático")
    print("=" * 60)
    agente = HybridAgent(mode='auto')
    agente.perguntar("Qual produto tem o maior TPV total?")
    
    print("\n\n")
    
    # Teste 2: Forçar SQL
    print("=" * 60)
    print("TESTE 2: Forçando SQL")
    print("=" * 60)
    agente.perguntar("Quantos produtos diferentes existem?", force_mode='sql')
    
    print("\n\n")
    
    # Teste 3: Forçar Pandas
    print("=" * 60)
    print("TESTE 3: Forçando Pandas")
    print("=" * 60)
    agente.perguntar("Qual o ticket médio por produto?", force_mode='pandas')
    
    print("\n\n")
    
    # Teste 4: Comparar engines
    print("=" * 60)
    print("TESTE 4: Comparando Engines")
    print("=" * 60)
    agente.comparar_engines("Qual segmento (entity) tem maior TPV?")