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

Exclusões (EXC) cancelam movimentações declaradas antes. Pela metodologia do
PDET, saldo = MOV + FOR - EXC. Por isso cada linha recebe a coluna "peso"
(+1 para MOV/FOR, -1 para EXC). No Power BI, conte admissões com SUM(peso),
não com COUNTROWS.

Saída: dados_tratados/fAdmissoes.csv
Uso:   python scripts/03_caged.py
       python scripts/03_caged.py --tipos MOV FOR EXC    (série completa)
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
    "horascontratuais", "indtrabintermitente", "indtrabparcial",
    "unidadesalariocodigo",
]

# Grau de instrução do Novo CAGED agrupado em níveis (confirmar no dicionário)
NIVEL_INSTRUCAO = {
    **{c: "Abaixo do médio" for c in range(1, 7)},
    7: "Médio completo",
    8: "Superior incompleto",
    9: "Superior completo ou mais",
    10: "Superior completo ou mais",  # mestrado
    11: "Superior completo ou mais",  # doutorado
    80: "Superior completo ou mais",  # pós-graduação completa
}

UNIDADE_MENSAL = 5  # unidadesalariocodigo = mês (confirmar no dicionário)


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
    parser.add_argument("--tipos", nargs="+", default=["MOV"], choices=["MOV", "FOR", "EXC"],
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
        df["peso"] = -1 if arq.name.upper().startswith("CAGEDEXC") else 1
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

    # Nível de instrução agrupado (base da dEscolaridade e do prêmio salarial)
    grau = pd.to_numeric(df["graudeinstrucao"], errors="coerce")
    df["nivel_instrucao"] = grau.map(NIVEL_INSTRUCAO).fillna("Não identificado")

    # Salário comparável: mensal, sem intermitente e positivo.
    # Use só as linhas com salario_comparavel = True no prêmio salarial.
    comparavel = df["salario"] > 0
    if "unidadesalariocodigo" in df:
        comparavel &= pd.to_numeric(df["unidadesalariocodigo"], errors="coerce") == UNIDADE_MENSAL
    if "indtrabintermitente" in df:
        comparavel &= pd.to_numeric(df["indtrabintermitente"], errors="coerce") != 1
    df["salario_comparavel"] = comparavel

    saida = TRATADOS / "fAdmissoes.csv"
    df.to_csv(saida, index=False, encoding="utf-8-sig")

    print("\nMovimentações por ano (soma de peso, já descontadas as exclusões):")
    print(df.pivot_table(index="ano", columns="movimento", values="peso",
                         aggfunc="sum", fill_value=0).to_string())
    print(f"\nSalário comparável em {df['salario_comparavel'].mean():.1%} das linhas")
    tamanho_mb = saida.stat().st_size / 1e6
    print(f"\nSalvo em {saida} ({tamanho_mb:.0f} MB)")
    if tamanho_mb > 100:
        print("Atenção: arquivo acima de 100 MB, não versionar (já está no .gitignore).")


if __name__ == "__main__":
    main()
