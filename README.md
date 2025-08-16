# Layout - Dashboard de Equipamentos

Esta pasta contém dois dashboards Streamlit para visualização e qualificação de equipamentos.

Arquivos principais:
- `app.py` - Versão original do dashboard.
- `pro_app.py` - Versão profissional aprimorada (recomendada).
- `data.csv` - Dados usados pelo dashboard (deve existir no diretório).
- `download.png` - Logo usado no header.

Requisitos

Instale dependências:

```bash
pip install -r requirements.txt
```

Como rodar

Versão profissional (recomendada):

```bash
streamlit run pro_app.py
```

Versão original:

```bash
streamlit run app.py
```

Notas

- Certifique-se de que `data.csv` contenha as colunas esperadas (TAG, complexo, Local, PQS_Rec_Total, PQS_Inst_Total, Liq_Rec_Total, Liq_Inst_Total, Computed_Status, layout_sensores_cabo, layout_bicos_mangueiras, layout_painel_cabine, nota_quantitativa, nota_qualitativa, status_final, report_id, observacao).
- O `pro_app.py` implementa:
  - Filtros avançados na sidebar (busca rápida, complexo, sistema, criticidade, pendentes).
  - KPIs no topo (Conforme / Não Conforme / Pendentes / Total).
  - Abas: Tabela completa, Pendentes, Críticos, Relatórios (PDF em modal com preview do Google Drive).
  - Painel de detalhe rápido por TAG.

Se quiser que eu gere uma versão com deploy e estilos CSS adicionais, me diga qual visual prefere (corporativo, material, flat, etc.).
