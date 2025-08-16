import os
import io
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional

# ------------------------
# Configurações e Tema
# ------------------------
st.set_page_config(
    page_title="Dashboard de Equipamentos - Grupo Franzen",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cores e estilo
COLORS = {
    "primary": "#FFC107",    # amarelo Franzen
    "secondary": "#2196F3",  # azul
    "success": "#4CAF50",    # verde
    "warning": "#FF9800",    # laranja
    "danger": "#F44336",     # vermelho
    "dark": "#1E1F24",       # fundo escuro
    "light": "#F5F5F5"       # texto claro
}

# CSS customizado
st.markdown(f"""
<style>
    /* Tema global */
    .stApp {{
        background-color: {COLORS['dark']};
        color: {COLORS['light']};
    }}
    
    /* Cards e containers */
    .css-1r6slb0 {{  /* Sidebar */
        background-color: #252731;
    }}
    .block-container {{
        padding: 2rem;
    }}
    
    /* Métricas e status */
    .metric-card {{
        background: #2a2d3e;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #3a3f59;
    }}
    .status-conforme {{
        color: {COLORS['success']};
        font-weight: bold;
    }}
    .status-nao-conforme {{
        color: {COLORS['danger']};
        font-weight: bold;
    }}
    .status-pendente {{
        color: {COLORS['warning']};
        font-weight: bold;
    }}
    
    /* Botões e inputs */
    .stButton > button {{
        background-color: {COLORS['primary']};
        color: #000;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
    }}
    .stSelectbox > div > div {{
        background-color: #2a2d3e;
        color: {COLORS['light']};
    }}
    
    /* Tabelas */
    .dataframe {{
        background-color: #2a2d3e;
    }}
    .dataframe td {{
        font-size: 14px;
    }}
    
    /* PDF viewer */
    .pdf-viewer {{
        border: 1px solid #3a3f59;
        border-radius: 8px;
        overflow: hidden;
    }}
</style>
""", unsafe_allow_html=True)

# ------------------------
# Login
# ------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None

if not st.session_state.authenticated:
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        if username == "admin" and password == "admin123":
            st.session_state.authenticated = True
            st.session_state.user_role = "admin"
            st.experimental_rerun()
        elif username == "user" and password == "user123":
            st.session_state.authenticated = True
            st.session_state.user_role = "user"
            st.experimental_rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos")
    st.stop()

# ------------------------
# Funções Auxiliares
# ------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    """Carrega e processa os dados do Excel"""
    try:
        df = pd.read_excel("equipamentos_filtrado.xlsx")
        
        # Calcular status de conformidade
        def calc_status(row):
            pqs_rec = row['PQS_Rec_Total'] if pd.notnull(row['PQS_Rec_Total']) else 0
            pqs_inst = row['PQS_Inst_Total'] if pd.notnull(row['PQS_Inst_Total']) else 0
            liq_rec = row['Liq_Rec_Total'] if pd.notnull(row['Liq_Rec_Total']) else 0
            liq_inst = row['Liq_Inst_Total'] if pd.notnull(row['Liq_Inst_Total']) else 0
            
            if pqs_rec == 0 and liq_rec == 0:
                return "CONFORME"
            elif (pqs_rec > 0 and pqs_inst == 0) or (liq_rec > 0 and liq_inst == 0):
                return "NÃO CONFORME"
            elif pqs_inst >= pqs_rec and liq_inst >= liq_rec:
                return "CONFORME"
            else:
                return "NÃO CONFORME"
        
        if 'Computed_Status' not in df.columns:
            df['Computed_Status'] = df.apply(calc_status, axis=1)
        
        # Calcular nota final
        qual_cols = ['5.)Layout Monitoramento Sensores/Cabo Linear',
                    '6.) Layout Bicos e Mangueiras',
                    '7.)Layout Posicionamento Acionadores e Painel da Cabine']
        
        df['nota_qualitativa'] = df[qual_cols].mean(axis=1)
        df['status_final'] = df['nota_quantitativa'].fillna(0) + df['nota_qualitativa'].fillna(0)
        
        # Determinar criticidade
        def get_criticidade(nota):
            if pd.isna(nota):
                return "Sem Nota"
            if nota <= 4.0:
                return "Crítico"
            elif nota <= 7.0:
                return "Atenção"
            return "OK"
        
        df['criticidade'] = df['status_final'].apply(get_criticidade)
        df['pendente'] = df[qual_cols + ['nota_qualitativa']].isna().any(axis=1)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def export_excel(df: pd.DataFrame) -> bytes:
    """Exporta DataFrame para Excel formatado"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Dados', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Dados']
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#283593',
            'font_color': 'white',
            'border': 1
        })
        
        conforme_format = workbook.add_format({
            'bg_color': '#E8F5E9',
            'font_color': '#2E7D32'
        })
        
        nao_conforme_format = workbook.add_format({
            'bg_color': '#FFEBEE',
            'font_color': '#C62828'
        })
        
        # Aplicar formatos
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15)
        
        # Formatação condicional
        status_col = df.columns.get_loc('Computed_Status')
        worksheet.conditional_format(1, status_col, len(df), status_col, {
            'type': 'text',
            'criteria': 'containing',
            'value': 'CONFORME',
            'format': conforme_format
        })
        
        worksheet.conditional_format(1, status_col, len(df), status_col, {
            'type': 'text',
            'criteria': 'containing',
            'value': 'NÃO CONFORME',
            'format': nao_conforme_format
        })
    
    return output.getvalue()

# ------------------------
# Carregar Dados
# ------------------------
df = load_data()

# ------------------------
# Sidebar e Filtros
# ------------------------
st.sidebar.title("Filtros")

# Multi-select filters
complexos = sorted(df['complexo'].dropna().unique())
sistemas = sorted(df['Sistema'].dropna().unique())
locais = sorted(df['Local'].dropna().unique())

selected_complexos = st.sidebar.multiselect("Complexo", complexos)
selected_sistemas = st.sidebar.multiselect("Sistema", sistemas)
selected_locais = st.sidebar.multiselect("Local", locais)
search_tag = st.sidebar.text_input("Buscar TAG")

# Apply filters
filtered_df = df.copy()
if selected_complexos:
    filtered_df = filtered_df[filtered_df['complexo'].isin(selected_complexos)]
if selected_sistemas:
    filtered_df = filtered_df[filtered_df['Sistema'].isin(selected_sistemas)]
if selected_locais:
    filtered_df = filtered_df[filtered_df['Local'].isin(selected_locais)]
if search_tag:
    filtered_df = filtered_df[filtered_df['TAG'].str.contains(search_tag, case=False, na=False)]

# ------------------------
# Tabs Layout
# ------------------------
tabs = st.tabs(["Dashboard", "Equipamentos", "Notas Qualitativas", "Relatórios"])

with tabs[0]:
    st.title("Dashboard de Equipamentos")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(filtered_df)
    conformes = (filtered_df['Computed_Status'] == 'CONFORME').sum()
    nao_conformes = (filtered_df['Computed_Status'] == 'NÃO CONFORME').sum()
    pendentes = filtered_df['pendente'].sum()
    
    col1.metric("Total", total)
    col2.metric("Conformes", conformes)
    col3.metric("Não Conformes", nao_conformes)
    col4.metric("Pendentes", pendentes)
    
    # Gráficos
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Status por Complexo")
        complex_status = (filtered_df.groupby(['complexo', 'Computed_Status'])
                         .size().reset_index(name='count'))
        
        chart = alt.Chart(complex_status).mark_bar().encode(
            x='complexo:N',
            y='count:Q',
            color=alt.Color('Computed_Status:N',
                          scale=alt.Scale(domain=['CONFORME', 'NÃO CONFORME'],
                                        range=[COLORS['success'], COLORS['danger']])),
            tooltip=['complexo', 'Computed_Status', 'count']
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
    
    with chart_col2:
        st.subheader("Distribuição de Criticidade")
        crit_count = filtered_df['criticidade'].value_counts()
        
        colors = ['#F44336', '#FFA726', '#66BB6A']
        pie = alt.Chart(pd.DataFrame({
            'criticidade': crit_count.index,
            'count': crit_count.values
        })).mark_arc().encode(
            theta='count:Q',
            color=alt.Color('criticidade:N',
                          scale=alt.Scale(domain=['Crítico', 'Atenção', 'OK'],
                                        range=colors)),
            tooltip=['criticidade', 'count']
        ).properties(height=300)
        
        st.altair_chart(pie, use_container_width=True)

with tabs[1]:
    st.title("Lista de Equipamentos")
    
    # Tabela principal
    cols_to_show = ['TAG', 'complexo', 'Sistema', 'Local', 'Modelo',
                    'PQS_Rec_Total', 'PQS_Inst_Total',
                    'Liq_Rec_Total', 'Liq_Inst_Total',
                    'Computed_Status', 'criticidade']
    
    st.dataframe(filtered_df[cols_to_show].style.apply(lambda x: [
        f"background-color: {'#E8F5E9' if v == 'CONFORME' else '#FFEBEE' if v == 'NÃO CONFORME' else 'transparent'}"
        for v in x
    ], axis=1), height=400, use_container_width=True)
    
    # Export buttons
    col1, col2 = st.columns(2)
    excel_data = export_excel(filtered_df)
    col1.download_button("📥 Exportar Excel",
                        data=excel_data,
                        file_name="equipamentos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    col2.download_button("📥 Exportar CSV",
                        data=csv_data,
                        file_name="equipamentos.csv",
                        mime="text/csv")

with tabs[2]:
    st.title("Notas Qualitativas")
    
    # Seletor de equipamento
    selected_tag = st.selectbox("Selecione o Equipamento (TAG)",
                              filtered_df['TAG'].unique())
    
    if selected_tag:
        equip = filtered_df[filtered_df['TAG'] == selected_tag].iloc[0]
        
        st.markdown(f"""
        **Complexo:** {equip['complexo']}  
        **Sistema:** {equip['Sistema']}  
        **Local:** {equip['Local']}  
        **Status atual:** {equip['Computed_Status']}
        """)
        
        # Notas qualitativas
        nota_cols = ['5.)Layout Monitoramento Sensores/Cabo Linear',
                    '6.) Layout Bicos e Mangueiras',
                    '7.)Layout Posicionamento Acionadores e Painel da Cabine']
        
        st.subheader("Avaliação")
        for col in nota_cols:
            current = float(equip[col]) if pd.notnull(equip[col]) else 3.0
            st.select_slider(col, options=[1,1.5,2,2.5,3,3.5,4,4.5,5],
                           value=current, key=f"slider_{col}")
        
        # Campo obrigatório de observação
        obs = st.text_area("Observações (obrigatório)",
                          value=equip.get('Observação', ''),
                          height=100)
        
        if st.button("Salvar Avaliação"):
            if not obs.strip():
                st.error("O campo de observações é obrigatório!")
            else:
                st.success("Avaliação salva com sucesso!")
                # Aqui implementar lógica de salvar no DataFrame/Excel

with tabs[3]:
    st.title("Relatórios")
    
    # Lista de equipamentos com relatório
    has_report = filtered_df[filtered_df['report_id'].notna()]
    
    if not has_report.empty:
        selected = st.selectbox("Selecione o equipamento para ver o relatório",
                              has_report['TAG'])
        
        if selected:
            report_id = has_report[has_report['TAG'] == selected]['report_id'].iloc[0]
            url = f"https://drive.google.com/file/d/{report_id}/preview"
            
            st.markdown(f'''
            <div class="pdf-viewer">
                <iframe src="{url}"
                        width="100%"
                        height="600"
                        frameborder="0">
                </iframe>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("Nenhum relatório disponível para os filtros atuais")
