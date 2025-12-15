import streamlit as st
import sys
import os
import pandas as pd

# Adicionar pasta src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.hybrid_agent import HybridAgent
from src.alerts import AlertSystem

# Configuração da página
st.set_page_config(
    page_title="Agente de BI CloudWalk",
    page_icon="🤖",
    layout="wide"
)

# CSS customizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🤖 Agente de BI CloudWalk</div>', unsafe_allow_html=True)
st.markdown("---")

# Inicializar sistemas
@st.cache_resource
def init_agent():
    with st.spinner("🔄 Inicializando agente..."):
        return HybridAgent(mode='auto')

@st.cache_resource
def init_alerts():
    with st.spinner("🔄 Inicializando alertas..."):
        return AlertSystem()

try:
    agente = init_agent()
    sistema_alertas = init_alerts()
    st.success("✅ Sistema inicializado!")
except Exception as e:
    st.error(f"❌ Erro: {e}")
    st.stop()

# Tabs principais
tab1, tab2 = st.tabs(["🤖 Agente Conversacional", "🚨 Alertas"])

# ==================== TAB 1: AGENTE ====================
with tab1:
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        modo = st.radio(
            "Modo de Execução:",
            ["Auto (Inteligente)", "SQL", "Pandas"]
        )
        
        modo_map = {
            "Auto (Inteligente)": None,
            "SQL": "sql",
            "Pandas": "pandas"
        }
        
        st.markdown("---")
        st.header("💡 Exemplos")
        
        exemplos = [
            "Qual produto tem maior TPV?",
            "Qual o ticket médio por produto?",
            "Como os dias da semana influenciam o TPV?",
            "Qual método de antecipação mais usado por PJ?"
        ]
        
        for exemplo in exemplos:
            if st.button(f"💬 {exemplo}", key=exemplo, use_container_width=True):
                st.session_state.pergunta = exemplo
    
    # Input
    st.header("❓ Faça sua Pergunta")
    
    pergunta = st.text_area(
        "Digite sua pergunta:",
        value=st.session_state.get('pergunta', ''),
        height=100,
        placeholder="Ex: Qual produto tem maior TPV?"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        executar = st.button("🚀 Perguntar", type="primary", use_container_width=True)
    with col2:
        limpar = st.button("🗑️ Limpar", use_container_width=True)
    
    if limpar:
        st.session_state.pergunta = ''
        st.rerun()
    
    # Executar
    if executar and pergunta:
        st.markdown("---")
        modo_exec = modo_map[modo]
        
        with st.spinner("🤖 Processando..."):
            try:
                from io import StringIO
                old_stdout = sys.stdout
                sys.stdout = captured = StringIO()
                
                resultado_obj = agente.perguntar(pergunta, force_mode=modo_exec, com_interpretacao=True)
                
                if isinstance(resultado_obj, dict) and 'interpretacao' in resultado_obj:
                    resultado = resultado_obj['resultado']
                    interpretacao = resultado_obj['interpretacao']
                else:
                    resultado = resultado_obj
                    interpretacao = None
                
                sys.stdout = old_stdout
                output = captured.getvalue()
                
                # Extrair código gerado
                linhas = output.split('\n')
                codigo_gerado = None
                tipo_codigo = None
                
                for i, linha in enumerate(linhas):
                    if '💻 SQL gerado:' in linha and i+1 < len(linhas):
                        codigo_gerado = linhas[i+1]
                        tipo_codigo = "SQL"
                    elif '💻 Código gerado:' in linha and i+1 < len(linhas):
                        codigo_gerado = linhas[i+1]
                        tipo_codigo = "Python"
                
                # Mostrar interpretação
                if interpretacao:
                    st.subheader("💬 Interpretação:")
                    st.info(interpretacao)
                
                # Mostrar código
                if codigo_gerado:
                    st.subheader(f"💻 {tipo_codigo} Gerado:")
                    st.code(codigo_gerado, language='sql' if tipo_codigo == 'SQL' else 'python')
                
                # Mostrar resultado
                st.subheader("📊 Resultado:")
                
                if isinstance(resultado, pd.DataFrame):
                    st.dataframe(resultado, use_container_width=True)
                    
                    csv = resultado.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV", csv, "resultado.csv", "text/csv")
                    
                elif isinstance(resultado, pd.Series):
                    df_result = resultado.reset_index()
                    df_result.columns = ['Categoria', 'Valor']
                    st.dataframe(df_result, use_container_width=True)
                    
                elif isinstance(resultado, str):
                    if "❌" in resultado or "⚠️" in resultado:
                        st.error(resultado)
                    else:
                        st.success(resultado)
                else:
                    st.write(resultado)
                
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
                st.exception(e)
    
    elif executar and not pergunta:
        st.warning("⚠️ Digite uma pergunta!")

# ==================== TAB 2: ALERTAS ====================
with tab2:
    st.header("🚨 Sistema de Alertas")
    
    # Seletor de data
    kpis_diarios = sistema_alertas.calcular_kpis_diarios()
    data_min = kpis_diarios['day'].min().date()
    data_max = kpis_diarios['day'].max().date()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        data_selecionada = st.date_input(
            "Data:",
            value=data_max,
            min_value=data_min,
            max_value=data_max
        )
    
    with col2:
        threshold = st.slider("Threshold (%)", 5, 30, 15, key="threshold_slider")
    
    with col3:
        st.write("")
        st.caption(f"Alertas > {threshold}%")
    
    st.markdown("---")
    
    # Calcular variações
    variacoes = sistema_alertas.calcular_variacoes(pd.to_datetime(data_selecionada))
    
    if variacoes:
        # KPIs
        st.subheader("💰 KPIs do Dia")
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric("TPV", f"R$ {variacoes['tpv_atual']:,.2f}")
        
        with c2:
            if variacoes['var_d1_pct'] is not None:
                delta_color = "inverse" if abs(variacoes['var_d1_pct']) > threshold else "normal"
                st.metric("vs D-1", f"{variacoes['var_d1_pct']:.2f}%", 
                         delta=f"{variacoes['var_d1_pct']:.2f}%", delta_color=delta_color)
        
        with c3:
            if variacoes['var_d7_pct'] is not None:
                delta_color = "inverse" if abs(variacoes['var_d7_pct']) > threshold else "normal"
                st.metric("vs D-7", f"{variacoes['var_d7_pct']:.2f}%",
                         delta=f"{variacoes['var_d7_pct']:.2f}%", delta_color=delta_color)
        
        with c4:
            if variacoes['var_30d_pct'] is not None:
                delta_color = "inverse" if abs(variacoes['var_30d_pct']) > threshold else "normal"
                st.metric("vs 30d", f"{variacoes['var_30d_pct']:.2f}%",
                         delta=f"{variacoes['var_30d_pct']:.2f}%", delta_color=delta_color)
        
        st.markdown("---")
        
        # Alertas
        st.subheader("🚨 Alertas")
        
        # Análise por período
        st.markdown("##### 📊 Análise por Período:")
        
        periodos_analise = []
        
        # D-1
        if variacoes['var_d1_pct'] is not None:
            ultrapassa = abs(variacoes['var_d1_pct']) > threshold
            emoji = "⚠️" if ultrapassa else "✅"
            status = "ALERTA" if ultrapassa else "OK"
            periodos_analise.append({
                'Período': 'D-1 (dia anterior)',
                'Variação': f"{variacoes['var_d1_pct']:+.2f}%",
                'Status': f"{emoji} {status}"
            })
        
        # D-7
        if variacoes['var_d7_pct'] is not None:
            ultrapassa = abs(variacoes['var_d7_pct']) > threshold
            emoji = "⚠️" if ultrapassa else "✅"
            status = "ALERTA" if ultrapassa else "OK"
            periodos_analise.append({
                'Período': 'D-7 (semana passada)',
                'Variação': f"{variacoes['var_d7_pct']:+.2f}%",
                'Status': f"{emoji} {status}"
            })
        
        # D-30
        if variacoes['var_30d_pct'] is not None:
            ultrapassa = abs(variacoes['var_30d_pct']) > threshold
            emoji = "⚠️" if ultrapassa else "✅"
            status = "ALERTA" if ultrapassa else "OK"
            periodos_analise.append({
                'Período': 'Média 30 dias',
                'Variação': f"{variacoes['var_30d_pct']:+.2f}%",
                'Status': f"{emoji} {status}"
            })
        
        # Tabela de análise
        if periodos_analise:
            df_analise = pd.DataFrame(periodos_analise)
            st.dataframe(df_analise, use_container_width=True, hide_index=True)
        
        # Contador de alertas
        alertas, _ = sistema_alertas.detectar_anomalias(threshold_pct=threshold)
        
        if len(alertas) > 0:
            st.warning(f"🎯 **Threshold: {threshold}%** → **{len(alertas)} alerta(s) detectado(s)**")
        else:
            st.success(f"🎯 **Threshold: {threshold}%** → **Nenhum alerta detectado**")
        
        st.markdown("---")
        
        # Detalhes dos alertas
        if alertas:
            st.markdown("##### 🚨 Detalhes dos Alertas:")
            for alerta in alertas:
                msg = sistema_alertas.formatar_alerta(alerta, variacoes)
                if alerta['severidade'] == 'ALTA':
                    st.error(msg)
                else:
                    st.warning(msg)
        
        st.markdown("---")
        
        # Segmentos
        segmentos, _ = sistema_alertas.calcular_kpis_por_segmento(pd.to_datetime(data_selecionada))
        
        sc1, sc2, sc3 = st.columns(3)
        
        with sc1:
            st.subheader("📦 Top Produtos")
            top = segmentos['produto'].sort_values('amount_transacted', ascending=False).head(3)
            for idx, row in top.iterrows():
                st.write(f"**{row['product']}**: R$ {row['amount_transacted']:,.2f}")
        
        with sc2:
            st.subheader("👥 Segmento")
            for idx, row in segmentos['entity'].iterrows():
                st.write(f"**{row['entity']}**: R$ {row['amount_transacted']:,.2f}")
        
        with sc3:
            st.subheader("💳 Pagamento")
            for idx, row in segmentos['payment_method'].iterrows():
                st.write(f"**{row['payment_method']}**: R$ {row['amount_transacted']:,.2f}")
    
    else:
        st.error("❌ Sem dados para a data selecionada")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    🚀 Agente CloudWalk | Powered by Ollama + Python
</div>
""", unsafe_allow_html=True)