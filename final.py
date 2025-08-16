# app_enterprise.py
# [compatível] Dashboard empresarial moderno para os dados "VALE - MG"

import os
from typing import Tuple
import unicodedata  # mantido

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="BI | VALE - MG - Franzen", page_icon="📊", layout="wide")

PRIMARY = "#00a86b"
ACCENT  = "#f4c247"
DARK_BG = "#0e1117"
LIGHT_BG = "#111827"
TEXT    = "#e5e7eb"

st.markdown(f"""
<style>
body, .block-container {{ color: {TEXT}; }}
[data-testid="stSidebar"] > div:first-child {{ background: {DARK_BG}; }}
.card {{ background: linear-gradient(180deg, {LIGHT_BG} 0%, {DARK_BG} 100%); border: 1px solid #1f2937; border-radius: 14px; padding: 14px 16px; }}
.kpi-number {{ font-size: 28px; font-weight: 800; line-height: 1.1; }}
.kpi-label {{ font-size: 12px; opacity: .85; }}
.badge {{ display:inline-block; padding: 4px 8px; border-radius: 999px; border:1px solid #334155; background:#0b1220; font-size: 11px; }}
.header {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
.header h1 {{ font-size: 20px; margin:0; }}
.table-small table {{ font-size: 12px; }}
a, a:visited {{ color:{ACCENT}; }}
hr {{ border: none; border-top: 1px solid #1f2937; margin: 8px 0 16px 0; }}
</style>
""", unsafe_allow_html=True)

CANDIDATE_FILES = [
    "equipamentos_filtrado.xlsx",
    "data.csv",
    "vale - MG - layout v3_processed (1).xlsm",
    "vale - MG - layout v3_processed.xlsm",
]

def _lower_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def try_load_local_data() -> Tuple[pd.DataFrame, str]:
    if os.path.exists("equipamentos_filtrado.xlsx"):
        df = pd.read_excel("equipamentos_filtrado.xlsx", engine="openpyxl")
        return _lower_cols(df), "equipamentos_filtrado.xlsx"
    if os.path.exists("data.csv"):
        df = pd.read_csv("data.csv")
        return _lower_cols(df), "data.csv"
    for nm in ["vale - MG - layout v3_processed (1).xlsm", "vale - MG - layout v3_processed.xlsm"]:
        if os.path.exists(nm):
            try:
                raw = pd.read_excel(nm, sheet_name="DATASHEET EQUIPAMENTOS", engine="openpyxl")
                raw = _lower_cols(raw)
                keep = [c for c in raw.columns if c in {"local","sistema","fabricante","modelo","r. pqs","r. liquido"}]
                df_min = raw[keep].copy()
                df_min["complexo"] = np.nan
                df_min["status"] = np.nan
                df_min.rename(columns={"r. pqs":"pqs", "r. liquido":"liquido"}, inplace=True)
                return df_min, nm
            except Exception as e:
                st.warning(f"Falha ao ler '{nm}': {e}")
    return pd.DataFrame(), ""

def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = _lower_cols(df)
    ren = {
        "tag": "tag",
        "modelo": "modelo",
        "sistema": "sistema",
        "local": "local",
        "complexo": "complexo",
        "computed_status": "status",
        "status_final": "status_final",
    }
    df = df.rename(columns={k:v for k,v in ren.items() if k in df.columns})
    if "status" not in df.columns:
        if "status_final" in df.columns:
            df["status"] = df["status_final"]
        elif "computed_status" in df.columns:
            df["status"] = df["computed_status"]
        elif "status_final_excel" in df.columns:
            df["status"] = df["status_final_excel"]
    if "nota_quantitativa" not in df.columns:
        df["nota_quantitativa"] = np.nan
    if "nota_qualitativa" not in df.columns:
        df["nota_qualitativa"] = np.nan
    for col in ["complexo","local","sistema","modelo","tag","status"]:
        if col not in df.columns:
            df[col] = np.nan
    return df

def _strip_object_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"": np.nan, "nan": np.nan, "None": np.nan})
    return df

def clean_minimal_and_dq(df: pd.DataFrame):
    original_len = len(df)
    df = _strip_object_cols(df).copy()
    if "status" in df.columns:
        df["status"] = df["status"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    dup_mask = df.duplicated(keep="first")
    removed_dups = int(dup_mask.sum())
    if removed_dups:
        df = df.loc[~dup_mask].copy()
    missing_rate = (
        df.isna().mean().rename("missing_rate").to_frame()
          .reset_index().rename(columns={"index": "col"})
          .sort_values("missing_rate", ascending=False)
    )
    dq = {
        "rows_in": int(original_len),
        "rows_out": int(len(df)),
        "exact_duplicates_removed": removed_dups,
        "cols_missing_over_20pct": missing_rate[missing_rate["missing_rate"] > 0.20]["col"].tolist(),
    }
    return df, dq

def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    st.sidebar.subheader("Filtros")
    def options(col):
        vals = sorted([v for v in df[col].dropna().unique().tolist() if str(v).strip() != ""])
        return vals
    complexo = st.sidebar.multiselect("Complexo", options("complexo"))
    local    = st.sidebar.multiselect("Local", options("local"))
    sistema  = st.sidebar.multiselect("Sistema", options("sistema"))
    status   = st.sidebar.multiselect("Status", options("status"))
    search = st.sidebar.text_input("Busca rápida (TAG/Modelo)")
    if complexo:
        df = df[df["complexo"].isin(complexo)]
    if local:
        df = df[df["local"].isin(local)]
    if sistema:
        df = df[df["sistema"].isin(sistema)]
    if status:
        df = df[df["status"].isin(status)]
    if search:
        s = search.strip().lower()
        df = df[df.apply(lambda r: s in str(r.get("tag","")).lower() or s in str(r.get("modelo","")).lower(), axis=1)]
    return df

def kpis(df: pd.DataFrame):
    total = len(df)
    conformes = int((df["status"].astype(str).str.upper() == "CONFORME").sum()) if "status" in df.columns else 0
    nao_conf = int((df["status"].astype(str).str.upper().str.contains("NAO") | df["status"].astype(str).str.upper().str.contains("NÃO")).sum()) if "status" in df.columns else 0
    pct_conf = (conformes / total * 100) if total else 0.0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="card"><div class="kpi-number">{}</div><div class="kpi-label">Equipamentos</div></div>'.format(total), unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="kpi-number">{:.1f}%</div><div class="kpi-label">% Conformidade</div></div>'.format(pct_conf), unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><div class="kpi-number">{}</div><div class="kpi-label">Conformes</div></div>'.format(conformes), unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="card"><div class="kpi-number">{}</div><div class="kpi-label">Não conformes</div></div>'.format(nao_conf), unsafe_allow_html=True)

def charts(df: pd.DataFrame):
    st.markdown("### Visão geral")
    if "complexo" in df.columns and "status" in df.columns:
        agg = (
            df.assign(status=lambda d: d["status"].fillna("Sem status"))
              .groupby(["complexo","status"], dropna=False).size()
              .reset_index(name="qtd")
        )
        chart = alt.Chart(agg).mark_bar().encode(
            x=alt.X("qtd:Q", title="Equipamentos"),
            y=alt.Y("complexo:N", sort="-x", title="Complexo"),
            color=alt.Color("status:N", legend=alt.Legend(title="Status")),
            tooltip=["complexo","status","qtd"]
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    if "modelo" in df.columns and "status" in df.columns:
        nc = df[df["status"].astype(str).str.upper().str.contains("NAO|NÃO", na=False)]
        if not nc.empty:
            top = (
                nc.groupby("modelo", dropna=False).size().reset_index(name="qtd")
                  .sort_values("qtd", ascending=False).head(15)
            )
            chart2 = alt.Chart(top).mark_bar().encode(
                x=alt.X("qtd:Q", title="Não conformes"),
                y=alt.Y("modelo:N", sort="-x", title="Modelo"),
                tooltip=["modelo","qtd"]
            ).properties(height=350)
            st.altair_chart(chart2, use_container_width=True)

def data_table(df: pd.DataFrame):
    st.markdown("### Detalhamento")
    cols_pref = [c for c in ["complexo","local","sistema","modelo","tag","status","nota_quantitativa","nota_qualitativa","report_id","report_url"] if c in df.columns]
    show = df[cols_pref] if cols_pref else df
    st.dataframe(show, use_container_width=True, hide_index=True)
    csv = show.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV (filtrado)", csv, "dados_filtrados.csv", "text/csv")

def header(logo_path: str = "download.png"):
    left, mid, right = st.columns([0.14, 0.56, 0.30])
    with left:
        if os.path.exists(logo_path):
            st.image(logo_path, use_column_width=True)
        else:
            st.markdown(f'<span class="badge">LOGO</span>', unsafe_allow_html=True)
    with mid:
        st.markdown(f'<div class="header"><h1>Dashboard | VALE - MG</h1><span class="badge">layout empresarial</span></div>', unsafe_allow_html=True)
        st.caption("Análise de conformidade por complexo, local, sistema e modelo.")
    with right:
        st.markdown('<div class="card"><div class="kpi-label">Fonte</div><div class="kpi-number">Planilha / CSV</div></div>', unsafe_allow_html=True)

header()

with st.sidebar:
    st.markdown("### 📁 Fonte de dados")
    uploaded = st.file_uploader("Carregar novo arquivo (.xlsx, .csv, .xlsm)", type=["xlsx","csv","xlsm"])
    source_note = ""

if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df0 = pd.read_csv(uploaded)
            source_note = f"upload: {uploaded.name}"
        elif uploaded.name.lower().endswith((".xlsx",".xlsm")):
            try:
                xls = pd.ExcelFile(uploaded, engine="openpyxl")
                sheet = None
                for cand in xls.sheet_names:
                    nm = cand.strip().lower()
                    if "equip" in nm or "datasheet" in nm:
                        sheet = cand
                        break
                if sheet is None and xls.sheet_names:
                    sheet = xls.sheet_names[0]
                df0 = pd.read_excel(xls, sheet_name=sheet)
                source_note = f"upload: {uploaded.name} (aba: {sheet})"
            except Exception as e:
                st.error(f"Falha ao ler Excel enviado: {e}")
                df0 = pd.DataFrame()
        else:
            df0 = pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao processar upload: {e}")
        df0 = pd.DataFrame()
else:
    df0, source_note = try_load_local_data()

df = normalize_schema(df0)
df, dq = clean_minimal_and_dq(df)

if source_note:
    st.caption(f"📦 Dados carregados de: **{source_note}**")

df_filtered = filter_df(df)
kpis(df_filtered)
charts(df_filtered)
st.markdown("---")
data_table(df_filtered)
st.markdown("—")
st.caption("v1 • Assistente de Programação – Streamlit + Altair • layout empresarial moderno")
