"""Funções e caminhos compartilhados pelos scripts do projeto."""
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados_brutos"
TRATADOS = RAIZ / "dados_tratados"
TRATADOS.mkdir(exist_ok=True)

# Municípios do recorte (nomes como aparecem no IBGE)
MUNICIPIOS_RECORTE = [
    "Santana de Parnaíba",
    "Barueri",
    "Osasco",
    "Carapicuíba",
    "Cajamar",
    "Itapevi",
    "Jandira",
    "Pirapora do Bom Jesus",
]

# Início do recorte temporal (o Novo CAGED começa em jan/2020)
ANO_INICIAL = 2020

# Grau de instrução agrupado em níveis. Mesmos códigos no Novo CAGED e na RAIS
# (a RAIS não tem o 80). Conferido nos layouts do PDET.
NIVEL_INSTRUCAO = {
    **{c: "Abaixo do médio" for c in range(1, 7)},
    7: "Médio completo",
    8: "Superior incompleto",
    9: "Superior completo ou mais",
    10: "Superior completo ou mais",  # mestrado
    11: "Superior completo ou mais",  # doutorado
    80: "Superior completo ou mais",  # pós-graduação completa (só no CAGED)
}


def normalizar(texto: str) -> str:
    """Remove acentos, espaços e deixa minúsculo. Ex.: 'Competênciamov ' -> 'competenciamov'."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower().replace(" ", "")


def carregar_municipios():
    """Lê dMunicipio.csv gerado pelo script 01. Retorna o DataFrame."""
    import pandas as pd

    arq = TRATADOS / "dMunicipio.csv"
    if not arq.exists():
        raise FileNotFoundError("Rode primeiro: python scripts/01_dim_municipio.py")
    return pd.read_csv(arq, dtype={"cod_ibge_7": int, "cod_ibge_6": int})
