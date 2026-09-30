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
python scripts/05_rais.py             # RAIS: dados_brutos/rais/RAIS_VINC_PUB_SP_<ano>.7z
python scripts/06_ibge.py             # IBGE: Censo 2022 pela API do SIDRA (precisa de internet)
python scripts/indicadores.py         # indicadores por ano, área e município (conferência do Power BI)
python scripts/07_detalhe.py          # detalhe por município e curso (Fatec); roda depois de indicadores
```

| Script | Entrada | Saída |
|---|---|---|
| `01_dim_municipio.py` | API de localidades do IBGE | `dados_tratados/dMunicipio.csv` |
| `02_censo_superior.py` | `dados_brutos/inep/*CURSOS*.CSV` | `dados_tratados/fOfertaEnsino.csv` |
| `03_caged.py` | `dados_brutos/caged/CAGEDMOV*.txt` ou `.7z` | `dados_tratados/fAdmissoes.csv` (completo) e `fAdmissoes.parquet` (só admissões) |
| `04_dim_cbo.py` | `docs/depara_cine_cbo.xlsx` e layout do CAGED | `dados_tratados/dCBO.csv`, `docs/cobertura_depara.csv` |
| `05_rais.py` | `dados_brutos/rais/RAIS_VINC_PUB_SP_<ano>.7z` | `dados_tratados/fEstoqueEmprego.csv`, `dados_tratados/rais_mediana_ano.csv` |
| `06_ibge.py` | API do SIDRA (tabelas 9514, 10059, 10061, 10064) | `dados_tratados/fPopulacao.csv`, `fFormadosResidentes.csv`, `fFrequenciaEscolar.csv` |
| `07_detalhe.py` | saídas anteriores + `docs/curso_ocupacao_fatec.csv` | `dados_tratados/detalhe_*.csv`, `docs/cursos_fatec.md` |
| `indicadores.py` | saídas de 02, 03 e 04 | `dados_tratados/indicadores_ano.csv`, `dados_tratados/indicadores_area_ano.csv` |

Municípios do recorte e ano inicial ficam em `utils.py` (`MUNICIPIOS_RECORTE`, `ANO_INICIAL`).

No CAGED, `python scripts/03_caged.py --tipos MOV FOR EXC` monta a série completa. As exclusões entram com `peso = -1`, então no Power BI as admissões são `SUM(peso)`, não `COUNTROWS`. Para o prêmio salarial, use só as linhas com `salario_comparavel = True` (salário mensal, sem intermitente).

`fAdmissoes.csv` fica fora do Git (cerca de 430 MB). As análises e o Power BI leem `fAdmissoes.parquet` (só admissões, cerca de 11 MB), que vai para o Git; assim o repositório funciona sem rodar o script 03. A RAIS sai agregada (`fEstoqueEmprego.csv`, cerca de 7 MB) e vai para o Git.

A RAIS muda de formato entre anos: até 2022 usa `;` e decimal `,`; de 2023 em diante usa `,` e decimal `.`, com cabeçalhos terminados em " - Código". O script 05 detecta os dois.
Nomes de colunas e códigos (rede, modalidade, escolaridade) devem ser conferidos no dicionário de dados de cada ano.
