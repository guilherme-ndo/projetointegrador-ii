# Painel Power BI

O painel fica em formato de projeto do Power BI (PBIP): modelo em TMDL e relatório em PBIR, tudo em texto versionado no Git.

## Como abrir em outro computador (ex.: laptop)

Todos os dados que o painel usa estão no GitHub (as admissões do CAGED vão em `fAdmissoes.parquet`, com 11 MB). Não precisa rodar nenhum script.

1. Baixe o repositório: `git clone https://github.com/guilherme-ndo/projetointegrador-ii.git` ou, no GitHub, **Code > Download ZIP** (e descompacte).
2. Abra `powerbi/PI2.pbip` no Power BI Desktop (só existe para Windows).
3. Em **Página Inicial > Transformar dados > Editar parâmetros**, troque `PastaDados` pelo caminho da pasta `dados_tratados` do laptop, terminando com `\` (ex.: `C:\Users\voce\projetointegrador-ii\dados_tratados\`).
4. Clique em **Aplicar alterações** (ou **Atualizar**). A carga leva cerca de 1 minuto.
5. Salve (Ctrl+S). O Power BI guarda uma cópia dos dados em `.pbi/cache.abf`; nas próximas vezes o painel abre já com dados, sem precisar atualizar.

Se o computador tiver Python, o passo 3 pode ser trocado por `python powerbi/gerar_pbip.py`, que grava o caminho certo sozinho (mas sobrescreve mudanças feitas à mão no Desktop).

Plano B para apresentar: exporte o painel em PDF (**Arquivo > Exportar > Exportar para PDF**) e leve o arquivo.

## Modelo (esquema estrela)

| Tabela | Origem | Papel |
|---|---|---|
| dCalendario | gerada (2020 a 2024) | ano |
| dMunicipio | `dMunicipio.csv` | liga código de 7 dígitos (INEP) e de 6 (CAGED e RAIS) |
| dArea | `dArea.csv` | áreas CINE |
| dCBO | `dCBO.csv` | ocupação, área (de-para) e categoria; filtra por área as admissões e o estoque |
| dEscolaridade | gerada | nível de instrução |
| fOfertaEnsino | `fOfertaEnsino.csv` | INEP: cursos, ingressantes, matrículas, concluintes |
| fAdmissoes | `fAdmissoes.parquet` | CAGED: admissões (soma de `peso`; exclusões entram com -1) |
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

Visão geral, Descompasso, Salários, Oferta de cursos, Emprego (RAIS), Municípios, Cursos (com filtro É Fatec) e População (IBGE). Todas têm filtro de município; só a do IBGE não tem filtro de ano (o Censo é de 2022).

## Editar

Pode editar direto no Power BI Desktop e salvar (o PBIP continua em texto). Se rodar `gerar_pbip.py` de novo, ele sobrescreve o modelo e o relatório: mudanças feitas à mão no Desktop se perdem. Depois que o painel estiver estável, a ideia é editar só pelo Desktop.
