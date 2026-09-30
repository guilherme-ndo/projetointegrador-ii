"""
Indicadores do projeto por ano e por área, calculados direto dos dados tratados.

Serve para conferir as medidas DAX do Power BI e alimentar relatório e
apresentação. Rode depois dos scripts 02, 03, 04 e 05 (a RAIS é opcional).

Saídas (pequenas, versionadas):
  dados_tratados/indicadores_ano.csv        um registro por ano (região toda)
  dados_tratados/indicadores_area_ano.csv   um registro por área CINE e ano
  dados_tratados/indicadores_municipio.csv  Censo 2022 por município (script 06)

Uso: python scripts/indicadores.py
"""
import pandas as pd

from utils import TRATADOS

DEFASAGEM_CONCLUSAO = 3  # anos entre ingresso e conclusão (aproximação: bacharelados e tecnólogos misturados)
SUPERIOR, MEDIO = "Superior completo ou mais", "Médio completo"


def carregar():
    oferta = pd.read_csv(TRATADOS / "fOfertaEnsino.csv", dtype={"CO_CINE_AREA_GERAL": str})
    cbo = pd.read_csv(TRATADOS / "dCBO.csv", dtype=str,
                      usecols=["cbo_codigo", "categoria_ocupacao", "area_codigo", "tipo_vinculo"])
    colunas = ["ano", "cbo2002ocupacao", "movimento", "nivel_instrucao", "peso", "salario", "salario_comparavel"]
    adm = pd.read_csv(TRATADOS / "fAdmissoes.csv", usecols=colunas,
                      dtype={"cbo2002ocupacao": str, "movimento": "category", "nivel_instrucao": "category"})
    adm = adm[adm["movimento"] == "Admissão"]
    adm = adm.merge(cbo, left_on="cbo2002ocupacao", right_on="cbo_codigo", how="left")
    estoque = None
    if (TRATADOS / "fEstoqueEmprego.csv").exists():
        estoque = pd.read_csv(TRATADOS / "fEstoqueEmprego.csv", dtype={"cbo2002ocupacao": str})
        estoque = estoque.merge(cbo, left_on="cbo2002ocupacao", right_on="cbo_codigo", how="left")
    return oferta, adm, estoque, cbo


def estoque_por_ano(estoque):
    """Indicadores da RAIS: vínculos ativos em 31/12."""
    sup = estoque[estoque["nivel_instrucao"] == SUPERIOR]
    ind = pd.DataFrame({
        "vinculos_ativos": estoque.groupby("ano")["vinculos"].sum(),
        "vinculos_superior": sup.groupby("ano")["vinculos"].sum(),
    })
    ind["part_superior_estoque"] = ind["vinculos_superior"] / ind["vinculos_ativos"]
    medio_op = sup["categoria_ocupacao"] == "Nível médio ou operacional"
    ind["sobrequalificacao_estoque"] = sup[medio_op].groupby("ano")["vinculos"].sum() / ind["vinculos_superior"]
    med = pd.read_csv(TRATADOS / "rais_mediana_ano.csv").pivot_table(
        index="ano", columns="nivel_instrucao", values="rem_mediana")
    ind["rem_mediana_superior_estoque"] = med[SUPERIOR]
    ind["rem_mediana_medio_estoque"] = med[MEDIO]
    ind["premio_salarial_estoque"] = med[SUPERIOR] / med[MEDIO]
    return ind


def por_ano(oferta, adm, estoque):
    of = oferta.groupby("NU_ANO_CENSO").agg(
        ingressantes=("QT_ING", "sum"), matriculas=("QT_MAT", "sum"), concluintes=("QT_CONC", "sum"))
    of["part_privada_matriculas"] = (oferta[oferta["rede"] == "Privada"].groupby("NU_ANO_CENSO")["QT_MAT"].sum()
                                     / of["matriculas"])
    of["part_ead_concluintes"] = (oferta[oferta["modalidade"] == "EaD"].groupby("NU_ANO_CENSO")["QT_CONC"].sum()
                                  / of["concluintes"])
    of["taxa_conclusao_defasada"] = of["concluintes"] / of["ingressantes"].shift(DEFASAGEM_CONCLUSAO)

    sup = adm[adm["nivel_instrucao"] == SUPERIOR]
    ad = pd.DataFrame({
        "admissoes": adm.groupby("ano")["peso"].sum(),
        "admissoes_superior": sup.groupby("ano")["peso"].sum(),
    })
    ad["part_superior_admissoes"] = ad["admissoes_superior"] / ad["admissoes"]
    medio_op = sup["categoria_ocupacao"] == "Nível médio ou operacional"
    ad["sobrequalificacao"] = sup[medio_op].groupby("ano")["peso"].sum() / ad["admissoes_superior"]

    comp = adm[adm["salario_comparavel"] & (adm["peso"] == 1)]
    med = comp[comp["nivel_instrucao"].isin([SUPERIOR, MEDIO])].groupby(
        ["ano", "nivel_instrucao"], observed=True)["salario"].median().unstack()
    ad["salario_mediano_superior"] = med[SUPERIOR]
    ad["salario_mediano_medio"] = med[MEDIO]
    ad["premio_salarial"] = med[SUPERIOR] / med[MEDIO]

    res = of.join(ad, how="outer")
    if estoque is not None:
        res = res.join(estoque_por_ano(estoque), how="outer")
    return res.rename_axis("ano").reset_index()


def por_area_ano(oferta, adm, estoque):
    of = (oferta.groupby(["NU_ANO_CENSO", "CO_CINE_AREA_GERAL", "NO_CINE_AREA_GERAL"])
          [["QT_ING", "QT_MAT", "QT_CONC"]].sum().reset_index()
          .rename(columns={"NU_ANO_CENSO": "ano", "CO_CINE_AREA_GERAL": "area_codigo", "NO_CINE_AREA_GERAL": "area_nome",
                           "QT_ING": "ingressantes", "QT_MAT": "matriculas", "QT_CONC": "concluintes"}))
    sup = adm[(adm["nivel_instrucao"] == SUPERIOR) & (adm["tipo_vinculo"] == "Principal")]
    ad = sup.groupby(["ano", "area_codigo"])["peso"].sum().rename("admissoes_superior_principal").reset_index()
    df = of.merge(ad, on=["ano", "area_codigo"], how="outer")
    if estoque is not None:
        est = estoque[(estoque["nivel_instrucao"] == SUPERIOR) & (estoque["tipo_vinculo"] == "Principal")]
        est = est.groupby(["ano", "area_codigo"])["vinculos"].sum().rename("estoque_superior_principal").reset_index()
        df = df.merge(est, on=["ano", "area_codigo"], how="outer")
    df["indice_descompasso"] = df["admissoes_superior_principal"] / df["concluintes"].where(df["concluintes"] > 0)
    return df.sort_values(["ano", "area_codigo"])


def por_municipio():
    """Indicadores do Censo 2022 (IBGE) por município."""
    pop = pd.read_csv(TRATADOS / "fPopulacao.csv")
    freq = pd.read_csv(TRATADOS / "fFrequenciaEscolar.csv")
    mun = pd.read_csv(TRATADOS / "dMunicipio.csv")
    p = pop.pivot_table(index="municipio", columns=["grupo_idade", "nivel_instrucao"], values="pessoas")
    f = freq.pivot_table(index="municipio", columns=["grupo_idade", "nivel_frequentado"], values="pessoas")
    ind = pd.DataFrame({
        "populacao": p[("Todas as idades", "Total")],
        "pop_25mais": p[("25 anos ou mais", "Total")],
        "superior_25mais": p[("25 anos ou mais", "Superior completo")],
        "pop_18a24": p[("18 a 24 anos", "Total")],
        "graduacao_18a24": f[("18 a 24 anos", "Superior de graduação")],
    })
    ind["part_superior_25mais"] = ind["superior_25mais"] / ind["pop_25mais"]
    ind["taxa_graduacao_18a24"] = ind["graduacao_18a24"] / ind["pop_18a24"]
    ind = ind.join(mun.set_index("cod_ibge_7")["nome"]).reset_index().rename(columns={"index": "municipio"})
    total = ind[["populacao", "pop_25mais", "superior_25mais", "pop_18a24", "graduacao_18a24"]].sum()
    regiao = {"municipio": 0, "nome": "Região (8 municípios)", **total,
              "part_superior_25mais": total["superior_25mais"] / total["pop_25mais"],
              "taxa_graduacao_18a24": total["graduacao_18a24"] / total["pop_18a24"]}
    return pd.concat([ind, pd.DataFrame([regiao])], ignore_index=True)


def main():
    oferta, adm, estoque, _ = carregar()
    ano = por_ano(oferta, adm, estoque)
    area = por_area_ano(oferta, adm, estoque)
    if (TRATADOS / "fFormadosResidentes.csv").exists():
        form = pd.read_csv(TRATADOS / "fFormadosResidentes.csv", dtype={"area_codigo": str})
        form = form[form["grupo_idade"] == "Total"].groupby("area_codigo")["pessoas"].sum()
        area["formados_residentes_2022"] = area["area_codigo"].map(form).where(area["ano"] == 2022)
        area["formados_residentes_por_vinculo"] = (area["formados_residentes_2022"]
                                                   / area["estoque_superior_principal"])
        mun = por_municipio()
        mun.to_csv(TRATADOS / "indicadores_municipio.csv", index=False, encoding="utf-8-sig")
        print("\nCenso 2022 por município:")
        print(mun.set_index("nome")[["populacao", "part_superior_25mais", "taxa_graduacao_18a24"]].round(3).to_string())
        print("\nFormados moradores (Censo 2022) por vínculo de formado na área (RAIS 2022):")
        print(area[area["ano"] == 2022].set_index("area_nome")[
            ["formados_residentes_2022", "estoque_superior_principal", "formados_residentes_por_vinculo"]].round(2).to_string())
    ano.to_csv(TRATADOS / "indicadores_ano.csv", index=False, encoding="utf-8-sig")
    area.to_csv(TRATADOS / "indicadores_area_ano.csv", index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 200)
    print(ano.round(3).set_index("ano").T.to_string())
    print("\nÍndice de descompasso por área e ano:")
    print(area.pivot_table(index="area_nome", columns="ano", values="indice_descompasso").round(2).to_string())
    print(f"\nSalvo em {TRATADOS / 'indicadores_ano.csv'} e {TRATADOS / 'indicadores_area_ano.csv'}")


if __name__ == "__main__":
    main()
