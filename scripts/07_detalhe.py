"""
07 - Detalhamento por município e por curso, com foco nos cursos da Fatec.

Rode depois dos scripts 02 a 06.

Saídas:
  dados_tratados/detalhe_municipio.csv       indicadores de 2024 por município (+ região)
  dados_tratados/detalhe_municipio_area.csv  concluintes x admissões por município e área (2024)
  dados_tratados/detalhe_curso.csv           cursos da região em 2024 (todas as instituições)
  dados_tratados/detalhe_fatec.csv           cursos das Fatecs x ocupações que contratam
  docs/cursos_fatec.md                       resumo legível dos cursos da Fatec

A ligação curso -> ocupações da Fatec fica em docs/curso_ocupacao_fatec.csv
(proposta, para revisar). A concorrência entre cursos fica no nível da área CINE
(índice de descompasso): cursos de uma mesma área disputam as mesmas ocupações,
e os campos detalhados da CINE não acompanham essa divisão (ex.: ADS em 0613,
Ciência de Dados e Jogos Digitais em 0681).

Uso: python scripts/07_detalhe.py
"""
import pandas as pd

from utils import RAIZ, TRATADOS, ler_admissoes

ANO = 2024
SUP, MED = "Superior completo ou mais", "Médio completo"
MIN_CONCLUINTES = 50  # abaixo disso o índice fica em branco (amostra pequena)
NOME_FATEC = {"15709": "Fatec Osasco", "15757": "Fatec Barueri", "16395": "Fatec Carapicuíba",
              "20478": "Fatec Santana de Parnaíba", "34": "Fatec São Paulo (polos EaD)"}


def carregar():
    oferta = pd.read_csv(TRATADOS / "fOfertaEnsino.csv", dtype={"CO_CINE_AREA_GERAL": str, "CO_IES": str})
    cbo = pd.read_csv(TRATADOS / "dCBO.csv", dtype=str)
    adm = ler_admissoes(["ano", "municipio", "cbo2002ocupacao", "movimento", "nivel_instrucao", "peso",
                         "salario", "salario_comparavel"]).astype({"cbo2002ocupacao": str, "peso": int})
    adm = adm[adm["movimento"] == "Admissão"].merge(
        cbo[["cbo_codigo", "categoria_ocupacao", "area_codigo", "tipo_vinculo"]],
        left_on="cbo2002ocupacao", right_on="cbo_codigo", how="left")
    est = pd.read_csv(TRATADOS / "fEstoqueEmprego.csv", dtype={"cbo2002ocupacao": str})
    est = est.merge(cbo[["cbo_codigo", "categoria_ocupacao", "area_codigo", "tipo_vinculo"]],
                    left_on="cbo2002ocupacao", right_on="cbo_codigo", how="left")
    mun = pd.read_csv(TRATADOS / "dMunicipio.csv")
    return oferta, adm, est, mun


def mediana_salario(df, nivel):
    ok = df[df["salario_comparavel"] & (df["peso"] == 1) & (df["nivel_instrucao"] == nivel)]
    return ok["salario"].median()


def por_municipio(oferta, adm, est, mun):
    of = oferta[oferta["NU_ANO_CENSO"] == ANO]
    ad = adm[adm["ano"] == ANO]
    es = est[est["ano"] == ANO]
    linhas = []
    grupos = [(r.nome, r.cod_ibge_7, r.cod_ibge_6) for r in mun.itertuples()] + [("Região (8 municípios)", None, None)]
    for nome, c7, c6 in grupos:
        o = of if c7 is None else of[of["CO_MUNICIPIO"] == c7]
        a = ad if c6 is None else ad[ad["municipio"] == c6]
        e = es if c6 is None else es[es["municipio"] == c6]
        sup = a[a["nivel_instrucao"] == SUP]
        esup = e[e["nivel_instrucao"] == SUP]
        linhas.append({
            "municipio": nome,
            "concluintes": o["QT_CONC"].sum(),
            "matriculas": o["QT_MAT"].sum(),
            "part_privada_matriculas": o.loc[o["rede"] == "Privada", "QT_MAT"].sum() / o["QT_MAT"].sum(),
            "part_ead_concluintes": o.loc[o["modalidade"] == "EaD", "QT_CONC"].sum() / o["QT_CONC"].sum(),
            "admissoes": a["peso"].sum(),
            "admissoes_superior": sup["peso"].sum(),
            "part_superior_admissoes": sup["peso"].sum() / a["peso"].sum(),
            "sobrequalificacao": sup.loc[sup["categoria_ocupacao"] == "Nível médio ou operacional", "peso"].sum()
                                 / sup["peso"].sum(),
            "salario_mediano_superior": mediana_salario(a, SUP),
            "salario_mediano_medio": mediana_salario(a, MED),
            "vinculos_ativos": e["vinculos"].sum(),
            "part_superior_estoque": esup["vinculos"].sum() / e["vinculos"].sum(),
        })
    df = pd.DataFrame(linhas)
    df["premio_salarial"] = df["salario_mediano_superior"] / df["salario_mediano_medio"]
    regiao = df.iloc[-1]
    df["part_concluintes_regiao"] = df["concluintes"] / regiao["concluintes"]
    df["part_admissoes_superior_regiao"] = df["admissoes_superior"] / regiao["admissoes_superior"]
    ibge = pd.read_csv(TRATADOS / "indicadores_municipio.csv")
    df = df.merge(ibge[["nome", "populacao", "part_superior_25mais", "taxa_graduacao_18a24"]],
                  left_on="municipio", right_on="nome", how="left").drop(columns="nome")
    return df


def por_municipio_area(oferta, adm, mun):
    of = oferta[oferta["NU_ANO_CENSO"] == ANO]
    conc = (of.groupby(["CO_MUNICIPIO", "CO_CINE_AREA_GERAL"])["QT_CONC"].sum()
            .rename("concluintes").reset_index()
            .merge(mun, left_on="CO_MUNICIPIO", right_on="cod_ibge_7")
            .rename(columns={"CO_CINE_AREA_GERAL": "area_codigo"}))
    sup = adm[(adm["ano"] == ANO) & (adm["nivel_instrucao"] == SUP) & (adm["tipo_vinculo"] == "Principal")]
    ads = (sup.groupby(["municipio", "area_codigo"])["peso"].sum().rename("admissoes_superior_area")
           .reset_index().merge(mun, left_on="municipio", right_on="cod_ibge_6"))
    df = conc[["nome", "area_codigo", "concluintes"]].merge(
        ads[["nome", "area_codigo", "admissoes_superior_area"]], on=["nome", "area_codigo"], how="outer")
    df["indice_descompasso"] = (df["admissoes_superior_area"] / df["concluintes"]).where(
        df["concluintes"] >= MIN_CONCLUINTES)
    areas = pd.read_csv(TRATADOS / "dArea.csv", dtype=str)
    return (df.merge(areas[["area_codigo", "area_curta"]], on="area_codigo", how="left")
            .rename(columns={"nome": "municipio"}).sort_values(["municipio", "area_codigo"]))


def por_curso(oferta):
    of = oferta[oferta["NU_ANO_CENSO"] == ANO]
    g = of.groupby("curso")
    df = pd.DataFrame({
        "area": g["NO_CINE_AREA_GERAL"].first(),
        "rotulo_cine": g["NO_CINE_ROTULO"].first(),
        "instituicoes": g["CO_IES"].nunique(),
        "ingressantes": g["QT_ING"].sum(),
        "matriculas": g["QT_MAT"].sum(),
        "concluintes": g["QT_CONC"].sum(),
        "part_ead_concluintes": of[of["modalidade"] == "EaD"].groupby("curso")["QT_CONC"].sum() / g["QT_CONC"].sum(),
        "tem_fatec": g["fatec"].any(),
    })
    df["concluintes_2020_2024"] = oferta.groupby("curso")["QT_CONC"].sum()
    return df.sort_values("concluintes", ascending=False).reset_index()


def fatec(oferta, adm, est):
    mapa = pd.read_csv(RAIZ / "docs" / "curso_ocupacao_fatec.csv", dtype=str)
    mapa["prefixos"] = mapa["cbo_prefixos"].str.split(";").map(tuple)
    of = oferta[oferta["fatec"]]
    area_ano = pd.read_csv(TRATADOS / "indicadores_area_ano.csv", dtype={"area_codigo": str})
    area_ano = area_ano[area_ano["ano"] == ANO].set_index("area_codigo")
    linhas = []
    for (cod_ies, curso), d in of.groupby(["CO_IES", "curso"]):
        sigla = NOME_FATEC.get(cod_ies, d["SG_IES"].iloc[0])
        ano = d.groupby("NU_ANO_CENSO")[["QT_ING", "QT_CONC"]].sum()
        ing = lambda a: ano["QT_ING"].get(a, 0)  # noqa: E731
        conc = lambda a: ano["QT_CONC"].get(a, 0)  # noqa: E731
        rotulo = d["NO_CINE_ROTULO"].iloc[-1]
        area_cod = d["CO_CINE_AREA_GERAL"].iloc[-1]
        linha = {
            "fatec": sigla, "municipio": ", ".join(sorted(d["NO_MUNICIPIO"].unique())), "curso": curso,
            "modalidade": d["modalidade"].iloc[-1], "area": d["NO_CINE_AREA_GERAL"].iloc[-1], "rotulo_cine": rotulo,
            "ingressantes_2024": ing(ANO), "concluintes_2024": conc(ANO),
            "concluintes_2020_2024": ano["QT_CONC"].sum(),
            # só quando o curso já tinha ingressantes em 2020 e 2021
            "conclusao_aprox": ((conc(2023) + conc(2024)) / (ing(2020) + ing(2021))
                                if ing(2020) > 0 and ing(2021) > 0 else None),
            "situacao_2024": "com ingresso" if ing(ANO) > 0 else "sem ingresso em 2024",
            "area_codigo": area_cod,
            "concluintes_area_regiao_2024": area_ano["concluintes"].get(area_cod),
            "indice_descompasso_area_2024": area_ano["indice_descompasso"].get(area_cod),
        }
        m = mapa[mapa["curso"] == curso]
        if len(m):
            pref = m["prefixos"].iloc[0]
            a = adm[adm["cbo2002ocupacao"].str.startswith(pref)]
            e = est[est["cbo2002ocupacao"].str.startswith(pref) & (est["ano"] == ANO)]
            a_sup = a[a["nivel_instrucao"] == SUP]
            linha.update({
                "ocupacoes_cbo": m["cbo_prefixos"].iloc[0],
                "admissoes_superior_2021": a_sup.loc[a_sup["ano"] == 2021, "peso"].sum(),
                "admissoes_superior_2024": a_sup.loc[a_sup["ano"] == ANO, "peso"].sum(),
                "admissoes_todas_2024": a.loc[a["ano"] == ANO, "peso"].sum(),
                "salario_mediano_superior_2024": mediana_salario(a[a["ano"] == ANO], SUP),
                "vinculos_superior_2024": e.loc[e["nivel_instrucao"] == SUP, "vinculos"].sum(),
            })
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    # 2021 como base: 2020 tem admissões baixas por causa da pandemia
    df["crescimento_admissoes_2021_2024"] = df["admissoes_superior_2024"] / df["admissoes_superior_2021"] - 1
    return df.sort_values(["fatec", "curso"])


def titulo(curso):
    minusculas = {"De", "Da", "Do", "Das", "Dos", "E", "Para", "A"}
    return " ".join(p if i == 0 or p not in minusculas else p.lower()
                    for i, p in enumerate(curso.title().split()))


def fmt(v, casas=0, pct=False):
    if pd.isna(v):
        return "–"
    if pct:
        return f"{v * 100:.0f}%"
    txt = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return txt


def markdown(fat):
    linhas = [
        "# Cursos das Fatecs da região: oferta e mercado",
        "",
        f"Gerado por `scripts/07_detalhe.py`. Dados: INEP 2020-2024, CAGED 2020-2024 e RAIS {ANO}, "
        "nos 8 municípios do recorte.",
        "",
        "- **Admissões de formados**: admissões de pessoas com superior completo nas ocupações ligadas ao curso "
        "(`docs/curso_ocupacao_fatec.csv`, proposta a revisar). Cursos que levam às mesmas ocupações "
        "(ex.: ADS, Jogos Digitais e Sistemas para Internet) mostram os mesmos números.",
        "- **Crescimento**: de 2021 a 2024 (2020 teve admissões baixas por causa da pandemia).",
        "- **Índice da área**: admissões de formados na área ÷ concluintes da área na região em 2024. É a medida de "
        "concorrência: todos os cursos da área disputam as mesmas vagas.",
        "- **Conclusão aprox.**: concluintes de 2023-2024 ÷ ingressantes de 2020-2021.",
        "",
        "| Fatec | Curso | Ingr. 2024 | Concl. 2024 | Conclusão aprox. | Admissões de formados 2024 | "
        "Crescimento 2021-24 | Salário mediano (formados) | Índice da área |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in fat.itertuples():
        situacao = "" if r.situacao_2024 == "com ingresso" else " (sem ingresso em 2024)"
        linhas.append(
            f"| {r.fatec} | {titulo(r.curso)}{situacao} | {fmt(r.ingressantes_2024)} | {fmt(r.concluintes_2024)} | "
            f"{fmt(r.conclusao_aprox, pct=True)} | {fmt(r.admissoes_superior_2024)} | "
            f"{fmt(r.crescimento_admissoes_2021_2024, pct=True)} | R$ {fmt(r.salario_mediano_superior_2024)} | "
            f"{fmt(r.indice_descompasso_area_2024, 1)} |")
    linhas += ["", "Cursos EaD da Fatec São Paulo (FATEC-SP) aparecem pelos polos da região.", ""]
    (RAIZ / "docs" / "cursos_fatec.md").write_text("\n".join(linhas), encoding="utf-8")


def main():
    oferta, adm, est, mun = carregar()
    m = por_municipio(oferta, adm, est, mun)
    ma = por_municipio_area(oferta, adm, mun)
    c = por_curso(oferta)
    f = fatec(oferta, adm, est)
    m.to_csv(TRATADOS / "detalhe_municipio.csv", index=False, encoding="utf-8-sig")
    ma.to_csv(TRATADOS / "detalhe_municipio_area.csv", index=False, encoding="utf-8-sig")
    c.to_csv(TRATADOS / "detalhe_curso.csv", index=False, encoding="utf-8-sig")
    f.to_csv(TRATADOS / "detalhe_fatec.csv", index=False, encoding="utf-8-sig")
    markdown(f)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(f"Por município ({ANO}):")
    print(m.set_index("municipio")[["concluintes", "part_concluintes_regiao", "admissoes_superior",
                                   "part_admissoes_superior_regiao", "sobrequalificacao", "premio_salarial",
                                   "part_superior_25mais"]].round(2).to_string())
    print("\nÍndice de descompasso por município e área (em branco: menos de 50 concluintes):")
    print(ma.pivot_table(index="area_curta", columns="municipio", values="indice_descompasso").round(1).to_string())
    print("\nCursos com mais concluintes na região (2024):")
    print(c.head(15)[["curso", "instituicoes", "concluintes", "part_ead_concluintes", "tem_fatec"]].to_string(index=False))
    print("\nCursos das Fatecs:")
    print(f[["fatec", "curso", "ingressantes_2024", "concluintes_2024", "conclusao_aprox", "admissoes_superior_2024",
             "crescimento_admissoes_2021_2024", "salario_mediano_superior_2024", "indice_descompasso_area_2024"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main()
