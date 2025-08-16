import os
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional

DATA_FILE = 'data.csv'
LOGO = 'download.png'


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_FILE):
        st.error(f"Arquivo de dados '{DATA_FILE}' não encontrado no diretório.")
        return pd.DataFrame()
    return pd.read_csv(DATA_FILE)


def criticality_from_status(status: Optional[float]) -> str:
    # status_final: <=4 crítico, >4 e <=7 atenção, >7 ok
    try:
        v = float(status)
    except Exception:
        return 'Sem Nota'
    if v <= 4.0:
        return 'Crítico'
    if v <= 7.0:
        return 'Atenção'
    return 'OK'


def style_metric(text: str, bgcolor: str = '#111') -> str:
    return f'<div style="background:{bgcolor};padding:12px;border-radius:8px;color:#fff;font-weight:700;text-align:center">{text}</div>'


def main():
    st.set_page_config(page_title='Dashboard Profissional - Equipamentos', layout='wide')

    # CSS
    st.markdown("""
    <style>
    .header{display:flex;align-items:center;gap:18px}
    .card{background:#0f1720;padding:16px;border-radius:12px;margin-bottom:14px}
    .kpi{background:linear-gradient(90deg,#f4c247,#00a85e);padding:10px;border-radius:10px;color:#111;font-weight:700}
    table.dataframe{border-collapse:separate; border-spacing:0 6px}
    .tag-btn{background:#111;border-radius:6px;color:#f4c247;padding:6px 10px}
    </style>
    """, unsafe_allow_html=True)

    # Header
    cols = st.columns([0.15, 0.85])
    with cols[0]:
        if os.path.exists(LOGO):
            st.image(LOGO, use_column_width=True)
    with cols[1]:
        st.title('Dashboard Profissional — Equipamentos')
        st.caption('Visual moderno, filtros de criticidade, pendências e relatórios em modal')

    df = load_data()
    if df.empty:
        return

    # Precompute columns
    if 'status_final' not in df.columns:
        df['status_final'] = df.get('nota_quantitativa', np.nan) + df.get('nota_qualitativa', np.nan)
    df['criticidade'] = df['status_final'].apply(criticality_from_status)
    df['Computed_Status'] = np.where(df['criticidade'].isin(['OK', 'Atenção']), 'CONFORME', 'NÃO CONFORME')
    df['pendente'] = df[['nota_quantitativa', 'nota_qualitativa']].isna().any(axis=1)

    # Sidebar controls
    st.sidebar.header('Filtros Avançados')
    q = st.sidebar.text_input('Busca rápida (TAG, Modelo, Local)')
    complexo = st.sidebar.multiselect('Complexo', options=sorted(df['complexo'].dropna().unique()))
    sistema = st.sidebar.multiselect('Sistema', options=sorted(df['Sistema'].dropna().unique()))
    criticidade = st.sidebar.multiselect('Criticidade', options=['Crítico', 'Atenção', 'OK', 'Sem Nota'], default=['Crítico', 'Atenção', 'OK', 'Sem Nota'])
    apenas_pendentes = st.sidebar.checkbox('Mostrar apenas pendentes', value=False)

    # Apply filters
    filtered = df.copy()
    if q:
        mask = filtered[['TAG', 'Modelo', 'Local']].astype(str).apply(lambda row: row.str.contains(q, case=False, na=False))
        filtered = filtered[mask.any(axis=1)]
    if complexo:
        filtered = filtered[filtered['complexo'].isin(complexo)]
    if sistema:
        filtered = filtered[filtered['Sistema'].isin(sistema)]
    if criticidade:
        filtered = filtered[filtered['criticidade'].isin(criticidade)]
    if apenas_pendentes:
        filtered = filtered[filtered['pendente']]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(style_metric(f'Conforme: {int(df[~df["pendente"] & (df["Computed_Status"]=="CONFORME")].shape[0])}'), unsafe_allow_html=True)
    c2.markdown(style_metric(f'Não Conforme: {int((df["Computed_Status"]=="NÃO CONFORME").sum())}'), unsafe_allow_html=True)
    c3.markdown(style_metric(f'Pendentes: {int(df["pendente"].sum())}'), unsafe_allow_html=True)
    c4.markdown(style_metric(f'Total: {len(df)}'), unsafe_allow_html=True)

    # Selector por criticidade
    st.markdown('---')
    st.subheader('Painel — Seleção por Criticidade')
    tabs = st.tabs(['Tabela Completa', 'Pendentes', 'Críticos', 'Relatórios'])

    with tabs[0]:
        st.markdown('### Tabela de Equipamentos (interativa)')
        display_cols = ['complexo', 'Local', 'TAG', 'Sistema', 'Modelo', 'PQS_Rec_Total', 'PQS_Inst_Total', 'Liq_Rec_Total', 'Liq_Inst_Total', 'nota_quantitativa', 'nota_qualitativa', 'status_final', 'criticidade']
        st.dataframe(filtered[display_cols].sort_values(['criticidade', 'status_final'], ascending=[True, True]), use_container_width=True)

    with tabs[1]:
        st.markdown('### Equipamentos Pendentes de Nota')
        pend = filtered[filtered['pendente']]
        st.dataframe(pend[['TAG', 'complexo', 'Local', 'nota_quantitativa', 'nota_qualitativa', 'observacao']], use_container_width=True)

    with tabs[2]:
        st.markdown('### Equipamentos Críticos (status_final <= 4)')
        crit = filtered[filtered['criticidade'] == 'Crítico']
        st.dataframe(crit[['TAG', 'complexo', 'Local', 'status_final', 'observacao']], use_container_width=True)

    with tabs[3]:
        st.markdown('### Relatórios — Abrir em Modal')
        tags_with_reports = df.dropna(subset=['report_id'])[['TAG', 'report_id']]
        if tags_with_reports.empty:
            st.info('Nenhum relatório encontrado.')
        else:
            row = st.selectbox('Escolha equipamento para visualizar o PDF', tags_with_reports['TAG'])
            report = tags_with_reports[tags_with_reports['TAG'] == row]['report_id'].values[0]
            file_id = str(report)
            if '_' in file_id:
                file_id = file_id.split('_')[-1]
            if '.' in file_id:
                file_id = file_id.split('.')[0]
            url = f'https://drive.google.com/file/d/{file_id}/preview'
            if st.button('Abrir Relatório (Modal)'):
                with st.modal('Relatório PDF'):
                    st.markdown(f'<iframe src="{url}" width="100%" height="650"></iframe>', unsafe_allow_html=True)

    # Quick action: abrir detalhes de um equipamento
    st.markdown('---')
    st.subheader('Abrir detalhe rápido')
    quick_tag = st.selectbox('Selecionar TAG', options=filtered['TAG'].unique())
    if quick_tag:
        row = df[df['TAG'] == quick_tag].iloc[0]
        st.markdown(f"**{row['TAG']}** — {row.get('Modelo','')} | {row.get('Sistema','')}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric('Status Carga', row.get('Computed_Status','-'))
            st.metric('Status Final', row.get('status_final', '-'))
        with col2:
            st.write('Observação:')
            st.write(row.get('observacao', ''))

    st.markdown('---')
    st.caption('Versão profissional do dashboard — filtros de criticidade, pendências e PDFs em modal.')


if __name__ == '__main__':
    main()
