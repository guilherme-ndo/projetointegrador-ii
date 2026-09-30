# Painel Power BI

O painel fica em formato de projeto do Power BI (PBIP): modelo em TMDL e relatório em PBIR, tudo em texto versionado no Git.

## Como abrir

1. Rode os scripts de `scripts/` (01 a 06) para gerar os CSVs de `dados_tratados/`. O `fAdmissoes.csv` não vai para o Git; cada integrante gera o seu.
2. Rode `python powerbi/gerar_pbip.py`. Ele recria o projeto com o caminho de `dados_tratados/` desta máquina no parâmetro `PastaDados`.
3. Abra `powerbi/PI2.pbip` no Power BI Desktop e clique em **Atualizar**. A carga leva cerca de 2 minutos (o CAGED tem 5 milhões de linhas).

Se preferir não rodar o gerador, abra o projeto e mude o parâmetro em **Transformar dados > Gerenciar parâmetros > PastaDados** (o caminho precisa terminar com `\`).

## Modelo (esquema estrela)

| Tabela | Origem | Papel |
|---|---|---|
| dCalendario | gerada (2020 a 2024) | ano |
| dMunicipio | `dMunicipio.csv` | liga código de 7 dígitos (INEP) e de 6 (CAGED e RAIS) |
| dArea | `dArea.csv` | áreas CINE |
| dCBO | `dCBO.csv` | ocupação, área (de-para) e categoria; filtra por área as admissões e o estoque |
| dEscolaridade | gerada | nível de instrução |
| fOfertaEnsino | `fOfertaEnsino.csv` | INEP: cursos, ingressantes, matrículas, concluintes |
| fAdmissoes | `fAdmissoes.csv` | CAGED: movimentações (admissões = soma de `peso`) |
| fEstoqueEmprego | `fEstoqueEmprego.csv` | RAIS: vínculos ativos em 31/12 |
| fPopulacao | `fPopulacao.csv` | IBGE 2022: população por idade e nível de instrução |
| fFormadosResidentes | `fFormadosResidentes.csv` | IBGE 2022: moradores com superior por área CINE |
| fFrequenciaEscolar | `fFrequenciaEscolar.csv` | IBGE 2022: quem frequentava escola, por nível |
| _Medidas | | todas as medidas DAX, em pastas por tema |

As medidas foram conferidas contra `scripts/indicadores.py` (mesmos valores por ano e por área). Diferenças de propósito:
- **Índice de descompasso** fica em branco quando a área tem menos de 50 concluintes no recorte filtrado (amostra pequena).
- **Estoque (RAIS)** usa o último ano do filtro, porque somar estoques de anos diferentes não faz sentido.
- **Prêmio salarial no estoque** usa média (a RAIS está agregada e não permite mediana); o `indicadores.py` usa mediana, então os valores diferem (cerca de 3,0 contra 2,6).

## Páginas

Visão geral, Descompasso, Salários, Oferta de cursos, Emprego (RAIS) e População (IBGE). Todas têm filtro de município; só a do IBGE não tem filtro de ano (o Censo é de 2022).

## Editar

Pode editar direto no Power BI Desktop e salvar (o PBIP continua em texto). Se rodar `gerar_pbip.py` de novo, ele sobrescreve o modelo e o relatório: mudanças feitas à mão no Desktop se perdem. Depois que o painel estiver estável, a ideia é editar só pelo Desktop.
