
# Dashboard de Equipamentos — Grupo Franzen

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```
- Notas permitidas: 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5 (via `select_slider`).
- Filtros na barra lateral: Complexo, Local, Sistema, Modelo e busca por TAG.
- **Relatório em Modal**: na página **Lançar Notas**, botão "Exibir relatório em modal" abre o PDF (Google Drive) com scroll e campos de nota/observação ao lado.
- Campo adicional **Obs internas Franzen** adicionado e persistido em `data.csv`.
- Nova aba **Gráficos & Exportar** com gráficos Altair e **download** de dados filtrados em CSV/Excel.

> Observação: para cada linha, `data.csv` deve conter a coluna `report_id` (ID do arquivo no Google Drive). A URL de preview é montada automaticamente.
