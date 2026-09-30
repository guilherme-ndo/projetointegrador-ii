"""
06 - IBGE, Censo Demográfico 2022 (SIDRA), por município do recorte.

Busca direto na API do SIDRA (precisa de internet):
  9514   população residente total
  10061  pessoas de 18 anos ou mais por nível de instrução e grupo de idade
  10064  pessoas com superior completo por área geral de formação (CINE)
  10059  pessoas de 18 anos ou mais que frequentavam escola, por nível de ensino

Saídas:
  dados_tratados/fPopulacao.csv          município, grupo de idade, nível de instrução, pessoas
  dados_tratados/fFormadosResidentes.csv município, área CINE, grupo de idade, pessoas
  dados_tratados/fFrequenciaEscolar.csv  município, grupo de idade, nível que frequentava, pessoas

Uso: python scripts/06_ibge.py
"""
import re

import pandas as pd
import requests

from utils import TRATADOS, carregar_municipios

API = "https://apisidra.ibge.gov.br/values"
META = "https://servicodados.ibge.gov.br/api/v3/agregados/{}/metadados"

IDADE = {"95253": "Total", "100052": "18 a 24 anos", "108866": "25 anos ou mais"}
NIVEL = {"120704": "Total", "9493": "Sem instrução e fundamental incompleto",
         "9494": "Fundamental completo e médio incompleto", "9495": "Médio completo e superior incompleto",
         "99713": "Superior completo"}
FREQUENCIA = {"95300": "Total", "95307": "Superior de graduação", "7910": "Especialização",
              "7911": "Mestrado", "7912": "Doutorado"}


def sidra(caminho):
    resp = requests.get(f"{API}/{caminho}", timeout=120)
    resp.raise_for_status()
    dados = resp.json()
    df = pd.DataFrame(dados[1:])  # primeira linha é o cabeçalho descritivo
    df["V"] = pd.to_numeric(df["V"], errors="coerce")  # "-" e "X" (sigilo) viram vazio
    return df


def areas_gerais():
    """Categorias da tabela 10064 que são áreas gerais CINE (código de 2 dígitos)."""
    meta = requests.get(META.format(10064), timeout=60).json()
    cats = next(c for c in meta["classificacoes"] if c["id"] == 2082)["categorias"]
    return {str(c["id"]): c["nome"] for c in cats if re.match(r"^\d{2} - ", c["nome"])}


def main():
    mun = carregar_municipios()
    n6 = ",".join(str(c) for c in mun["cod_ibge_7"])
    idades = ",".join(IDADE)

    print("População total (9514)...")
    pop_total = sidra(f"t/9514/n6/{n6}/v/93/p/2022/c2/6794/c287/100362/c286/113635")
    pop_total = pop_total[["D1C", "V"]].rename(columns={"D1C": "municipio", "V": "pessoas"})
    pop_total["grupo_idade"], pop_total["nivel_instrucao"] = "Todas as idades", "Total"

    print("Nível de instrução (10061)...")
    inst = sidra(f"t/10061/n6/{n6}/v/2667/p/2022/c1568/{','.join(NIVEL)}/c58/{idades}/c2/6794/c86/95251")
    inst = pd.DataFrame({"municipio": inst["D1C"], "grupo_idade": inst["D5C"].map(IDADE),
                         "nivel_instrucao": inst["D4C"].map(NIVEL), "pessoas": inst["V"]})
    populacao = pd.concat([pop_total, inst], ignore_index=True)
    populacao["municipio"] = populacao["municipio"].astype(int)
    populacao.to_csv(TRATADOS / "fPopulacao.csv", index=False, encoding="utf-8-sig")

    print("Formados por área (10064)...")
    areas = areas_gerais()
    form = sidra(f"t/10064/n6/{n6}/v/1920/p/2022/c2082/78032,{','.join(areas)}/c58/95253,108866")
    form = pd.DataFrame({
        "municipio": form["D1C"].astype(int),
        "area_codigo": form["D4C"].map(lambda c: areas[c][:2] if c in areas else "Total"),
        "grupo_idade": form["D5C"].map(IDADE),
        "pessoas": form["V"],
    })
    form = form[form["area_codigo"] != "Total"]  # o total é a soma das áreas (01 a 11)
    form.to_csv(TRATADOS / "fFormadosResidentes.csv", index=False, encoding="utf-8-sig")

    print("Frequência escolar (10059)...")
    freq = sidra(f"t/10059/n6/{n6}/v/13284/p/2022/c11798/{','.join(FREQUENCIA)}/c58/{idades}/c2/6794/c86/95251")
    freq = pd.DataFrame({"municipio": freq["D1C"].astype(int), "grupo_idade": freq["D5C"].map(IDADE),
                         "nivel_frequentado": freq["D4C"].map(FREQUENCIA), "pessoas": freq["V"]})
    freq.to_csv(TRATADOS / "fFrequenciaEscolar.csv", index=False, encoding="utf-8-sig")

    # Resumo
    nomes = dict(zip(mun["cod_ibge_7"], mun["nome"]))
    p = inst.assign(municipio=inst["municipio"].astype(int)).pivot_table(
        index="municipio", columns=["grupo_idade", "nivel_instrucao"], values="pessoas", aggfunc="sum")
    resumo = pd.DataFrame({
        "populacao": pop_total.set_index(pop_total["municipio"].astype(int))["pessoas"],
        "superior_25mais_%": p[("25 anos ou mais", "Superior completo")] / p[("25 anos ou mais", "Total")] * 100,
    })
    f = freq.pivot_table(index="municipio", columns=["grupo_idade", "nivel_frequentado"], values="pessoas")
    resumo["jovens_18a24_na_graduacao_%"] = (f[("18 a 24 anos", "Superior de graduação")]
                                            / p[("18 a 24 anos", "Total")] * 100)
    resumo.index = resumo.index.map(nomes)
    print("\n" + resumo.round(1).to_string())
    tot = form[form["grupo_idade"] == "Total"].groupby("area_codigo")["pessoas"].sum()
    print("\nMoradores com superior completo por área (região):")
    print(tot.sort_values(ascending=False).to_string())
    print(f"\nSalvo em {TRATADOS}: fPopulacao.csv, fFormadosResidentes.csv, fFrequenciaEscolar.csv")


if __name__ == "__main__":
    main()
