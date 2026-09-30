"""
03 - Novo CAGED (MTE), movimentações mensais.

Antes de rodar:
  1. Baixe os microdados no portal PDET (Microdados RAIS e CAGED > Novo CAGED).
     Cada mês vem em .7z: CAGEDMOV (movimentações no prazo),
     CAGEDFOR (declaradas fora do prazo) e CAGEDEXC (exclusões).
  2. Coloque os .7z ou os .txt já extraídos em dados_brutos/caged/.
     Comece com UM mês para testar.

O script extrai .7z (se houver), lê em blocos, filtra os municípios do
recorte e junta tudo.

Saída: dados_tratados/fAdmissoes.csv
Uso:   python scripts/03_caged.py
       python scripts/03_caged.py --tipos MOV FOR    (inclui fora do prazo)
"""
import argparse

import pandas as pd

from utils import BRUTOS, TRATADOS, carregar_municipios, normalizar

PASTA = BRUTOS / "caged"

# Nomes já normalizados (sem acento, minúsculos). Confira no dicionário do PDET.
COLUNAS = [
    "competenciamov", "municipio", "secao", "subclasse",
    "saldomovimentacao", "cbo2002ocupacao", "graudeinstrucao",
    "idade", "sexo", "salario", "tipomovimentacao",
]


def extrair_7z():
    arquivos = list(PASTA.glob("*.7z"))
    if not arquivos:
        return
    try:
        import py7zr
    except ImportError:
        raise ImportError("Instale py7zr (pip install py7zr) ou extraia os .7z manualmente.")
    for arq in arquivos:
        destino = arq.with_suffix(".txt")
        if destino.exists() or any(PASTA.glob(arq.stem + "*.txt")):
            continue
        print(f"Extraindo {arq.name}...")
        with py7zr.SevenZipFile(arq, "r") as z:
            z.extractall(PASTA)


def ler_mes(arq, codigos, encoding="utf-8"):
    pedacos = []
    leitor = pd.read_csv(arq, sep=";", dtype=str, chunksize=500_000, encoding=encoding)
    for bloco in leitor:
        bloco.columns = [normalizar(c) for c in bloco.columns]
        bloco = bloco[pd.to_numeric(bloco["municipio"], errors="coerce").isin(codigos)]
        pedacos.append(bloco[[c for c in COLUNAS if c in bloco.columns]])
    return pd.concat(pedacos, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tipos", nargs="+", default=["MOV"],
                        help="MOV, FOR e/ou EXC (padrão: MOV)")
    args = parser.parse_args()

    PASTA.mkdir(parents=True, exist_ok=True)
    extrair_7z()

    codigos = set(carregar_municipios()["cod_ibge_6"])
    arquivos = sorted(
        p for p in PASTA.glob("*.txt")
        if any(p.name.upper().startswith("CAGED" + t) for t in args.tipos)
    )
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo CAGED {args.tipos} em {PASTA}")

    partes = []
    for arq in arquivos:
        try:
            df = ler_mes(arq, codigos)
        except UnicodeDecodeError:
            print(f"  {arq.name}: encoding não é UTF-8, tentando latin-1")
            df = ler_mes(arq, codigos, encoding="latin-1")
        df["arquivo_origem"] = arq.stem
        print(f"{arq.name}: {len(df)} movimentações no recorte")
        partes.append(df)

    df = pd.concat(partes, ignore_index=True)

    # Tipos e colunas derivadas para o Power BI
    df["municipio"] = df["municipio"].astype(int)
    df["saldomovimentacao"] = pd.to_numeric(df["saldomovimentacao"], errors="coerce")
    df["salario"] = pd.to_numeric(df["salario"].str.replace(",", "."), errors="coerce")
    df["ano"] = df["competenciamov"].str[:4].astype(int)
    df["mes"] = df["competenciamov"].str[4:6].astype(int)
    df["movimento"] = df["saldomovimentacao"].map({1: "Admissão", -1: "Desligamento"})
    df["cbo2002ocupacao"] = df["cbo2002ocupacao"].str.zfill(6)
    for n in (4, 3, 2, 1):  # chaves para a busca em cascata do de-para
        df[f"cbo_{n}"] = df["cbo2002ocupacao"].str[:n]

    saida = TRATADOS / "fAdmissoes.csv"
    df.to_csv(saida, index=False, encoding="utf-8-sig")

    print("\nSaldo por ano:")
    print(df.groupby(["ano", "movimento"]).size().unstack(fill_value=0).to_string())
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    main()
