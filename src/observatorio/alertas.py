"""HU8 · Alertas de posible fraccionamiento (GPR-62, GPR-63).

Regla (la misma del PMV presentado en la review del Sprint 1; reproduce sus 2.712 alertas):

- Solo proveedores de tipo "Empresa / persona física / otro".
- Se agrupan los pagos por universidad, año, unidad compradora, proveedor
  (``PROVEEDOR_CLAVE``) y tipo de contrato. En la UPV la unidad es el centro directivo;
  la UV no publica la unidad, así que allí se agrupa la universidad completa.
- Hay alerta si el grupo tiene al menos 2 pagos, **todos** por debajo del umbral del
  contrato menor (40.000 € en obras, 15.000 € en el resto) y **juntos lo superan**.

Patrón y prioridad (regla v2, documentada aquí; el PMV usaba una puntuación que no está en
el repositorio y estas reglas coinciden con su patrón en el 98,5 % de los casos):

- **Pocos pagos grandes**: al menos la mitad del importe está en pagos de 3.000 € o más
  y hay 20 pagos o menos. Es el patrón típico de un contrato partido.
    - **Alta** si la suma llega a 1,5 veces el umbral o, en la UV, si el umbral se
      supera dentro de un solo trimestre.
    - **Media** en otro caso.
- **Muchos pagos pequeños**: el resto. Suele ser gasto recurrente.
    - **Media** si la suma llega a 3 veces el umbral: candidato a contrato o acuerdo marco.
    - **Baja** en otro caso.

Una alerta es un indicio a revisar, no una acusación.

Uso:
    python -m observatorio.alertas --entrada UP_UV_Final.csv --salida outputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TIPO_COMERCIAL = "Empresa / persona física / otro"
UMBRAL_OBRAS = 40_000.0
UMBRAL_GENERAL = 15_000.0
PAGO_GRANDE = 3_000.0
UNIDAD_UV = "UV (universidad completa)"
ORDEN_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}
CLAVES = ["UNIVERSIDAD", "AÑO", "UNIDAD", "PROVEEDOR_CLAVE", "TIPO"]


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra proveedores comerciales y añade UNIDAD, TIPO y UMBRAL."""
    d = df[df["TIPO_PROVEEDOR"] == TIPO_COMERCIAL].copy() if "TIPO_PROVEEDOR" in df.columns else df.copy()
    d["UNIDAD"] = np.where(d["UNIVERSIDAD"] == "UPV", d["CENTRO DIRECTIVO"], UNIDAD_UV)
    d["TIPO"] = d["Tipo_Contrato_UV"].fillna("Sin tipo (UPV)") if "Tipo_Contrato_UV" in d.columns else "Sin tipo"
    d["UMBRAL"] = np.where(d["TIPO"] == "Obras", UMBRAL_OBRAS, UMBRAL_GENERAL)
    return d


def _clasificar(r) -> tuple[str, str]:
    pocos_grandes = r["PCT_PAGOS_GRANDES"] >= 0.5 and r["N_PAGOS"] <= 20
    if pocos_grandes:
        alta = r["VECES_UMBRAL"] >= 1.5 or bool(r["SUPERA_EN_UN_TRIMESTRE"])
        return "Pocos pagos grandes", "Alta" if alta else "Media"
    return "Muchos pagos pequeños", "Media" if r["VECES_UMBRAL"] >= 3 else "Baja"


def _motivo(r) -> str:
    def miles(v) -> str:
        return f"{v:,.0f}".replace(",", ".")

    veces = f"{r['VECES_UMBRAL']:.2f}".replace(".", ",")
    partes = [
        f"{r['N_PAGOS']} pagos en {r['AÑO']}, todos por debajo de {miles(r['UMBRAL'])} €, "
        f"que suman {miles(r['IMPORTE_TOTAL'])} € ({veces} veces el umbral)"
    ]
    if r["PATRON"] == "Pocos pagos grandes":
        partes.append(f"el {round(100 * r['PCT_PAGOS_GRANDES'])} % del importe está en pagos de 3.000 € o más")
    elif r["VECES_UMBRAL"] >= 3:
        partes.append("gasto recurrente: candidato a contrato o acuerdo marco")
    if r["SUPERA_EN_UN_TRIMESTRE"]:
        partes.append("más del umbral en un solo trimestre")
    return "; ".join(partes)


def detectar(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una fila por alerta, ordenadas por prioridad e importe."""
    d = preparar(df)
    d["_GRANDE"] = np.where(d["Importe_num"] >= PAGO_GRANDE, d["Importe_num"], 0.0)
    g = d.groupby(CLAVES, dropna=False).agg(
        N_PAGOS=("Importe_num", "size"),
        IMPORTE_TOTAL=("Importe_num", "sum"),
        PAGO_MAX=("Importe_num", "max"),
        UMBRAL=("UMBRAL", "max"),
        _GRANDE=("_GRANDE", "sum"),
    ).reset_index()
    g = g[(g["N_PAGOS"] >= 2) & (g["PAGO_MAX"] < g["UMBRAL"]) & (g["IMPORTE_TOTAL"] > g["UMBRAL"])].copy()
    g["VECES_UMBRAL"] = (g["IMPORTE_TOTAL"] / g["UMBRAL"]).round(2)
    g["PCT_PAGOS_GRANDES"] = (g["_GRANDE"] / g["IMPORTE_TOTAL"]).round(4)

    if "Trimestre" in d.columns and d["Trimestre"].notna().any():
        t = (
            d[d["Trimestre"].notna()].groupby(CLAVES + ["Trimestre"], dropna=False)["Importe_num"].sum()
            .groupby(level=list(range(len(CLAVES)))).max().rename("MAX_TRIMESTRE").reset_index()
        )
        g = g.merge(t, on=CLAVES, how="left")
        g["SUPERA_EN_UN_TRIMESTRE"] = g["MAX_TRIMESTRE"].fillna(0) > g["UMBRAL"]
    else:
        g["SUPERA_EN_UN_TRIMESTRE"] = False

    if "GRUPO_GASTO" in d.columns:
        cat = (
            d.groupby(CLAVES + ["GRUPO_GASTO"], dropna=False)["Importe_num"].sum().reset_index()
            .sort_values("Importe_num", ascending=False).drop_duplicates(CLAVES)[CLAVES + ["GRUPO_GASTO"]]
        )
        g = g.merge(cat, on=CLAVES, how="left").rename(columns={"GRUPO_GASTO": "CATEGORIA"})

    clas = g.apply(_clasificar, axis=1, result_type="expand")
    g["PATRON"], g["PRIORIDAD"] = clas[0], clas[1]
    g["MOTIVO"] = g.apply(_motivo, axis=1)
    g["_ORDEN"] = g["PRIORIDAD"].map(ORDEN_PRIORIDAD)
    g = g.sort_values(["_ORDEN", "IMPORTE_TOTAL"], ascending=[True, False]).reset_index(drop=True)
    g.insert(0, "ID", [f"A{i:04d}" for i in range(1, len(g) + 1)])
    g["IMPORTE_TOTAL"] = g["IMPORTE_TOTAL"].round(2)
    return g.drop(columns=["_GRANDE", "_ORDEN", "PAGO_MAX", "MAX_TRIMESTRE"], errors="ignore")


def resumen(alertas: pd.DataFrame) -> dict:
    por = lambda col: {str(k): int(v) for k, v in alertas[col].value_counts().items()}  # noqa: E731
    return {
        "alertas": int(len(alertas)),
        "por_universidad": por("UNIVERSIDAD"),
        "por_prioridad": por("PRIORIDAD"),
        "por_patron": por("PATRON"),
        "alta_por_universidad": {
            str(k): int(v) for k, v in alertas[alertas["PRIORIDAD"] == "Alta"]["UNIVERSIDAD"].value_counts().items()
        },
        "importe_en_alertas": round(float(alertas["IMPORTE_TOTAL"].sum()), 2),
    }


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", required=True, help="UP_UV_Final.csv")
    p.add_argument("--salida", default="outputs")
    a = p.parse_args(argv)

    from .carga import leer_dataset_final

    alertas = detectar(leer_dataset_final(a.entrada))
    res = resumen(alertas)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    alertas.to_csv(salida / "alertas_fraccionamiento.csv", sep=";", index=False, encoding="utf-8-sig")
    (salida / "alertas_resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
