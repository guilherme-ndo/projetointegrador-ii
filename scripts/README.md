# Scripts de coleta e tratamento

Rodar sempre a partir da raiz do repositório, na ordem:

```bash
pip install -r requirements.txt
python scripts/01_dim_municipio.py    # códigos IBGE (precisa de internet)
python scripts/02_censo_superior.py   # INEP: arquivos em dados_brutos/inep/
python scripts/03_caged.py            # CAGED: arquivos em dados_brutos/caged/
```

| Script | Entrada | Saída |
|---|---|---|
| `01_dim_municipio.py` | API de localidades do IBGE | `dados_tratados/dMunicipio.csv` |
| `02_censo_superior.py` | `dados_brutos/inep/*CURSOS*.CSV` | `dados_tratados/fOfertaEnsino.csv` |
| `03_caged.py` | `dados_brutos/caged/CAGEDMOV*.txt` ou `.7z` | `dados_tratados/fAdmissoes.csv` |

Municípios do recorte ficam em `utils.py` (`MUNICIPIOS_RECORTE`).
Nomes de colunas e códigos (rede, modalidade, escolaridade) devem ser conferidos no dicionário de dados de cada ano.
