"""
04 - Dimensão ocupação (dCBO) a partir da tabela de-para CINE x CBO.

Aplica a busca em cascata (4, 3, 2 e 1 dígitos) a TODAS as ocupações da
CBO 2002, para que o Power BI só precise de uma relação simples entre
fAdmissoes[cbo2002ocupacao] e dCBO[cbo_codigo].

Também classifica cada ocupação pelo grande grupo da CBO:
  0 Forças armadas | 1 Dirigente | 2 Nível superior | 3 Técnico
  4 a 9 Nível médio ou operacional
Formado admitido em ocupação "Nível médio ou operacional" conta como
sobrequalificação e fica fora do índice de descompasso.

Antes de rodar:
  - docs/depara_cine_cbo.xlsx (versionado)
  - dados_brutos/caged/layout_novo_caged_movimentacao.xlsx (layout do PDET,
    aba cbo2002ocupação, com a lista de ocupações)
  - dados_tratados/fAdmissoes.csv (opcional, para o relatório de cobertura)

Saída: dados_tratados/dCBO.csv e docs/cobertura_depara.csv
Uso:   python scripts/04_dim_cbo.py
"""
import pandas as pd

from utils import BRUTOS, RAIZ, TRATADOS

DEPARA = RAIZ / "docs" / "depara_cine_cbo.xlsx"
LAYOUT = BRUTOS / "caged" / "layout_novo_caged_movimentacao.xlsx"

CATEGORIA = {
    "0": "Forças armadas",
    "1": "Dirigente",
    "2": "Nível superior",
    "3": "Técnico",
    **{g: "Nível médio ou operacional" for g in "456789"},
}


def carregar_depara():
    dp = pd.read_excel(DEPARA, sheet_name="DePara_CBO_CINE", dtype=str)
    areas = pd.read_excel(DEPARA, sheet_name="CINE_Areas", dtype=str)
    dp = dp.drop(columns="area_nome").merge(areas, on="area_codigo", how="left")
    repetidos = dp["cbo_codigo"][dp["cbo_codigo"].duplicated()]
    if len(repetidos):
        raise ValueError(f"Código CBO repetido no de-para: {list(repetidos)}")
    return dp.set_index("cbo_codigo")


def buscar(cbo, dp):
    """Retorna a linha do de-para mais específica para a ocupação (ou None)."""
    for n in (4, 3, 2, 1):
        if cbo[:n] in dp.index:
            return cbo[:n]
    return None


def main():
    dp = carregar_depara()
    cbo = pd.read_excel(LAYOUT, sheet_name="cbo2002ocupação", dtype=str)
    cbo.columns = ["cbo_codigo", "cbo_descricao"]
    cbo["cbo_codigo"] = cbo["cbo_codigo"].str.strip().str.zfill(6)
    cbo = cbo[cbo["cbo_codigo"].str.isdigit()].drop_duplicates("cbo_codigo")

    cbo["categoria_ocupacao"] = cbo["cbo_codigo"].str[0].map(CATEGORIA)
    cbo["chave_depara"] = cbo["cbo_codigo"].map(lambda c: buscar(c, dp))
    campos = ["area_codigo", "area_nome", "tipo_vinculo", "confianca"]
    cbo = cbo.join(dp[campos], on="chave_depara")
    cbo["area_nome"] = cbo["area_nome"].fillna("Sem área")

    saida = TRATADOS / "dCBO.csv"
    cbo.to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"{len(cbo)} ocupações, {cbo['area_codigo'].notna().sum()} com área. Salvo em {saida}")

    # Cobertura: quanto das admissões de formados o de-para alcança
    arq = TRATADOS / "fAdmissoes.csv"
    if not arq.exists():
        return
    adm = pd.read_csv(arq, dtype=str, usecols=["cbo2002ocupacao", "movimento", "nivel_instrucao", "peso"])
    adm = adm[(adm["movimento"] == "Admissão") & (adm["nivel_instrucao"] == "Superior completo ou mais")]
    adm["peso"] = adm["peso"].astype(int)
    rank = (adm.groupby("cbo2002ocupacao")["peso"].sum().rename("admissoes_superior")
            .reset_index().rename(columns={"cbo2002ocupacao": "cbo_codigo"})
            .merge(cbo, on="cbo_codigo", how="left")
            .sort_values("admissoes_superior", ascending=False))
    total = rank["admissoes_superior"].sum()
    rank["perc_acumulado"] = (rank["admissoes_superior"].cumsum() / total * 100).round(1)
    rank.to_csv(RAIZ / "docs" / "cobertura_depara.csv", index=False, encoding="utf-8-sig")

    print(f"\nAdmissões com superior completo ou mais: {total}")
    print("\nPor categoria da ocupação (%):")
    print((rank.groupby("categoria_ocupacao")["admissoes_superior"].sum() / total * 100).round(1).to_string())
    print("\nPor área CINE (%):")
    print((rank.groupby("area_nome")["admissoes_superior"].sum() / total * 100).round(1)
          .sort_values(ascending=False).to_string())
    fora = rank[rank["area_codigo"].isna() & rank["categoria_ocupacao"].isin(["Nível superior", "Técnico", "Dirigente"])]
    print("\nOcupações de nível superior, técnico ou dirigente ainda sem área (top 15):")
    print(fora.head(15)[["cbo_codigo", "cbo_descricao", "admissoes_superior"]].to_string(index=False))


if __name__ == "__main__":
    main()
