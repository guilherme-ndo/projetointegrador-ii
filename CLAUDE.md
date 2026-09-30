# Projeto Integrador II: Formação superior e mercado de trabalho na Sub-região Oeste da RMSP

Curso de Ciência de Dados, Fatec Santana de Parnaíba, 2026.
Autores: Guilherme Neves Dantas de Oliveira e Luiz Rodolfo Dawoglio.
Orientador: Prof. Me. Antonio Manuel Marques Matias.

## Contexto
Este trabalho continua o PI1 ("Políticas Públicas e a Inclusão no Ensino Superior"). O PI1 concluiu que o gargalo do ensino superior brasileiro migrou do acesso para a permanência. Também mostrou que o diploma reduz o desemprego (3,9% no nível superior contra 8,8% no nível médio, dados de 2023 do Banco Mundial). As considerações finais recomendaram estratégias de transição estudo-trabalho (ODS 8).

O PI2 leva essa análise para a escala regional. A pergunta central é: os cursos superiores oferecidos na região formam para as vagas que o mercado local abre?

## Exigências da disciplina
- Cruzar três bases de dados.
- Dar um retorno à sociedade, conforme orientação do MEC. O produto previsto é um guia "Cursos com mercado na nossa região", entregue às escolas estaduais (Diretoria de Ensino) e à coordenação da Fatec.
- O relatório pode ser relato técnico ou artigo científico, a confirmar com o professor Venerson.
- Pendente: validar com o professor se a proposta só com dados públicos, sem visita de campo, é aceita.

## Recorte
- Municípios: Santana de Parnaíba, Barueri, Osasco, Carapicuíba, Cajamar, Itapevi, Jandira e Pirapora do Bom Jesus. A lista fica em `scripts/utils.py`.
- Período: de 2020 até o último ano disponível. O Novo CAGED começa em jan/2020.

## Bases
- INEP, Censo da Educação Superior (arquivo de cursos): chave `CO_MUNICIPIO` com 7 dígitos e área `CO_CINE_AREA_GERAL` com 2 dígitos.
- MTE, Novo CAGED e RAIS (portal PDET): o município tem 6 dígitos e a ocupação vem em CBO 2002 com 6 dígitos.
- IBGE, Censo 2022 (SIDRA): município com 7 dígitos.
- INEP: `CO_MUNICIPIO` é o município do local de oferta; cursos EaD aparecem por município do polo (conferido em 2024: só 473 concluintes EaD no Brasil sem município). EaD é cerca de 2/3 dos concluintes da região em 2024.
- CAGED: exclusões (EXC) entram com `peso = -1`; admissões = `SUM(peso)`. Nível superior = graus 9, 10, 11 e 80; `unidadesalariocodigo = 5` é mensal; `indtrabintermitente = 1` é intermitente (conferido no layout do PDET).
- Dicionários ficam em `dados_brutos/inep/dicionario_educacao_superior_2024.xlsx` e `dados_brutos/caged/layout_novo_caged_movimentacao.xlsx`.

## Perguntas de pesquisa
1. Quais áreas formam mais concluintes na região?
2. Quais ocupações de nível superior mais contratam?
3. Onde há descompasso entre formados e vagas? (núcleo do projeto)
4. Quanto o diploma aumenta o salário de admissão localmente?
5. A oferta é pública ou privada, e qual a taxa de conclusão?

## Métricas principais
- Índice de descompasso: admissões com nível superior na área ÷ concluintes na área.
- Prêmio salarial: salário de admissão com nível superior ÷ salário de admissão com nível médio.
- Taxa de conclusão local: concluintes ÷ ingressantes, com defasagem pela duração do curso.
- Participação privada: matrículas na rede privada ÷ total de matrículas.
- Sobrequalificação: admissões com superior em ocupações dos grandes grupos 4 a 9 da CBO ÷ total de admissões com superior.
- O índice de descompasso fica acima de 1 em todas as áreas (admissões incluem rotatividade e formados de fora), então a leitura é comparativa entre áreas.
- Prêmio salarial usa mediana e só linhas com `salario_comparavel = True`.

## Modelo de dados (Power BI, esquema estrela)
- Dimensões: dMunicipio (códigos de 7 e 6 dígitos), dCalendario, dArea (CINE), dCBO (de-para), dEscolaridade.
- Fatos: fOfertaEnsino (INEP), fAdmissoes (CAGED), fEstoqueEmprego (RAIS), fPopulacao (IBGE).

## Tabela de-para CINE x CBO
Fica em `docs/depara_cine_cbo.xlsx`. Validada em 30/09/2026 com CAGED 2024 e INEP 2024: 79 linhas, nenhuma "Verificar", coluna `fonte` com a evidência. A área de cada ocupação foi decidida pelo nome do curso no INEP (ex.: Logística em 04, Educação Física bacharelado em 09). A busca em cascata (4, 3, 2 e 1 dígitos) roda no script 04, que gera `dados_tratados/dCBO.csv` com todas as ocupações e a coluna `categoria_ocupacao` (pelo grande grupo da CBO). Ocupações de nível médio (grupos 4 a 9) ficam sem área de propósito. Cobertura: 99% das admissões de formados em cargos de nível superior, técnico ou dirigente. Cada ocupação tem uma área principal, e essa simplificação deve aparecer como limitação no relatório. `docs/cobertura_depara.csv` lista as CBOs por admissões de formados.

## Estrutura do repositório
- `dados_brutos/`: downloads originais, não versionados.
- `dados_tratados/`: CSVs filtrados.
- `scripts/`: 01_dim_municipio, 02_censo_superior, 03_caged, 04_dim_cbo e utils.
- `docs/apresentacao_pi2.pptx`: apresentação no modelo da III Mostra Acadêmica (`docs/Apresentacao-Trabalho-Conclusao-de-Curso-Minimalista-Preto-e-Branco.pptx`), preto e branco, fontes do modelo; seções: capa, introdução, justificativa, objetivos, revisão teórica, metodologia (coleta, organização, análise), resultados, conclusão, próximos passos e referências. Atualizar a cada avanço. Fontes: só Montaser Arabic e Montaser Arabic Light. Referências no formato ABNT do PI1.
- `powerbi/`, `docs/`, `relatorio/`.
- `dados pi/`: relato técnico do PI1 (docx, pdf, pptx), fonte das referências e números herdados.

## Próximos passos
- Feito: scripts 01 a 04 rodados com INEP 2024 e CAGED jan-dez/2024; de-para validado; primeiros resultados na apresentação (slides 9 e 10).
- Baixar INEP e CAGED de 2020 a 2023 e repetir (tendência do índice).
- Script 05 para a RAIS e script 06 para o IBGE.
- Primeiro fazer um fluxo completo no Power BI com uma área, um ano e um município, depois escalar.

## Convenções
- Código e comentários em português.
- Scripts rodam a partir da raiz do repositório.
- Arquivos maiores que 100 MB não vão para o GitHub.
