"""
05 - RAIS (MTE), estoque de vínculos formais em 31/12.

Antes de rodar:
  1. Baixe no FTP do PDET (ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/<ano>/)
     o arquivo RAIS_VINC_PUB_SP.7z de cada ano (cerca de 1 GB cada).
  2. Salve em dados_brutos/rais/ com o ano no nome: RAIS_VINC_PUB_SP_2024.7z.

O script extrai cada ano (o arquivo de texto, com extensão .COMT, passa de
6 GB), lê em blocos, fica só com os vínculos ativos em 31/12 nos municípios
do recorte e apaga o arquivo extraído no fim (use --manter-txt para guardar).

Saídas:
  dados_tratados/fEstoqueEmprego.csv  vínculos agregados por ano, município,
                                      ocupação (CBO) e grau de instrução,
                                      com soma de remuneração para médias
  dados_tratados/rais_mediana_ano.csv remuneração mediana de dezembro por ano
                                      e nível de instrução (região toda)

Uso: python scripts/05_rais.py [--anos 2023 2024] [--manter-txt]
"""
import argparse
import re

import pandas as pd

from utils import BRUTOS, NIVEL_INSTRUCAO, TRATADOS, carregar_municipios, normalizar

PASTA = BRUTOS / "rais"

# Nome da coluna (normalizado, só letras e números) -> nome usado aqui.
# Confira no layout do PDET se algum ano mudar o cabeçalho.
# Até 2022 o cabeçalho é curto ("Município"); de 2023 em diante vem com " - Código".
CANDIDATAS = {
    "municipio": ["municipio", "municipiocodigo"],
    "cbo": ["cboocupacao2002", "cbo2002ocupacaocodigo"],
    "grau": ["escolaridadeapos2005", "escolaridadeapos2005codigo"],
    "ativo": ["vinculoativo3112", "indvinculoativo3112codigo"],
    "rem_dez": ["vlremundezembronom", "vlremdezembronom"],
    "intermitente": ["indtrabintermitente", "indtrabalhointermitentecodigo"],
}


def chave(coluna):
    return re.sub(r"[^a-z0-9]", "", normalizar(coluna))


def mapear_colunas(cabecalho):
    presentes = {chave(c): c for c in cabecalho}
    mapa = {}
    for nome, opcoes in CANDIDATAS.items():
        achada = next((presentes[o] for o in opcoes if o in presentes), None)
        if achada is None and nome != "intermitente":
            raise KeyError(f"Coluna '{nome}' não encontrada. Cabeçalho: {list(presentes)}")
        if achada is not None:
            mapa[achada] = nome
    return mapa


def extrair(arq_7z, destino):
    import py7zr

    destino.mkdir(exist_ok=True)
    with py7zr.SevenZipFile(arq_7z, "r") as z:
        nomes = [i.filename for i in z.list() if not i.is_directory]
        z.extract(destino, targets=nomes)
    return [destino / n for n in nomes]


def num(serie, decimal):
    if decimal == ",":
        serie = serie.str.replace(",", ".", regex=False)
    return pd.to_numeric(serie.str.strip(), errors="coerce")


def ler_ano(arq_txt, codigos):
    # O separador mudou entre os anos: ";" com decimal "," ou "," com decimal "."
    with open(arq_txt, encoding="latin-1") as f:
        primeira = f.readline()
    sep = ";" if primeira.count(";") > primeira.count(",") else ","
    decimal = "," if sep == ";" else "."
    cabecalho = pd.read_csv(arq_txt, sep=sep, encoding="latin-1", nrows=0).columns
    mapa = mapear_colunas(cabecalho)
    pedacos = []
    leitor = pd.read_csv(arq_txt, sep=sep, encoding="latin-1", dtype=str, usecols=list(mapa),
                         chunksize=1_000_000)
    for bloco in leitor:
        bloco = bloco.rename(columns=mapa)
        bloco = bloco[pd.to_numeric(bloco["municipio"], errors="coerce").isin(codigos)
                      & (pd.to_numeric(bloco["ativo"], errors="coerce") == 1)]
        out = pd.DataFrame({
            "municipio": pd.to_numeric(bloco["municipio"]).astype("int32"),
            "cbo2002ocupacao": bloco["cbo"].str.strip().str.zfill(6),
            "graudeinstrucao": pd.to_numeric(bloco["grau"], errors="coerce").astype("Int16"),
            "rem_dez": num(bloco["rem_dez"], decimal).astype("float32"),
        })
        interm = (pd.to_numeric(bloco["intermitente"], errors="coerce") == 1) if "intermitente" in bloco else False
        out["rem_valida"] = (out["rem_dez"] > 0) & ~interm
        pedacos.append(out)
    return pd.concat(pedacos, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anos", nargs="+", type=int, help="anos a processar (padrão: todos os .7z da pasta)")
    parser.add_argument("--manter-txt", action="store_true", help="não apagar o .txt extraído")
    args = parser.parse_args()

    arquivos = sorted(PASTA.glob("RAIS_VINC_PUB_SP_*.7z"))
    if args.anos:
        arquivos = [a for a in arquivos if int(a.stem[-4:]) in args.anos]
    if not arquivos:
        raise FileNotFoundError(f"Nenhum RAIS_VINC_PUB_SP_<ano>.7z em {PASTA}")

    codigos = set(carregar_municipios()["cod_ibge_6"])
    agregados, medianas = [], []
    for arq in arquivos:
        ano = int(arq.stem[-4:])
        pasta_ano = PASTA / str(ano)
        txts = [f for f in pasta_ano.iterdir() if f.is_file()] if pasta_ano.exists() else []
        if not txts:
            print(f"Extraindo {arq.name}...")
            txts = extrair(arq, pasta_ano)
        df = pd.concat([ler_ano(t, codigos) for t in txts], ignore_index=True)
        df["nivel_instrucao"] = df["graudeinstrucao"].map(NIVEL_INSTRUCAO).fillna("Não identificado")
        print(f"{ano}: {len(df)} vínculos ativos em 31/12 no recorte")

        df["rem_soma"] = df["rem_dez"].where(df["rem_valida"], 0.0)
        ag = (df.groupby(["municipio", "cbo2002ocupacao", "graudeinstrucao", "nivel_instrucao"], dropna=False)
              .agg(vinculos=("rem_dez", "size"), rem_validos=("rem_valida", "sum"), rem_soma=("rem_soma", "sum"))
              .reset_index())
        ag.insert(0, "ano", ano)
        agregados.append(ag)
        med = (df[df["rem_valida"]].groupby("nivel_instrucao")["rem_dez"]
               .agg(rem_mediana="median", n="size").reset_index())
        med.insert(0, "ano", ano)
        medianas.append(med)

        if not args.manter_txt:
            for t in txts:
                t.unlink()

    novo = pd.concat(agregados, ignore_index=True)
    novo_med = pd.concat(medianas, ignore_index=True)
    # Junta com anos já processados antes (permite rodar um ano por vez)
    saida, saida_med = TRATADOS / "fEstoqueEmprego.csv", TRATADOS / "rais_mediana_ano.csv"
    anos = set(novo["ano"])
    if saida.exists():
        antigo = pd.read_csv(saida, dtype={"cbo2002ocupacao": str})
        novo = pd.concat([antigo[~antigo["ano"].isin(anos)], novo], ignore_index=True)
    if saida_med.exists():
        antigo = pd.read_csv(saida_med)
        novo_med = pd.concat([antigo[~antigo["ano"].isin(anos)], novo_med], ignore_index=True)
    novo = novo.sort_values(["ano", "municipio", "cbo2002ocupacao", "graudeinstrucao"])
    novo.to_csv(saida, index=False, encoding="utf-8-sig")
    novo_med.sort_values(["ano", "nivel_instrucao"]).to_csv(saida_med, index=False, encoding="utf-8-sig")

    print("\nVínculos ativos em 31/12 por ano e nível:")
    print(novo.pivot_table(index="ano", columns="nivel_instrucao", values="vinculos", aggfunc="sum").to_string())
    print("\nRemuneração mediana de dezembro (R$):")
    print(novo_med.pivot_table(index="ano", columns="nivel_instrucao", values="rem_mediana").round(0).to_string())
    print(f"\nSalvo em {saida} ({saida.stat().st_size / 1e6:.0f} MB) e {saida_med}")


if __name__ == "__main__":
    main()
