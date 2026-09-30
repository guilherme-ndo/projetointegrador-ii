"""
Gera o projeto Power BI (formato PBIP: modelo em TMDL e relatório em PBIR).

Cria em powerbi/:
  PI2.pbip                abrir este arquivo no Power BI Desktop
  PI2.SemanticModel/      modelo estrela: tabelas, relacionamentos e medidas DAX
  PI2.Report/             páginas e visuais do painel

Os dados vêm dos CSVs de dados_tratados/. O caminho da pasta fica no
parâmetro PastaDados (Transformar dados > Parâmetros), preenchido com o
caminho desta máquina quando o script roda.

Uso: python powerbi/gerar_pbip.py
Depois: abrir powerbi/PI2.pbip e clicar em Atualizar.
"""
import json
import shutil
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "powerbi"
MODELO = SAIDA / "PI2.SemanticModel"
RELATORIO = SAIDA / "PI2.Report"
PASTA_DADOS = str(RAIZ / "dados_tratados") + "\\"
ANOS = (2020, 2024)

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
T = "\t"


def guid(semente):
    """GUID estável, para o diff do Git não mudar a cada geração."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "pi2/" + semente))


def nome_tmdl(nome):
    return f"'{nome}'" if any(c in nome for c in " .=:'()") or not nome.isascii() else nome


# --------------------------------------------------------------------------
# Modelo semântico (TMDL)
# --------------------------------------------------------------------------

def texto_m(valor):
    return '"' + valor.replace('"', '""') + '"'


def csv_m(arquivo, tipos, colunas=None, renomear=None):
    """Partição M que lê um CSV de dados_tratados com tipos em cultura en-US."""
    passos = [
        f"Fonte = Csv.Document(File.Contents(PastaDados & {texto_m(arquivo)}), "
        "[Delimiter=\",\", Encoding=65001, QuoteStyle=QuoteStyle.Csv])",
        "Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true])",
    ]
    anterior = "Cabecalho"
    if colunas:
        passos.append(f"Colunas = Table.SelectColumns(Cabecalho, {{{', '.join(texto_m(c) for c in colunas)}}})")
        anterior = "Colunas"
    lista = ", ".join(f"{{{texto_m(c)}, {t}}}" for c, t in tipos)
    passos.append(f'Tipos = Table.TransformColumnTypes({anterior}, {{{lista}}}, "en-US")')
    anterior = "Tipos"
    if renomear:
        pares = ", ".join(f"{{{texto_m(a)}, {texto_m(b)}}}" for a, b in renomear.items())
        passos.append(f"Nomes = Table.RenameColumns(Tipos, {{{pares}}})")
        anterior = "Nomes"
    return "let\n" + ",\n".join("    " + p for p in passos) + f"\nin\n    {anterior}"


# Nome da coluna no CSV -> nome exibido no Power BI
RENOMEAR = {
    "dMunicipio": {"nome": "Município"},
    "dArea": {"area_nome": "Área", "area_curta": "Área (curta)"},
    "fOfertaEnsino": {"NO_CURSO": "Curso", "NO_CINE_ROTULO": "Rótulo CINE", "rede": "Rede",
                      "modalidade": "Modalidade"},
    "dCBO": {"cbo_descricao": "Ocupação", "categoria_ocupacao": "Categoria da ocupação",
             "tipo_vinculo": "Vínculo com a área"},
}

M_TIPO = {"text": "type text", "int64": "Int64.Type", "double": "type number", "boolean": "type logical"}
TIPO_TMDL = {"text": "string", "int64": "int64", "double": "double", "boolean": "boolean"}

# tabela: (arquivo ou M literal, [(coluna, tipo, oculta)], colunas a selecionar)
TABELAS = {
    "dMunicipio": ("dMunicipio.csv", [("cod_ibge_7", "int64", False), ("cod_ibge_6", "int64", False),
                                      ("nome", "text", False), ("uf", "text", True)], None),
    "dArea": ("dArea.csv", [("area_codigo", "text", False), ("area_nome", "text", False),
                            ("area_curta", "text", False)], None),
    "dCBO": ("dCBO.csv", [("cbo_codigo", "text", False), ("cbo_descricao", "text", False),
                          ("categoria_ocupacao", "text", False), ("chave_depara", "text", True),
                          ("area_codigo", "text", True), ("area_nome", "text", True),
                          ("tipo_vinculo", "text", False), ("confianca", "text", True)], None),
    "fOfertaEnsino": ("fOfertaEnsino.csv", [
        ("NU_ANO_CENSO", "int64", True), ("CO_MUNICIPIO", "int64", True), ("CO_IES", "int64", True),
        ("NO_CURSO", "text", False), ("CO_CURSO", "int64", True), ("NO_CINE_ROTULO", "text", False),
        ("CO_CINE_AREA_GERAL", "text", True), ("TP_GRAU_ACADEMICO", "int64", True),
        ("QT_VG_TOTAL", "int64", True), ("QT_ING", "int64", True), ("QT_MAT", "int64", True),
        ("QT_CONC", "int64", True), ("rede", "text", False), ("modalidade", "text", False)], "sel"),
    "fAdmissoes": ("fAdmissoes.csv", [
        ("ano", "int64", True), ("mes", "int64", False), ("municipio", "int64", True),
        ("cbo2002ocupacao", "text", True), ("nivel_instrucao", "text", True), ("movimento", "text", False),
        ("peso", "int64", True), ("salario", "double", True), ("salario_comparavel", "boolean", True),
        ("idade", "int64", True), ("sexo", "int64", True), ("secao", "text", False)], "sel"),
    "fEstoqueEmprego": ("fEstoqueEmprego.csv", [
        ("ano", "int64", True), ("municipio", "int64", True), ("cbo2002ocupacao", "text", True),
        ("nivel_instrucao", "text", True), ("vinculos", "int64", True), ("rem_validos", "int64", True),
        ("rem_soma", "double", True)], None),
}

M_CALENDARIO = (
    "let\n"
    f"    Anos = {{{ANOS[0]}..{ANOS[1]}}},\n"
    '    Tabela = Table.FromList(Anos, Splitter.SplitByNothing(), type table [Ano = Int64.Type])\n'
    "in\n"
    "    Tabela"
)
M_ESCOLARIDADE = (
    "let\n"
    "    Tabela = #table(type table [nivel_instrucao = text, ordem = Int64.Type], {\n"
    '        {"Abaixo do médio", 1}, {"Médio completo", 2}, {"Superior incompleto", 3},\n'
    '        {"Superior completo ou mais", 4}, {"Não identificado", 5}})\n'
    "in\n"
    "    Tabela"
)
M_MEDIDAS = "let\n    Tabela = #table(type table [Coluna = text], {})\nin\n    Tabela"

SUP, MED = '"Superior completo ou mais"', '"Médio completo"'
NIVEL_MEDIO_OP = '"Nível médio ou operacional"'
PCT, NUM, IDX, BRL = "0.0%", "#,0", "0.00", "R$ #,0"

# (pasta de exibição, nome, DAX, formato)
MEDIDAS = [
    ("Oferta", "Concluintes", "SUM ( fOfertaEnsino[QT_CONC] )", NUM),
    ("Oferta", "Ingressantes", "SUM ( fOfertaEnsino[QT_ING] )", NUM),
    ("Oferta", "Matrículas", "SUM ( fOfertaEnsino[QT_MAT] )", NUM),
    ("Oferta", "Vagas", "SUM ( fOfertaEnsino[QT_VG_TOTAL] )", NUM),
    ("Oferta", "Participação privada",
     'DIVIDE ( CALCULATE ( [Matrículas], fOfertaEnsino[Rede] = "Privada" ), [Matrículas] )', PCT),
    ("Oferta", "Participação EaD nos concluintes",
     'DIVIDE ( CALCULATE ( [Concluintes], fOfertaEnsino[Modalidade] = "EaD" ), [Concluintes] )', PCT),
    ("Oferta", "Taxa de conclusão (defasagem 3 anos)",
     ["VAR AnoAtual = SELECTEDVALUE ( dCalendario[Ano] )",
      "VAR IngressantesAntes = CALCULATE ( [Ingressantes], dCalendario[Ano] = AnoAtual - 3 )",
      "RETURN DIVIDE ( [Concluintes], IngressantesAntes )"], PCT),
    ("Admissões", "Admissões", 'CALCULATE ( SUM ( fAdmissoes[peso] ), fAdmissoes[movimento] = "Admissão" )', NUM),
    ("Admissões", "Admissões com superior",
     f"CALCULATE ( [Admissões], fAdmissoes[nivel_instrucao] = {SUP} )", NUM),
    ("Admissões", "Admissões com superior na área",
     'CALCULATE ( [Admissões com superior], dCBO[Vínculo com a área] = "Principal" )', NUM),
    ("Admissões", "Participação de formados nas admissões",
     "DIVIDE ( [Admissões com superior], [Admissões] )", PCT),
    ("Admissões", "Sobrequalificação nas admissões",
     f"DIVIDE ( CALCULATE ( [Admissões com superior], dCBO[Categoria da ocupação] = {NIVEL_MEDIO_OP} ), "
     "[Admissões com superior] )", PCT),
    ("Descompasso", "Índice de descompasso",
     ["-- Em branco quando a área tem menos de 50 concluintes no recorte (amostra pequena)",
      "IF ( [Concluintes] >= 50, DIVIDE ( [Admissões com superior na área], [Concluintes] ) )"], IDX),
    ("Salários", "Salário mediano de admissão (superior)",
     ["CALCULATE (", "    MEDIAN ( fAdmissoes[salario] ),", '    fAdmissoes[movimento] = "Admissão",',
      "    fAdmissoes[peso] = 1,", "    fAdmissoes[salario_comparavel] = TRUE (),",
      f"    fAdmissoes[nivel_instrucao] = {SUP}", ")"], BRL),
    ("Salários", "Salário mediano de admissão (médio)",
     ["CALCULATE (", "    MEDIAN ( fAdmissoes[salario] ),", '    fAdmissoes[movimento] = "Admissão",',
      "    fAdmissoes[peso] = 1,", "    fAdmissoes[salario_comparavel] = TRUE (),",
      f"    fAdmissoes[nivel_instrucao] = {MED}", ")"], BRL),
    ("Salários", "Prêmio salarial na admissão",
     "DIVIDE ( [Salário mediano de admissão (superior)], [Salário mediano de admissão (médio)] )", IDX),
    ("Estoque", "Vínculos ativos",
     ["-- Estoque: usa o último ano do filtro (somar anos de estoque não faz sentido)",
      "VAR UltimoAno = MAX ( dCalendario[Ano] )",
      "RETURN CALCULATE ( SUM ( fEstoqueEmprego[vinculos] ), dCalendario[Ano] = UltimoAno )"], NUM),
    ("Estoque", "Vínculos com superior",
     f"CALCULATE ( [Vínculos ativos], fEstoqueEmprego[nivel_instrucao] = {SUP} )", NUM),
    ("Estoque", "Vínculos com superior na área",
     'CALCULATE ( [Vínculos com superior], dCBO[Vínculo com a área] = "Principal" )', NUM),
    ("Estoque", "Participação de formados no emprego", "DIVIDE ( [Vínculos com superior], [Vínculos ativos] )", PCT),
    ("Estoque", "Sobrequalificação no estoque",
     f"DIVIDE ( CALCULATE ( [Vínculos com superior], dCBO[Categoria da ocupação] = {NIVEL_MEDIO_OP} ), "
     "[Vínculos com superior] )", PCT),
    ("Estoque", "Remuneração média (superior)",
     ["VAR UltimoAno = MAX ( dCalendario[Ano] )",
      "RETURN CALCULATE (",
      "    DIVIDE ( SUM ( fEstoqueEmprego[rem_soma] ), SUM ( fEstoqueEmprego[rem_validos] ) ),",
      f"    fEstoqueEmprego[nivel_instrucao] = {SUP}, dCalendario[Ano] = UltimoAno", ")"], BRL),
    ("Estoque", "Remuneração média (médio)",
     ["VAR UltimoAno = MAX ( dCalendario[Ano] )",
      "RETURN CALCULATE (",
      "    DIVIDE ( SUM ( fEstoqueEmprego[rem_soma] ), SUM ( fEstoqueEmprego[rem_validos] ) ),",
      f"    fEstoqueEmprego[nivel_instrucao] = {MED}, dCalendario[Ano] = UltimoAno", ")"], BRL),
    ("Estoque", "Prêmio salarial no estoque (média)",
     "DIVIDE ( [Remuneração média (superior)], [Remuneração média (médio)] )", IDX),
]

# (de, para): muitos -> um
RELACOES = [
    ("fOfertaEnsino.CO_MUNICIPIO", "dMunicipio.cod_ibge_7"),
    ("fAdmissoes.municipio", "dMunicipio.cod_ibge_6"),
    ("fEstoqueEmprego.municipio", "dMunicipio.cod_ibge_6"),
    ("fOfertaEnsino.NU_ANO_CENSO", "dCalendario.Ano"),
    ("fAdmissoes.ano", "dCalendario.Ano"),
    ("fEstoqueEmprego.ano", "dCalendario.Ano"),
    ("fOfertaEnsino.CO_CINE_AREA_GERAL", "dArea.area_codigo"),
    ("dCBO.area_codigo", "dArea.area_codigo"),
    ("fAdmissoes.cbo2002ocupacao", "dCBO.cbo_codigo"),
    ("fEstoqueEmprego.cbo2002ocupacao", "dCBO.cbo_codigo"),
    ("fAdmissoes.nivel_instrucao", "dEscolaridade.nivel_instrucao"),
    ("fEstoqueEmprego.nivel_instrucao", "dEscolaridade.nivel_instrucao"),
]


def indenta(texto, nivel):
    return "\n".join((T * nivel + linha) if linha else "" for linha in texto.split("\n"))


def tabela_tmdl(nome, colunas, m, oculta=False, medidas=None):
    ren = RENOMEAR.get(nome, {})
    colunas = [(ren.get(c, c), tp, o) for c, tp, o in colunas]
    linhas = [f"table {nome_tmdl(nome)}", f"{T}lineageTag: {guid(nome)}"]
    if oculta:
        linhas.append(f"{T}isHidden")
    linhas.append("")
    for pasta, medida, dax, fmt in medidas or []:
        if isinstance(dax, list):
            linhas.append(f"{T}measure {nome_tmdl(medida)} =")
            linhas += [T * 3 + d for d in dax]
        else:
            linhas.append(f"{T}measure {nome_tmdl(medida)} = {dax}")
        linhas += [f"{T * 2}formatString: {fmt}", f"{T * 2}displayFolder: {pasta}",
                   f"{T * 2}lineageTag: {guid(nome + '/m/' + medida)}", ""]
    for col, tipo, oculto in colunas:
        linhas.append(f"{T}column {nome_tmdl(col)}")
        linhas.append(f"{T * 2}dataType: {TIPO_TMDL[tipo]}")
        if oculto:
            linhas.append(f"{T * 2}isHidden")
        if tipo in ("int64", "double"):
            linhas.append(f"{T * 2}formatString: 0")
        linhas += [f"{T * 2}lineageTag: {guid(nome + '/c/' + col)}", f"{T * 2}summarizeBy: none",
                   f"{T * 2}sourceColumn: {col}", "", f"{T * 2}annotation SummarizationSetBy = User", ""]
    linhas += [f"{T}partition {nome_tmdl(nome)} = m", f"{T * 2}mode: import", f"{T * 2}source =",
               indenta(m, 4), "", f"{T}annotation PBI_ResultType = Table", ""]
    return "\n".join(linhas)


def gerar_modelo():
    definicao = MODELO / "definition"
    shutil.rmtree(definicao, ignore_errors=True)
    (definicao / "tables").mkdir(parents=True)
    escreve_json(MODELO / "definition.pbism", {
        "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})

    (definicao / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n", encoding="utf-8")
    ordem = ["_Medidas", "dCalendario", "dMunicipio", "dArea", "dCBO", "dEscolaridade",
             "fOfertaEnsino", "fAdmissoes", "fEstoqueEmprego"]
    modelo = ["model Model", "\tculture: pt-BR", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
              "\tsourceQueryCulture: pt-BR", "\tdataAccessOptions", "\t\tlegacyRedirects",
              "\t\treturnErrorValuesAsNull", "", 'annotation PBI_QueryOrder = ["PastaDados"]', ""]
    modelo += [f"ref table {nome_tmdl(t)}" for t in ordem]
    (definicao / "model.tmdl").write_text("\n".join(modelo) + "\n", encoding="utf-8")

    (definicao / "expressions.tmdl").write_text(
        f'expression PastaDados = "{PASTA_DADOS}" meta [IsParameterQuery=true, Type="Text", '
        f"IsParameterQueryRequired=true]\n\tlineageTag: {guid('PastaDados')}\n\n"
        "\tannotation PBI_ResultType = Text\n", encoding="utf-8")

    for nome, (arquivo, colunas, sel) in TABELAS.items():
        tipos = [(c, M_TIPO[t]) for c, t, _ in colunas]
        m = csv_m(arquivo, tipos, [c for c, _, _ in colunas] if sel else None, RENOMEAR.get(nome))
        (definicao / "tables" / f"{nome}.tmdl").write_text(tabela_tmdl(nome, colunas, m), encoding="utf-8")
    extras = {
        "dCalendario": tabela_tmdl("dCalendario", [("Ano", "int64", False)], M_CALENDARIO),
        "dEscolaridade": tabela_tmdl("dEscolaridade", [("nivel_instrucao", "text", False),
                                                       ("ordem", "int64", True)], M_ESCOLARIDADE),
        "_Medidas": tabela_tmdl("_Medidas", [("Coluna", "text", True)], M_MEDIDAS, medidas=MEDIDAS),
    }
    for nome, texto in extras.items():
        (definicao / "tables" / f"{nome}.tmdl").write_text(texto, encoding="utf-8")

    rel = []
    for de, para in RELACOES:
        rel += [f"relationship {guid(de + '->' + para)}", f"\tfromColumn: {de}", f"\ttoColumn: {para}", ""]
    (definicao / "relationships.tmdl").write_text("\n".join(rel), encoding="utf-8")


# --------------------------------------------------------------------------
# Relatório (PBIR)
# --------------------------------------------------------------------------

VISUAL_SCHEMA = f"{SCHEMA}/item/report/definition/visualContainer/2.4.0/schema.json"


def escreve_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def campo(ref):
    """'_Medidas[Concluintes]' vira Measure; 'dArea.area_nome' vira Column."""
    if "[" in ref:
        tabela, prop = ref[:-1].split("[")
        tipo = "Measure"
    else:
        tabela, prop = ref.split(".", 1)
        tipo = "Column"
    return {tipo: {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": prop}}, f"{tabela}.{prop}", prop


def projecoes(refs, ativo=False):
    saida = []
    for ref in refs:
        f, query_ref, nativo = campo(ref)
        p = {"field": f, "queryRef": query_ref, "nativeQueryRef": nativo}
        if ativo:
            p["active"] = True
        saida.append(p)
    return {"projections": saida}


def literal(valor):
    return {"expr": {"Literal": {"Value": valor}}}


def titulo_visual(texto):
    return {"title": [{"properties": {"show": literal("true"), "text": literal(f"'{texto}'")}}]}


def visual(nome, tipo, pos, papeis=None, titulo=None, ordenar=None, objetos=None):
    x, y, w, h = pos
    v = {"visualType": tipo}
    if papeis:
        estado = {}
        for papel, refs in papeis.items():
            estado[papel] = projecoes(refs, ativo=papel in ("Category", "Values") and tipo != "card"
                                      and tipo != "tableEx")
        v["query"] = {"queryState": estado}
        if ordenar:
            f, _, _ = campo(ordenar)
            v["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": "Descending"}]}
    if objetos:
        v["objects"] = objetos
    if titulo:
        v["visualContainerObjects"] = titulo_visual(titulo)
    v["drillFilterOtherVisuals"] = True
    return {"$schema": VISUAL_SCHEMA, "name": nome,
            "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0}, "visual": v}


def caixa_texto(nome, texto, pos, tamanho="20pt"):
    x, y, w, h = pos
    return {"$schema": VISUAL_SCHEMA, "name": nome,
            "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0},
            "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": texto, "textStyle": {"fontWeight": "bold", "fontSize": tamanho}}]}]}}]},
                "drillFilterOtherVisuals": True}}


DROPDOWN = {"data": [{"properties": {"mode": literal("'Dropdown'")}}]}
M = "_Medidas"


def cabecalho(prefixo, titulo):
    return [
        caixa_texto(f"{prefixo}_titulo", titulo, (24, 14, 840, 52), "16pt"),
        visual(f"{prefixo}_filtro_ano", "slicer", (880, 8, 180, 64), {"Values": ["dCalendario.Ano"]},
               objetos=DROPDOWN),
        visual(f"{prefixo}_filtro_municipio", "slicer", (1076, 8, 180, 64), {"Values": ["dMunicipio.Município"]},
               objetos=DROPDOWN),
    ]


def cartoes(prefixo, medidas):
    return [visual(f"{prefixo}_cartao_{i}", "card", (24 + i * 312, 84, 296, 110), {"Values": [f"{M}[{m}]"]})
            for i, m in enumerate(medidas)]


ESQ, DIR = (24, 210, 608, 490), (648, 210, 608, 490)

PAGINAS = [
    ("visao_geral", "Visão geral", "Formação superior e mercado de trabalho na Sub-região Oeste da RMSP",
     ["Concluintes", "Admissões com superior", "Prêmio salarial na admissão", "Sobrequalificação nas admissões"],
     [("clusteredColumnChart", "Concluintes e admissões com superior na área",
       {"Category": ["dCalendario.Ano"], "Y": [f"{M}[Concluintes]", f"{M}[Admissões com superior na área]"]}, None),
      ("lineChart", "Sobrequalificação e EaD",
       {"Category": ["dCalendario.Ano"],
        "Y": [f"{M}[Sobrequalificação nas admissões]", f"{M}[Participação EaD nos concluintes]"]}, None)]),
    ("descompasso", "Descompasso", "Índice de descompasso por área (admissões com diploma ÷ concluintes)",
     ["Índice de descompasso", "Concluintes", "Admissões com superior na área", "Participação de formados nas admissões"],
     [("clusteredBarChart", "Índice de descompasso por área",
       {"Category": ["dArea.Área (curta)"], "Y": [f"{M}[Índice de descompasso]"]}, f"{M}[Índice de descompasso]"),
      ("tableEx", "Detalhe por área",
       {"Values": ["dArea.Área (curta)", f"{M}[Concluintes]", f"{M}[Admissões com superior na área]",
                   f"{M}[Índice de descompasso]"]}, None)]),
    ("salarios", "Salários", "Prêmio salarial do diploma",
     ["Salário mediano de admissão (superior)", "Salário mediano de admissão (médio)",
      "Prêmio salarial na admissão", "Prêmio salarial no estoque (média)"],
     [("clusteredColumnChart", "Salário mediano de admissão por ano",
       {"Category": ["dCalendario.Ano"],
        "Y": [f"{M}[Salário mediano de admissão (superior)]", f"{M}[Salário mediano de admissão (médio)]"]}, None),
      ("clusteredBarChart", "Prêmio salarial na admissão por município",
       {"Category": ["dMunicipio.Município"], "Y": [f"{M}[Prêmio salarial na admissão]"]},
       f"{M}[Prêmio salarial na admissão]")]),
    ("oferta", "Oferta de cursos", "Oferta de ensino superior na região (INEP)",
     ["Matrículas", "Concluintes", "Participação privada", "Participação EaD nos concluintes"],
     [("columnChart", "Matrículas por ano e rede",
       {"Category": ["dCalendario.Ano"], "Series": ["fOfertaEnsino.Rede"], "Y": [f"{M}[Matrículas]"]}, None),
      ("tableEx", "Concluintes por curso",
       {"Values": ["fOfertaEnsino.Curso", f"{M}[Concluintes]"]}, f"{M}[Concluintes]")]),
    ("emprego", "Emprego (RAIS)", "Emprego formal em 31/12 (RAIS, último ano do filtro)",
     ["Vínculos ativos", "Participação de formados no emprego", "Sobrequalificação no estoque",
      "Prêmio salarial no estoque (média)"],
     [("clusteredBarChart", "Formados empregados em ocupações da área",
       {"Category": ["dArea.Área (curta)"], "Y": [f"{M}[Vínculos com superior na área]"]},
       f"{M}[Vínculos com superior na área]"),
      ("lineChart", "Formados no emprego e sobrequalificação",
       {"Category": ["dCalendario.Ano"],
        "Y": [f"{M}[Participação de formados no emprego]", f"{M}[Sobrequalificação no estoque]"]}, None)]),
]


def gerar_relatorio():
    definicao = RELATORIO / "definition"
    shutil.rmtree(definicao, ignore_errors=True)
    escreve_json(RELATORIO / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../PI2.SemanticModel"}}})
    escreve_json(definicao / "version.json", {
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    tema = RELATORIO / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU10.json"
    tema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SAIDA / "recursos" / "CY24SU10.json", tema)
    escreve_json(definicao / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/3.0.0/schema.json",
        "themeCollection": {"baseTheme": {
            "name": "CY24SU10", "reportVersionAtImport": {"visual": "1.8.95", "report": "2.0.95", "page": "1.3.95"},
            "type": "SharedResources"}},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
            {"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})

    for nome, exibicao, titulo, cards, graficos in PAGINAS:
        pasta = definicao / "pages" / nome
        escreve_json(pasta / "page.json", {
            "$schema": f"{SCHEMA}/item/report/definition/page/2.0.0/schema.json",
            "name": nome, "displayName": exibicao, "displayOption": "FitToPage", "height": 720, "width": 1280})
        visuais = cabecalho(nome, titulo) + cartoes(nome, cards)
        for i, (tipo, tit, papeis, ordem) in enumerate(graficos):
            visuais.append(visual(f"{nome}_grafico_{i}", tipo, (ESQ, DIR)[i], papeis, titulo=tit, ordenar=ordem))
        for z, v in enumerate(visuais):
            v["position"]["z"] = z * 1000
            v["position"]["tabOrder"] = z * 1000
            escreve_json(pasta / "visuals" / v["name"] / "visual.json", v)
    escreve_json(definicao / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p[0] for p in PAGINAS], "activePageName": PAGINAS[0][0]})


def main():
    gerar_modelo()
    gerar_relatorio()
    escreve_json(SAIDA / "PI2.pbip", {
        "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": "PI2.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    print(f"Projeto gerado em {SAIDA / 'PI2.pbip'}")
    print(f"Pasta de dados: {PASTA_DADOS}")


if __name__ == "__main__":
    main()
