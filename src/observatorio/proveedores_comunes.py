"""HU6 · Proveedores comunes UPV–UV y ranking de compra conjunta (GPR-56: GPR-57, GPR-58, GPR-59).

Parte del dataset unificado del equipo (``UP_UV_Final.csv``), en el que los nombres de
proveedor ya están normalizados y unificados (``PROVEEDOR_CLAVE``: nombre sin tildes,
signos ni forma societaria, fusión por NIF en la UV y fusiones revisadas a mano).

Definiciones:
- Solo cuentan los proveedores de tipo "Empresa / persona física / otro": universidades,
  entidades públicas y fundaciones suelen trabajar por convenio, no por compra.
- **Proveedor común**: tiene gasto en las dos universidades en 2019–2023.
- **Candidato a compra conjunta**: proveedor común con al menos ``UMBRAL_CANDIDATO``
  (50.000 €) en **cada** universidad.
- **Gasto solapado** de un proveedor: ``min(gasto UPV, gasto UV)``. Mide cuánto compran
  las dos a la vez y es más prudente que la suma, que premia a proveedores en los que
  casi todo el gasto es de una sola universidad.

Uso:
    python -m observatorio.proveedores_comunes --entrada UP_UV_Final.csv --salida outputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

TIPO_COMERCIAL = "Empresa / persona física / otro"
UMBRAL_CANDIDATO = 50_000.0
CATEGORIAS_SIN_CLASIFICAR = {"Suministros/servicios (sin detalle)", "Otros / sin clasificar"}


def filtrar_comerciales(df: pd.DataFrame) -> pd.DataFrame:
    if "TIPO_PROVEEDOR" not in df.columns:
        return df
    return df[df["TIPO_PROVEEDOR"] == TIPO_COMERCIAL]


def gasto_por_proveedor(df: pd.DataFrame, clave: str = "PROVEEDOR_CLAVE") -> pd.DataFrame:
    """Gasto, pagos y categoría principal por proveedor y universidad, en columnas."""
    g = df.groupby([clave, "UNIVERSIDAD"])["Importe_num"].agg(["sum", "size"]).unstack(fill_value=0)
    out = pd.DataFrame(index=g.index)
    for u in ("UPV", "UV"):
        out[f"GASTO_{u}"] = g[("sum", u)] if ("sum", u) in g.columns else 0.0
        out[f"PAGOS_{u}"] = g[("size", u)] if ("size", u) in g.columns else 0
    out["GASTO_TOTAL"] = out["GASTO_UPV"] + out["GASTO_UV"]
    out["GASTO_SOLAPADO"] = out[["GASTO_UPV", "GASTO_UV"]].min(axis=1)
    out["COMUN"] = (out["GASTO_UPV"] > 0) & (out["GASTO_UV"] > 0)
    out["CANDIDATO"] = (out["GASTO_UPV"] >= UMBRAL_CANDIDATO) & (out["GASTO_UV"] >= UMBRAL_CANDIDATO)

    if "GRUPO_GASTO" in df.columns:
        cat = (
            df.groupby([clave, "GRUPO_GASTO"])["Importe_num"].sum().reset_index()
            .sort_values([clave, "Importe_num"], ascending=[True, False])
            .drop_duplicates(clave).set_index(clave)["GRUPO_GASTO"]
        )
        out["CATEGORIA_PRINCIPAL"] = cat
    return out.sort_values("GASTO_SOLAPADO", ascending=False)


def resumen_comunes(df: pd.DataFrame, por_proveedor: pd.DataFrame) -> dict:
    total = df.groupby("UNIVERSIDAD")["Importe_num"].sum()
    comunes = por_proveedor[por_proveedor["COMUN"]]
    cand = por_proveedor[por_proveedor["CANDIDATO"]]
    return {
        "proveedores_UPV": int((por_proveedor["GASTO_UPV"] > 0).sum()),
        "proveedores_UV": int((por_proveedor["GASTO_UV"] > 0).sum()),
        "proveedores_comunes": int(len(comunes)),
        "pct_gasto_UPV_en_comunes": round(100 * comunes["GASTO_UPV"].sum() / total.get("UPV", 1), 1),
        "pct_gasto_UV_en_comunes": round(100 * comunes["GASTO_UV"].sum() / total.get("UV", 1), 1),
        "gasto_comunes_total": round(float(comunes["GASTO_TOTAL"].sum()), 2),
        "candidatos_compra_conjunta": int(len(cand)),
        "gasto_candidatos_total": round(float(cand["GASTO_TOTAL"].sum()), 2),
        "gasto_candidatos_solapado": round(float(cand["GASTO_SOLAPADO"].sum()), 2),
    }


def ranking_categorias(df: pd.DataFrame, clave: str = "PROVEEDOR_CLAVE") -> pd.DataFrame:
    """GPR-59 · Oportunidades por categoría de gasto.

    Dentro de cada categoría, un proveedor es común si las dos universidades le compran
    algo de esa categoría. Se ordena por gasto solapado.
    """
    g = df.groupby(["GRUPO_GASTO", clave, "UNIVERSIDAD"])["Importe_num"].sum().unstack(fill_value=0)
    for u in ("UPV", "UV"):
        if u not in g.columns:
            g[u] = 0.0
    g["SOLAPADO"] = g[["UPV", "UV"]].min(axis=1)
    comunes = g[(g["UPV"] > 0) & (g["UV"] > 0)].reset_index()

    def top3(grupo):
        t = grupo.sort_values("SOLAPADO", ascending=False).head(3)
        return " · ".join(t[clave])

    r = comunes.groupby("GRUPO_GASTO").agg(
        PROVEEDORES_COMUNES=(clave, "nunique"),
        GASTO_UPV=("UPV", "sum"),
        GASTO_UV=("UV", "sum"),
        GASTO_SOLAPADO=("SOLAPADO", "sum"),
    )
    r["GASTO_COMPARTIDO"] = r["GASTO_UPV"] + r["GASTO_UV"]
    r["PRINCIPALES_PROVEEDORES"] = comunes.groupby("GRUPO_GASTO").apply(top3, include_groups=False)
    # Concentración: parte del gasto solapado que se llevan los 3 primeros proveedores
    top3_solapado = comunes.sort_values("SOLAPADO", ascending=False).groupby("GRUPO_GASTO").head(3)
    r["CONCENTRACION_TOP3_PCT"] = (
        100 * top3_solapado.groupby("GRUPO_GASTO")["SOLAPADO"].sum() / r["GASTO_SOLAPADO"]
    ).round(1)
    r["CLASIFICADA"] = ~r.index.isin(CATEGORIAS_SIN_CLASIFICAR)
    r = r.sort_values("GASTO_SOLAPADO", ascending=False)
    r.insert(0, "RANKING", range(1, len(r) + 1))
    return r.reset_index()


def muestra_validacion(
    df: pd.DataFrame, n: int = 50, semilla: int = 2026, clave: str = "PROVEEDOR_CLAVE"
) -> pd.DataFrame:
    """GPR-58 · Muestra de emparejamientos UPV–UV para revisar a mano.

    Toma proveedores comunes cuyo nombre publicado difiere entre universidades (los casos
    en que la unificación ha hecho algo) y deja una columna CORRECTO_SN para marcar.
    Excluye personas físicas, porque el fichero se sube al repositorio.
    """
    base = df.copy()
    if "ES_PERSONA_FISICA" not in base.columns:
        from .seudonimizacion import es_persona_fisica

        base["ES_PERSONA_FISICA"] = [
            es_persona_fisica(a) or es_persona_fisica(b)
            for a, b in zip(base["Proveedor"], base[clave])
        ]
    base = base[~base["ES_PERSONA_FISICA"].astype(bool)]
    nombres = base.groupby([clave, "UNIVERSIDAD"])["Proveedor"].agg(lambda s: s.value_counts().index[0]).unstack()
    gasto = base.groupby([clave, "UNIVERSIDAD"])["Importe_num"].sum().unstack(fill_value=0)
    pares = nombres.dropna().join(gasto, rsuffix="_GASTO")
    pares = pares[pares["UPV"].str.upper() != pares["UV"].str.upper()]
    m = pares.sample(n=min(n, len(pares)), random_state=semilla).reset_index()
    out = pd.DataFrame(
        {
            "CLAVE_UNIFICADA": m[clave],
            "NOMBRE_EN_UPV": m["UPV"],
            "NOMBRE_EN_UV": m["UV"],
            "GASTO_UPV": m["UPV_GASTO"].round(2),
            "GASTO_UV": m["UV_GASTO"].round(2),
            "CORRECTO_SN": "",
            "REVISADO_POR": "",
            "COMENTARIO": "",
        }
    )
    return out.sort_values("CLAVE_UNIFICADA").reset_index(drop=True)


def precision_validacion(revisado: pd.DataFrame) -> dict:
    """Lee la muestra ya marcada (CORRECTO_SN = S/N) y calcula la precisión del emparejamiento."""
    marca = revisado["CORRECTO_SN"].astype(str).str.strip().str.upper().str[:1]
    hechos = marca.isin(["S", "N"])
    n = int(hechos.sum())
    correctos = int((marca == "S").sum())
    return {"revisados": n, "correctos": correctos, "precision": round(correctos / n, 3) if n else None}


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", required=True, help="UP_UV_Final.csv")
    p.add_argument("--salida", default="outputs")
    p.add_argument("--clave", default="PROVEEDOR_CLAVE", choices=["PROVEEDOR_CLAVE", "GRUPO_EMPRESARIAL"])
    a = p.parse_args(argv)

    from .carga import leer_dataset_final

    df = filtrar_comerciales(leer_dataset_final(a.entrada))
    por_prov = gasto_por_proveedor(df, a.clave)
    res = resumen_comunes(df, por_prov)
    cats = ranking_categorias(df, a.clave)

    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    por_prov[por_prov["COMUN"]].to_csv(salida / "proveedores_comunes.csv", sep=";", encoding="utf-8-sig")
    por_prov[por_prov["CANDIDATO"]].to_csv(salida / "candidatos_compra_conjunta.csv", sep=";", encoding="utf-8-sig")
    cats.to_csv(salida / "ranking_categorias_compra_conjunta.csv", sep=";", index=False, encoding="utf-8-sig")
    muestra_validacion(df, clave=a.clave).to_csv(
        salida / "validacion_emparejamientos_muestra50.csv", sep=";", index=False, encoding="utf-8-sig"
    )
    (salida / "proveedores_comunes_resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
