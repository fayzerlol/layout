import streamlit as st
import pandas as pd
import numpy as np
import os
from typing import Optional

# Configurações da página
st.set_page_config(
    page_title="Dashboard de Equipamentos",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #0e1117;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #2d3747;
    }
    .stDataFrame {
        border: 1px solid #2d3747;
        border-radius: 0.5rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        background-color: #0e1117;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Carrega os dados do Excel com cache"""
    try:
        df = pd.read_excel('equipamentos_filtrado.xlsx')
        
        # Limpeza básica
        df = df.fillna({
            'nota_quantitativa': 0,
            'nota_qualitativa': 0
        })
        
        # Cálculo do status final
        df['status_final'] = df['nota_quantitativa'] + df['nota_qualitativa']
        
        # Determinação da criticidade
        def get_criticidade(nota):
            if nota <= 4:
                return 'Crítico'
            elif nota <= 7:
                return 'Atenção'
            else:
                return 'OK'
        
        df['criticidade'] = df['status_final'].apply(get_criticidade)
        df['status'] = np.where(df['criticidade'].isin(['OK']), 'CONFORME', 'NÃO CONFORME')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def main():
    # Cabeçalho
    st.title("🏭 Dashboard de Equipamentos")
    st.markdown("---")
    
    # Carrega dados
    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponível para exibição")
        return
    
    # Sidebar com filtros
    with st.sidebar:
        st.header("Filtros")
        
        # Busca por texto
        busca = st.text_input("🔍 Busca por TAG/Local/Sistema")
        
        # Filtros de seleção múltipla
        col1, col2 = st.columns(2)
        with col1:
            complexos = st.multiselect(
                "Complexo",
                options=sorted(df['complexo'].unique())
            )
        
        with col2:
            sistemas = st.multiselect(
                "Sistema",
                options=sorted(df['Sistema'].unique())
            )
        
        # Filtro de criticidade
        criticidades = st.multiselect(
            "Criticidade",
            options=['Crítico', 'Atenção', 'OK'],
            default=['Crítico', 'Atenção', 'OK']
        )
        
        # Checkbox para pendentes
        apenas_pendentes = st.checkbox("Apenas Pendentes")
    
    # Aplicar filtros
    df_filtered = df.copy()
    
    if busca:
        mask = df_filtered[['TAG', 'Local', 'Sistema']].astype(str).apply(
            lambda x: x.str.contains(busca, case=False, na=False)
        ).any(axis=1)
        df_filtered = df_filtered[mask]
    
    if complexos:
        df_filtered = df_filtered[df_filtered['complexo'].isin(complexos)]
    
    if sistemas:
        df_filtered = df_filtered[df_filtered['Sistema'].isin(sistemas)]
    
    if criticidades:
        df_filtered = df_filtered[df_filtered['criticidade'].isin(criticidades)]
    
    if apenas_pendentes:
        df_filtered = df_filtered[df_filtered['status_final'] == 0]
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_conforme = len(df_filtered[df_filtered['status'] == 'CONFORME'])
        st.metric("Conformes", total_conforme)
    
    with col2:
        total_nao_conforme = len(df_filtered[df_filtered['status'] == 'NÃO CONFORME'])
        st.metric("Não Conformes", total_nao_conforme)
    
    with col3:
        total_pendentes = len(df_filtered[df_filtered['status_final'] == 0])
        st.metric("Pendentes", total_pendentes)
    
    with col4:
        st.metric("Total", len(df_filtered))
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "⚠️ Críticos", "📋 Detalhes"])
    
    with tab1:
        st.subheader("Visão Geral dos Equipamentos")
        cols_display = ['TAG', 'complexo', 'Sistema', 'Local', 'status_final', 'criticidade', 'status']
        st.dataframe(
            df_filtered[cols_display].sort_values('criticidade'),
            use_container_width=True
        )
        
        # Gráfico de distribuição
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Distribuição por Criticidade")
            criticos_data = df_filtered['criticidade'].value_counts()
            st.bar_chart(criticos_data)
        
        with col2:
            st.subheader("Status por Complexo")
            complex_status = pd.crosstab(df_filtered['complexo'], df_filtered['status'])
            st.bar_chart(complex_status)
    
    with tab2:
        st.subheader("Equipamentos Críticos")
        criticos = df_filtered[df_filtered['criticidade'] == 'Crítico']
        st.dataframe(
            criticos[['TAG', 'complexo', 'Sistema', 'Local', 'status_final']],
            use_container_width=True
        )
    
    with tab3:
        st.subheader("Detalhes do Equipamento")
        tag_selecionada = st.selectbox(
            "Selecione uma TAG",
            options=df_filtered['TAG'].unique()
        )
        
        if tag_selecionada:
            equip = df_filtered[df_filtered['TAG'] == tag_selecionada].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**TAG:** {equip['TAG']}")
                st.markdown(f"**Complexo:** {equip['complexo']}")
                st.markdown(f"**Sistema:** {equip['Sistema']}")
            with col2:
                st.markdown(f"**Status:** {equip['status']}")
                st.markdown(f"**Criticidade:** {equip['criticidade']}")
                st.markdown(f"**Nota Final:** {equip['status_final']}")

if __name__ == "__main__":
    main()
