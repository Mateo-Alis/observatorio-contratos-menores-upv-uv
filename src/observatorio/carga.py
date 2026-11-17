"""Lectura de los ficheros de entrada.

- Los CSV de contratos menores de la UPV (uno por año, separador ';', codificación
  latin-1, importes con coma decimal y punto de miles).
- El dataset unificado UPV + UV del equipo (``UP_UV_Final.csv``, rama DATASET_FINAL).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

COLUMNAS_UPV = ["EXPEDIENTE", "TERCERO", "CONCEPTO ECONÓMICO", "IMPORTE", "CENTRO DIRECTIVO"]


def importe_a_numero(valor) -> float:
    """Convierte un importe publicado ('1.088,52', ' 83,77   ', '363') a float.

    Devuelve NaN si el valor está vacío o no es un número.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("€", "").replace(" ", "")
    if not texto:
        return float("nan")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


def anio_de_fichero(ruta: str | Path) -> int:
    """Año del fichero a partir de los 4 primeros dígitos de su nombre."""
    m = re.match(r"(\d{4})", Path(ruta).name)
    if not m:
        raise ValueError(f"El nombre del fichero no empieza por un año: {ruta}")
    return int(m.group(1))


def leer_upv(ruta: str | Path) -> pd.DataFrame:
    """Lee un CSV anual de la UPV y devuelve las columnas normalizadas más AÑO e IMPORTE_NUM."""
    df = pd.read_csv(ruta, sep=";", encoding="latin-1", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    faltan = [c for c in COLUMNAS_UPV if c not in df.columns]
    if faltan:
        raise ValueError(f"{ruta}: faltan columnas {faltan}")
    df = df[COLUMNAS_UPV].copy()
    for c in COLUMNAS_UPV:
        df[c] = df[c].str.strip()
    df["AÑO"] = anio_de_fichero(ruta)
    df["IMPORTE_NUM"] = df["IMPORTE"].map(importe_a_numero)
    return df


def leer_upv_carpeta(carpeta: str | Path) -> pd.DataFrame:
    """Lee y apila todos los ``*UPV.csv`` de una carpeta, en orden de año."""
    rutas = sorted(Path(carpeta).glob("*UPV.csv"))
    if not rutas:
        raise FileNotFoundError(f"No hay ficheros *UPV.csv en {carpeta}")
    return pd.concat([leer_upv(r) for r in rutas], ignore_index=True)


def leer_dataset_final(ruta: str | Path) -> pd.DataFrame:
    """Lee el dataset unificado UPV + UV (``UP_UV_Final.csv``)."""
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    if "Importe_num" not in df.columns:
        df["Importe_num"] = df["Importe"].map(importe_a_numero)
    return df
