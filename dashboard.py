import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional
import os

# Configurações iniciais
st.set_page_config(
    page_title="Dashboard de Equipamentos",
    page_icon="📊",
    layout="wide"
)

# Constantes
EXCEL_FILE = 'equipamentos_filtrado.xlsx'
LOGO = 'download.png'

# Funções auxiliares
@st.cache_data
def load_data() -> pd.DataFrame:
    """Carrega os dados do Excel com cache para melhor performance"""
    try:
        df = pd.read_excel(EXCEL_FILE)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo '{EXCEL_FILE}': {str(e)}")
        return pd.DataFrame()

def get_status_class(value: Optional[float]) -> str:
    """Determina a classe de status baseada no valor"""
    if pd.isna(value):
        return "Sem Nota"
    value = float(value)
    if value <= 4.0:
        return "Crítico"
    elif value <= 7.0:
        return "Atenção"
    return "Conforme"

def style_metric(text: str, color: str = "#0e1117") -> str:
    """Estiliza as métricas do dashboard"""
    return f'''
    <div style="
        background-color: {color};
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        text-align: center;
        font-weight: bold;
        margin: 4px 0px;
    ">
        {text}
    </div>
    '''

def main():
    # CSS personalizado
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .metric-card {
            background: #1e2130;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        .custom-metric {
            border-left: 4px solid #00a86b;
            padding-left: 10px;
        }
        .dataframe {
            font-size: 12px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Cabeçalho
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        if os.path.exists(LOGO):
            st.image(LOGO, use_column_width=True)
    with col2:
        st.title("Dashboard de Equipamentos")
        st.caption("Sistema de Monitoramento e Análise")

    # Carregamento dos dados
    df = load_data()
    if df.empty:
        st.warning("Nenhum dado disponível para exibição.")
        return

    # Preparação dos dados
    df['status_final'] = df['nota_quantitativa'].fillna(0) + df['nota_qualitativa'].fillna(0)
    df['status_class'] = df['status_final'].apply(get_status_class)
    df['pendente'] = df[['nota_quantitativa', 'nota_qualitativa']].isna().any(axis=1)

    # Sidebar com filtros
    st.sidebar.title("Filtros")
    
    # Filtro de busca
    search = st.sidebar.text_input("🔍 Busca por TAG/Local/Sistema")
    
    # Filtros de seleção múltipla
    complexos = sorted(df['complexo'].dropna().unique())
    sistemas = sorted(df['Sistema'].dropna().unique())
    status_options = ['Crítico', 'Atenção', 'Conforme', 'Sem Nota']
    
    selected_complexos = st.sidebar.multiselect("Complexo", complexos)
    selected_sistemas = st.sidebar.multiselect("Sistema", sistemas)
    selected_status = st.sidebar.multiselect("Status", status_options, default=status_options)
    
    # Aplicação dos filtros
    filtered_df = df.copy()
    
    if search:
        mask = filtered_df[['TAG', 'Local', 'Sistema']].astype(str).apply(
            lambda x: x.str.contains(search, case=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if selected_complexos:
        filtered_df = filtered_df[filtered_df['complexo'].isin(selected_complexos)]
    
    if selected_sistemas:
        filtered_df = filtered_df[filtered_df['Sistema'].isin(selected_sistemas)]
    
    if selected_status:
        filtered_df = filtered_df[filtered_df['status_class'].isin(selected_status)]

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    conformes = len(filtered_df[filtered_df['status_class'] == 'Conforme'])
    criticos = len(filtered_df[filtered_df['status_class'] == 'Crítico'])
    atencao = len(filtered_df[filtered_df['status_class'] == 'Atenção'])
    total = len(filtered_df)
    
    col1.markdown(style_metric(f"Conformes\n{conformes}", "#00a86b"), unsafe_allow_html=True)
    col2.markdown(style_metric(f"Críticos\n{criticos}", "#ff4b4b"), unsafe_allow_html=True)
    col3.markdown(style_metric(f"Atenção\n{atencao}", "#ffa500"), unsafe_allow_html=True)
    col4.markdown(style_metric(f"Total\n{total}", "#1e88e5"), unsafe_allow_html=True)

    # Abas de conteúdo
    tabs = st.tabs(["Visão Geral", "Pendentes", "Críticos", "Relatórios"])
    
    with tabs[0]:
        st.subheader("Lista de Equipamentos")
        st.dataframe(
            filtered_df[[
                'TAG', 'complexo', 'Sistema', 'Local',
                'nota_quantitativa', 'nota_qualitativa',
                'status_final', 'status_class'
            ]].sort_values('status_class'),
            use_container_width=True
        )

    with tabs[1]:
        pendentes = filtered_df[filtered_df['pendente']]
        st.subheader(f"Equipamentos Pendentes ({len(pendentes)})")
        st.dataframe(
            pendentes[['TAG', 'complexo', 'Sistema', 'Local']],
            use_container_width=True
        )

    with tabs[2]:
        criticos = filtered_df[filtered_df['status_class'] == 'Crítico']
        st.subheader(f"Equipamentos Críticos ({len(criticos)})")
        st.dataframe(
            criticos[['TAG', 'complexo', 'Sistema', 'Local', 'status_final']],
            use_container_width=True
        )

    with tabs[3]:
        st.subheader("Relatórios")
        if 'report_id' in filtered_df.columns:
            reports = filtered_df.dropna(subset=['report_id'])
            if not reports.empty:
                selected_tag = st.selectbox(
                    "Selecione o equipamento para ver o relatório",
                    options=reports['TAG'].unique()
                )
                
                if selected_tag:
                    report_id = reports[reports['TAG'] == selected_tag]['report_id'].iloc[0]
                    file_id = str(report_id).split('_')[-1].split('.')[0]
                    
                    if st.button("Visualizar Relatório"):
                        st.markdown(f'''
                            <iframe 
                                src="https://drive.google.com/file/d/{file_id}/preview" 
                                width="100%" 
                                height="600px" 
                                frameborder="0">
                            </iframe>
                        ''', unsafe_allow_html=True)
            else:
                st.info("Nenhum relatório disponível.")
        else:
            st.info("Sistema de relatórios não configurado.")

if __name__ == "__main__":
    main()
