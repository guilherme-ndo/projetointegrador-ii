"""
01 - Dimensão município.

Busca os códigos oficiais dos municípios de SP na API de localidades do IBGE
e gera dados_tratados/dMunicipio.csv com código de 7 dígitos (INEP e IBGE)
e 6 dígitos (CAGED e RAIS).

Uso: python scripts/01_dim_municipio.py
"""
import pandas as pd
import requests

from utils import MUNICIPIOS_RECORTE, TRATADOS, normalizar

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios"


def main():
    print("Consultando API do IBGE...")
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    todos = pd.DataFrame(
        [{"cod_ibge_7": m["id"], "nome": m["nome"]} for m in resp.json()]
    )

    alvo = {normalizar(n) for n in MUNICIPIOS_RECORTE}
    todos["chave"] = todos["nome"].map(normalizar)
    dim = todos[todos["chave"].isin(alvo)].drop(columns="chave").copy()

    faltando = alvo - set(dim["nome"].map(normalizar))
    if faltando:
        raise ValueError(f"Municípios não encontrados no IBGE: {faltando}")

    dim["cod_ibge_6"] = dim["cod_ibge_7"] // 10  # tira o dígito verificador
    dim["uf"] = "SP"
    dim = dim[["cod_ibge_7", "cod_ibge_6", "nome", "uf"]].sort_values("nome")

    saida = TRATADOS / "dMunicipio.csv"
    dim.to_csv(saida, index=False, encoding="utf-8-sig")
    print(dim.to_string(index=False))
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    main()
