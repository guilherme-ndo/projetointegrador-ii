"""
02 - Censo da Educação Superior (INEP), arquivo de CURSOS.

Antes de rodar:
  1. Baixe os microdados em gov.br/inep > Dados abertos > Microdados >
     Censo da Educação Superior (um .zip por ano).
  2. Extraia e copie o arquivo de cursos (nome parecido com
     MICRODADOS_CADASTRO_CURSOS_2023.CSV) para dados_brutos/inep/.
  3. Pode colocar vários anos na pasta; o script junta todos.

Saída: dados_tratados/fOfertaEnsino.csv
Uso:   python scripts/02_censo_superior.py
"""
import pandas as pd

from utils import BRUTOS, TRATADOS, carregar_municipios

PASTA = BRUTOS / "inep"

# Colunas desejadas. As que não existirem em algum ano são ignoradas;
# confira os nomes no dicionário de dados de cada ano.
COLUNAS = [
    "NU_ANO_CENSO", "CO_MUNICIPIO", "NO_MUNICIPIO",
    "CO_IES", "TP_REDE", "TP_CATEGORIA_ADMINISTRATIVA",
    "TP_MODALIDADE_ENSINO", "TP_GRAU_ACADEMICO",
    "CO_CURSO", "NO_CURSO",
    "CO_CINE_AREA_GERAL", "NO_CINE_AREA_GERAL",
    "CO_CINE_ROTULO", "NO_CINE_ROTULO",
    "QT_VG_TOTAL", "QT_ING", "QT_MAT", "QT_CONC",
]


def ler_arquivo(arq, codigos):
    pedacos = []
    leitor = pd.read_csv(
        arq, sep=";", encoding="latin-1", dtype=str,
        usecols=lambda c: c in COLUNAS, chunksize=200_000,
    )
    for bloco in leitor:
        bloco = bloco[pd.to_numeric(bloco["CO_MUNICIPIO"], errors="coerce").isin(codigos)]
        pedacos.append(bloco)
    return pd.concat(pedacos, ignore_index=True)


def main():
    arquivos = sorted(
        p for p in PASTA.glob("*") if p.suffix.lower() == ".csv" and "CURSO" in p.name.upper()
    )
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de cursos em {PASTA}")

    codigos = set(carregar_municipios()["cod_ibge_7"])
    partes = []
    for arq in arquivos:
        print(f"Lendo {arq.name}...")
        df = ler_arquivo(arq, codigos)
        print(f"  {len(df)} cursos nos municípios do recorte")
        partes.append(df)

    df = pd.concat(partes, ignore_index=True)

    # Tipos e padronizações para o Power BI
    df["CO_MUNICIPIO"] = df["CO_MUNICIPIO"].astype(int)
    if "CO_CINE_AREA_GERAL" in df:
        df["CO_CINE_AREA_GERAL"] = df["CO_CINE_AREA_GERAL"].str.zfill(2)  # '6' -> '06', igual ao de-para
    for col in ["QT_VG_TOTAL", "QT_ING", "QT_MAT", "QT_CONC"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Rótulos legíveis (confirmar códigos no dicionário de dados)
    if "TP_REDE" in df:
        df["rede"] = df["TP_REDE"].map({"1": "Pública", "2": "Privada"})
    if "TP_MODALIDADE_ENSINO" in df:
        df["modalidade"] = df["TP_MODALIDADE_ENSINO"].map({"1": "Presencial", "2": "EaD"})

    saida = TRATADOS / "fOfertaEnsino.csv"
    df.to_csv(saida, index=False, encoding="utf-8-sig")

    print("\nResumo por ano:")
    agg = {c: "sum" for c in ["QT_ING", "QT_MAT", "QT_CONC"] if c in df}
    print(df.groupby("NU_ANO_CENSO").agg(agg).to_string())
    if "NO_CINE_AREA_GERAL" in df:
        print("\nConcluintes por área (todos os anos):")
        print(df.groupby("NO_CINE_AREA_GERAL")["QT_CONC"].sum().sort_values(ascending=False).to_string())
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    main()
