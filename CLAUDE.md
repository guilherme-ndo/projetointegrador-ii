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
- `powerbi/`: projeto PBIP do painel e gerador.
- `scripts/`: 01_dim_municipio, 02_censo_superior, 03_caged, 04_dim_cbo, 05_rais, 06_ibge, 07_detalhe, indicadores e utils (utils guarda também NIVEL_INSTRUCAO, comum a CAGED e RAIS).
- `dados_tratados/indicadores_ano.csv` e `indicadores_area_ano.csv`: indicadores calculados em Python, para conferir as medidas DAX.
- `docs/apresentacao_pi2.pptx`: apresentação no modelo da III Mostra Acadêmica (`docs/Apresentacao-Trabalho-Conclusao-de-Curso-Minimalista-Preto-e-Branco.pptx`), preto e branco, fontes do modelo; seções: capa, introdução, justificativa, objetivos, revisão teórica, metodologia (coleta, organização, análise), resultados, conclusão, próximos passos e referências. Atualizar a cada avanço. Fontes: só Montaser Arabic e Montaser Arabic Light. Referências no formato ABNT do PI1.
- `powerbi/`, `docs/`, `relatorio/`.
- `dados pi/`: relato técnico do PI1 (docx, pdf, pptx), fonte das referências e números herdados.

## Próximos passos
- Feito: scripts 01 a 04 e indicadores rodados com INEP 2020-2024 e CAGED jan/2020-dez/2024 (60 meses); de-para validado; apresentação com resultados de 2024 e evolução 2020-2024.
- Achados 2020-2024: índice de Computação/TIC caiu de 11,5 (2021) para 4,7 (concluintes da área 907 para 2.316); prêmio salarial caiu de 2,7x (2021) para 2,1x; sobrequalificação subiu de 30% para 34% (pico de 37% em 2023); EaD passou de 39% para 67% dos concluintes. 2020 tem admissões baixas (pandemia).
- `fAdmissoes.csv` com 5 anos tem cerca de 430 MB; o script 03 converte tipos mês a mês para caber na memória.
- Feito: RAIS 2020-2024 (script 05), vínculos ativos em 31/12, agregados por ano, município, CBO e grau. Achados: formados são 34% do estoque em 2024 (25% em 2020); sobrequalificação no estoque 16% (contra 34% nas admissões); prêmio salarial no estoque 2,6x (2,1x na admissão). Limitação: RAIS 2022 parece subdeclarada (formados +37% de 2022 para 2023, contra 10-14% nos outros anos), provável transição para o eSocial.
- Feito: painel Power BI em formato PBIP (`powerbi/`), gerado por `powerbi/gerar_pbip.py` (modelo TMDL + relatório PBIR, 5 páginas). Medidas DAX conferidas contra `indicadores.py`. Detalhes em `powerbi/README.md`. Se editar o painel no Desktop, não rodar o gerador de novo (sobrescreve).
- Teste do painel sem clicar na tela: abrir o .pbip, atualizar e consultar DAX pela instância local do Analysis Services do Power BI Desktop (porta em `%USERPROFILE%/Microsoft/Power BI Desktop Store App/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt`, DLL `Microsoft.PowerBI.AdomdClient.dll`).
- Feito: IBGE Censo 2022 (script 06, API do SIDRA; tabelas 9514, 10059, 10061 e 10064). A 10064 traz moradores formados por área CINE (mesmos códigos do INEP; tem também a área 11, não sabe ou mal especificada). Achados: 21% dos moradores de 25+ têm superior (10% Itapevi a 33% Santana de Parnaíba); 15% dos jovens de 18-24 cursam graduação; Computação e TIC é a única área com menos moradores formados (21,7 mil) que vínculos de formados na área (30,3 mil, RAIS 2022).
- As três bases exigidas estão integradas (INEP, MTE e IBGE).
- Feito: detalhamento por município e curso (script 07). Fatecs da região: Osasco (CO_IES 15709), Barueri (15757), Carapicuíba (16395), Santana de Parnaíba (20478) e polos EaD da Fatec São Paulo (34); identificadas pela mantenedora Paula Souza. Ligação curso -> ocupações em `docs/curso_ocupacao_fatec.csv` (proposta minha, a validar com as Fatecs); resumo em `docs/cursos_fatec.md`. A concorrência entre cursos fica no nível da área CINE (índice), porque os campos detalhados da CINE não acompanham as ocupações. Achados: Barueri faz 64% das admissões de formados e 16% dos concluintes; Osasco forma 47% e contrata 20% (mercado é regional); ocupações de TI contratam ~8 mil formados/ano com salário mediano ~R$ 9 mil, mas caíram ~15% desde 2021 enquanto concluintes de TI dobraram.
- Próximos: publicar o painel, validar com o professor e as Fatecs, guia para as escolas e relatório.
- Primeiro fazer um fluxo completo no Power BI com uma área, um ano e um município, depois escalar.

## Convenções
- Código e comentários em português.
- Scripts rodam a partir da raiz do repositório.
- Arquivos maiores que 100 MB não vão para o GitHub. O CAGED completo (`fAdmissoes.csv`, 430 MB) fica local; análises e Power BI leem `fAdmissoes.parquet` (só admissões, 11 MB, versionado), para o repositório funcionar em qualquer máquina (ex.: laptop para apresentar).
