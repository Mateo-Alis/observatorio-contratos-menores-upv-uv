"""HU3 · Agregación de las líneas de la UPV por expediente (GPR-45, GPR-46).

La UPV publica una fila por línea de gasto. El campo EXPEDIENTE tiene la forma
``<expediente>/<línea>`` (p. ej. ``PV000301547/386522``): la parte anterior a la barra
identifica el expediente y la posterior, la línea. Unas pocas filas (≈0,1 %) no llevan
barra: son expedientes de una sola línea.

Comprobado sobre 2019–2023: dentro de un mismo expediente el proveedor, el centro y el
año son siempre los mismos; solo el concepto económico puede variar (546 expedientes).
Además, las 19.739 filas que repiten proveedor, concepto, importe, centro y año tienen
EXPEDIENTE distinto: son pagos distintos, no duplicados.

Uso:
    python -m observatorio.expedientes --datos data --salida outputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .carga import leer_upv_carpeta

CLAVES_CONSTANTES = ["TERCERO", "CENTRO DIRECTIVO", "AÑO"]


def separar_expediente(valor: str) -> tuple[str, str | None]:
    """Devuelve (expediente, línea) a partir del campo EXPEDIENTE publicado.

    >>> separar_expediente("PV000301547/386522")
    ('PV000301547', '386522')
    >>> separar_expediente("073824")
    ('073824', None)
    """
    texto = str(valor).strip()
    if "/" in texto:
        expediente, linea = texto.split("/", 1)
        return expediente.strip(), linea.strip()
    return texto, None


def anadir_expediente(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas EXPEDIENTE_ID y LINEA_ID a las líneas de la UPV."""
    partes = df["EXPEDIENTE"].map(separar_expediente)
    out = df.copy()
    out["EXPEDIENTE_ID"] = partes.str[0]
    out["LINEA_ID"] = partes.str[1]
    return out


def comprobar_consistencia(lineas: pd.DataFrame) -> pd.DataFrame:
    """Devuelve los expedientes con más de un proveedor, centro o año (debería estar vacío)."""
    n = lineas.groupby("EXPEDIENTE_ID")[CLAVES_CONSTANTES].nunique()
    return n[(n > 1).any(axis=1)]


def agregar_por_expediente(lineas: pd.DataFrame) -> pd.DataFrame:
    """Una fila por expediente con su importe total, número de líneas y conceptos.

    Lanza ValueError si algún expediente mezcla proveedores, centros o años.
    """
    if "EXPEDIENTE_ID" not in lineas.columns:
        lineas = anadir_expediente(lineas)
    inconsistentes = comprobar_consistencia(lineas)
    if len(inconsistentes):
        raise ValueError(
            f"{len(inconsistentes)} expedientes mezclan proveedor, centro o año: "
            f"{list(inconsistentes.index[:5])}"
        )

    por_concepto = (
        lineas.groupby(["EXPEDIENTE_ID", "CONCEPTO ECONÓMICO"], dropna=False)["IMPORTE_NUM"]
        .sum()
        .reset_index()
        .sort_values(["EXPEDIENTE_ID", "IMPORTE_NUM"], ascending=[True, False])
    )
    principal = por_concepto.drop_duplicates("EXPEDIENTE_ID").set_index("EXPEDIENTE_ID")[
        "CONCEPTO ECONÓMICO"
    ]

    agg = lineas.groupby("EXPEDIENTE_ID").agg(
        AÑO=("AÑO", "first"),
        TERCERO=("TERCERO", "first"),
        CENTRO_DIRECTIVO=("CENTRO DIRECTIVO", "first"),
        N_LINEAS=("EXPEDIENTE", "size"),
        IMPORTE_TOTAL=("IMPORTE_NUM", "sum"),
        IMPORTE_MAX_LINEA=("IMPORTE_NUM", "max"),
        N_CONCEPTOS=("CONCEPTO ECONÓMICO", "nunique"),
        CONCEPTOS=("CONCEPTO ECONÓMICO", lambda s: " | ".join(sorted(s.dropna().unique()))),
    )
    agg["CONCEPTO_PRINCIPAL"] = principal
    agg["IMPORTE_TOTAL"] = agg["IMPORTE_TOTAL"].round(2)
    return agg.reset_index().sort_values(["AÑO", "EXPEDIENTE_ID"]).reset_index(drop=True)


def resumen(lineas: pd.DataFrame, expedientes: pd.DataFrame) -> dict:
    """Cifras clave de la agregación, para el informe y la sprint review."""
    contenido = ["TERCERO", "CONCEPTO ECONÓMICO", "IMPORTE", "CENTRO DIRECTIVO", "AÑO"]
    return {
        "lineas": int(len(lineas)),
        "expedientes": int(len(expedientes)),
        "expedientes_multilinea": int((expedientes["N_LINEAS"] > 1).sum()),
        "lineas_en_expedientes_multilinea": int(
            expedientes.loc[expedientes["N_LINEAS"] > 1, "N_LINEAS"].sum()
        ),
        "max_lineas_por_expediente": int(expedientes["N_LINEAS"].max()),
        "expedientes_con_varios_conceptos": int((expedientes["N_CONCEPTOS"] > 1).sum()),
        "filas_iguales_salvo_expediente": int(lineas.duplicated(contenido).sum()),
        "importe_total_lineas": round(float(lineas["IMPORTE_NUM"].sum()), 2),
        "importe_total_expedientes": round(float(expedientes["IMPORTE_TOTAL"].sum()), 2),
        "expedientes_que_superan_15000": int((expedientes["IMPORTE_TOTAL"] >= 15000).sum()),
    }


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datos", default="data", help="Carpeta con los *_UPV.csv")
    p.add_argument("--salida", default="outputs", help="Carpeta de salida")
    a = p.parse_args(argv)

    lineas = anadir_expediente(leer_upv_carpeta(a.datos))
    expedientes = agregar_por_expediente(lineas)
    res = resumen(lineas, expedientes)

    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    expedientes.to_csv(salida / "upv_expedientes.csv", sep=";", index=False, encoding="utf-8-sig")
    lineas.to_csv(salida / "upv_lineas_con_expediente.csv", sep=";", index=False, encoding="utf-8-sig")
    (salida / "upv_expedientes_resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
