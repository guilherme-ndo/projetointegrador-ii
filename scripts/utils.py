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
