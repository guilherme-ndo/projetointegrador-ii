"""
Figuras do relato técnico do PI2, geradas a partir de dados_tratados/.

Rode depois de scripts/indicadores.py e scripts/07_detalhe.py.
Saída: relatorio/figuras/figura_N.png
Uso:   python relatorio/figuras.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from utils import TRATADOS, ler_admissoes, ler_oferta  # noqa: E402

SAIDA = RAIZ / "relatorio" / "figuras"
SAIDA.mkdir(exist_ok=True)

# Destaque em azul escuro e o resto em cinzas (impressão em preto e branco continua legível)
DESTAQUE, CINZA, CINZA_CLARO, TEXTO, GRADE = "#1F3A5F", "#7F7F7F", "#BFBFBF", "#262626", "#E5E5E5"
SUP, MED = "Superior completo ou mais", "Médio completo"
AREAS = {"04": "Negócios e direito", "06": "Computação e TIC", "07": "Engenharia", "10": "Serviços"}

plt.rcParams.update({
    "font.family": "Arial", "font.size": 10, "text.color": TEXTO, "axes.labelcolor": TEXTO,
    "xtick.color": TEXTO, "ytick.color": TEXTO, "axes.edgecolor": CINZA_CLARO,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 12, "axes.titleweight": "bold",
})


def br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def salvar(fig, n):
    fig.tight_layout()
    fig.savefig(SAIDA / f"figura_{n}.png", dpi=200)
    plt.close(fig)


def grade_y(ax):
    ax.yaxis.grid(True, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def linhas(ax, df, estilos, fmt, deslocar=None):
    """Uma linha por coluna, com o rótulo e o último valor escritos no fim da linha.

    deslocar: {coluna: pontos} para afastar rótulos que se encostam.
    """
    for col, (cor, tracejado, espessura) in estilos.items():
        s = df[col].dropna()
        ax.plot(s.index, s.values, color=cor, linestyle=tracejado, linewidth=espessura, marker="o", markersize=4)
        ax.annotate(f"{col}: {fmt(s.iloc[-1])}", (s.index[-1], s.iloc[-1]), xytext=(8, (deslocar or {}).get(col, 0)),
                    textcoords="offset points", va="center", fontsize=9, color=TEXTO)
    ax.set_xticks(df.index)
    ax.set_xlim(df.index.min() - 0.2, df.index.max() + 1.6)
    grade_y(ax)


def fig1_concluintes_area():
    of = ler_oferta()
    df = (of[of["CO_CINE_AREA_GERAL"].isin(AREAS)]
          .pivot_table(index="NU_ANO_CENSO", columns="CO_CINE_AREA_GERAL", values="QT_CONC", aggfunc="sum")
          .rename(columns=AREAS))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    linhas(ax, df, {"Negócios e direito": (CINZA, "--", 1.6), "Computação e TIC": (DESTAQUE, "-", 2.4),
                    "Engenharia": (CINZA, "-", 1.6), "Serviços": (CINZA_CLARO, ":", 1.6)}, br,
           {"Computação e TIC": 7, "Negócios e direito": -7})
    ax.set_ylim(0, 450)
    ax.set_title("Concluintes das Fatecs por área", loc="left")
    salvar(fig, 1)


def fig2_ocupacoes():
    cbo = pd.read_csv(TRATADOS / "dCBO.csv", dtype=str)
    adm = ler_admissoes(["ano", "cbo2002ocupacao", "nivel_instrucao", "peso"]).astype({"cbo2002ocupacao": str})
    adm = adm[(adm["ano"] == 2024) & (adm["nivel_instrucao"] == SUP)]
    adm = adm.merge(cbo, left_on="cbo2002ocupacao", right_on="cbo_codigo")
    adm = adm[adm["categoria_ocupacao"].isin(["Nível superior", "Técnico", "Dirigente"])]
    top = adm.groupby("cbo_descricao")["peso"].sum().sort_values().tail(10)
    area = adm.drop_duplicates("cbo_descricao").set_index("cbo_descricao")["area_codigo"]
    nomes = [n.replace("(A)", "").replace("Negocios", "Negócios").replace("Logistica", "Logística").strip()
             for n in top.index]
    cores = [DESTAQUE if area[n] == "06" else CINZA_CLARO for n in top.index]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.barh(nomes, top.values, color=cores, height=0.65)
    for i, v in enumerate(top.values):
        ax.text(v + 60, i, br(v), va="center", fontsize=9)
    ax.set_xlim(0, top.max() * 1.15)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_title("Admissões de formados por ocupação (2024)", loc="left")
    ax.text(0, -0.13, "Em azul: ocupações de Computação e TIC. Só cargos de nível superior, técnico ou dirigente.",
            transform=ax.transAxes, fontsize=8, color=CINZA)
    salvar(fig, 2)


def fig3_indice_2024():
    area = pd.read_csv(TRATADOS / "indicadores_area_ano.csv", dtype={"area_codigo": str})
    s = (area[(area["ano"] == 2024)].dropna(subset=["indice_descompasso"])
         .set_index("area_codigo")["indice_descompasso"].rename(AREAS).sort_values())
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.barh(s.index, s.values, color=[DESTAQUE if n == "Computação e TIC" else CINZA_CLARO for n in s.index],
            height=0.6)
    for i, v in enumerate(s.values):
        ax.text(v + 0.6, i, br(v, 1), va="center", fontsize=10)
    ax.set_xlim(0, 50)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_title("Admissões de formados por concluinte das Fatecs (2024)", loc="left")
    salvar(fig, 3)


def fig4_indice_evolucao():
    area = pd.read_csv(TRATADOS / "indicadores_area_ano.csv", dtype={"area_codigo": str})
    df = (area[area["area_codigo"].isin(["04", "06", "07"])]
          .pivot_table(index="ano", columns="area_codigo", values="indice_descompasso").rename(columns=AREAS))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    linhas(ax, df, {"Negócios e direito": (CINZA, "--", 1.6), "Computação e TIC": (DESTAQUE, "-", 2.4),
                    "Engenharia": (CINZA, "-", 1.6)}, lambda v: br(v, 1))
    ax.set_ylim(0, 60)
    ax.set_title("Índice de descompasso por área", loc="left")
    salvar(fig, 4)


def fig5_salarios():
    ind = pd.read_csv(TRATADOS / "indicadores_ano.csv").set_index("ano")
    df = ind[["salario_mediano_superior", "salario_mediano_medio"]].rename(
        columns={"salario_mediano_superior": "Superior", "salario_mediano_medio": "Médio"})
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    linhas(ax, df, {"Superior": (DESTAQUE, "-", 2.4), "Médio": (CINZA, "--", 1.6)}, lambda v: f"R$ {br(v)}")
    for ano, p in ind["premio_salarial"].items():
        ax.text(ano, df.loc[ano, "Superior"] + 180, f"{br(p, 1)}x", ha="center", fontsize=8, color=CINZA)
    ax.set_ylim(0, 5000)
    ax.yaxis.set_major_formatter(lambda v, _: f"R$ {br(v)}")
    ax.set_title("Salário mediano de admissão por escolaridade", loc="left")
    salvar(fig, 5)


def fig6_sobrequalificacao():
    ind = pd.read_csv(TRATADOS / "indicadores_ano.csv").set_index("ano")
    df = (ind[["sobrequalificacao", "sobrequalificacao_estoque"]] * 100).rename(
        columns={"sobrequalificacao": "Admissões (CAGED)", "sobrequalificacao_estoque": "Estoque (RAIS)"})
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    linhas(ax, df, {"Admissões (CAGED)": (DESTAQUE, "-", 2.4), "Estoque (RAIS)": (CINZA, "--", 1.6)},
           lambda v: f"{br(v)}%")
    ax.set_ylim(0, 45)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title("Formados em vagas de nível médio", loc="left")
    salvar(fig, 6)


def fig7_municipios():
    det = pd.read_csv(TRATADOS / "detalhe_municipio.csv")
    det = det[det["municipio"] != "Região (8 municípios)"].set_index("municipio")
    det = det.sort_values("part_admissoes_superior_regiao")
    y = range(len(det))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.barh([i + 0.2 for i in y], det["part_admissoes_superior_regiao"] * 100, height=0.38, color=DESTAQUE,
            label="Admissões de formados")
    ax.barh([i - 0.2 for i in y], det["part_concluintes_regiao"] * 100, height=0.38, color=CINZA_CLARO,
            label="Concluintes das Fatecs")
    for i, (a, c) in enumerate(zip(det["part_admissoes_superior_regiao"], det["part_concluintes_regiao"])):
        ax.text(a * 100 + 1, i + 0.2, f"{a * 100:.0f}%", va="center", fontsize=8)
        ax.text(c * 100 + 1, i - 0.2, f"{c * 100:.0f}%", va="center", fontsize=8, color=CINZA)
    ax.set_yticks(list(y), det.index)
    ax.set_xlim(0, 75)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("Participação de cada município na região (2024)", loc="left")
    salvar(fig, 7)


def fig8_moradores():
    mun = pd.read_csv(TRATADOS / "indicadores_municipio.csv").set_index("nome")
    s = (mun["part_superior_25mais"] * 100).sort_values()
    regiao = "Região (8 municípios)"
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.barh(s.index, s.values, color=[CINZA if n == regiao else DESTAQUE if n == "Santana de Parnaíba"
                                      else CINZA_CLARO for n in s.index], height=0.65)
    for i, v in enumerate(s.values):
        ax.text(v + 0.4, i, f"{br(v)}%", va="center", fontsize=9)
    ax.set_xlim(0, 38)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_title("Moradores de 25 anos ou mais com superior completo", loc="left")
    salvar(fig, 8)


if __name__ == "__main__":
    for f in (fig1_concluintes_area, fig2_ocupacoes, fig3_indice_2024, fig4_indice_evolucao, fig5_salarios,
              fig6_sobrequalificacao, fig7_municipios, fig8_moradores):
        f()
    print(f"Figuras salvas em {SAIDA}")
