# Scripts de coleta e tratamento

Rodar sempre a partir da raiz do repositório, na ordem:

```bash
python -m venv .venv                  # uma vez só
.venv\Scripts\activate                # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python scripts/01_dim_municipio.py    # códigos IBGE (precisa de internet)
python scripts/02_censo_superior.py   # INEP: arquivos em dados_brutos/inep/
python scripts/03_caged.py            # CAGED: arquivos em dados_brutos/caged/
python scripts/04_dim_cbo.py          # dCBO: cascata do de-para em todas as ocupações
```

| Script | Entrada | Saída |
|---|---|---|
| `01_dim_municipio.py` | API de localidades do IBGE | `dados_tratados/dMunicipio.csv` |
| `02_censo_superior.py` | `dados_brutos/inep/*CURSOS*.CSV` | `dados_tratados/fOfertaEnsino.csv` |
| `03_caged.py` | `dados_brutos/caged/CAGEDMOV*.txt` ou `.7z` | `dados_tratados/fAdmissoes.csv` |
| `04_dim_cbo.py` | `docs/depara_cine_cbo.xlsx` e layout do CAGED | `dados_tratados/dCBO.csv`, `docs/cobertura_depara.csv` |

Municípios do recorte e ano inicial ficam em `utils.py` (`MUNICIPIOS_RECORTE`, `ANO_INICIAL`).

No CAGED, `python scripts/03_caged.py --tipos MOV FOR EXC` monta a série completa. As exclusões entram com `peso = -1`, então no Power BI as admissões são `SUM(peso)`, não `COUNTROWS`. Para o prêmio salarial, use só as linhas com `salario_comparavel = True` (salário mensal, sem intermitente).

`fAdmissoes.csv` e `fEstoqueEmprego.csv` ficam fora do Git (passam de 100 MB). Cada integrante gera localmente.
Nomes de colunas e códigos (rede, modalidade, escolaridade) devem ser conferidos no dicionário de dados de cada ano.
