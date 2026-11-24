"""HU10 · Datos para el dashboard de Power BI (GPR-66: GPR-108, GPR-109, GPR-110).

Prepara un único Excel (``observatorio_powerbi.xlsx``) con las tablas que el informe de
Power BI necesita, ya calculadas y con los proveedores que son personas físicas
seudonimizados (HU7), de modo que el .pbix se pueda compartir.

Modelo (estrella; relaciones en docs/powerbi/guia_powerbi.md):

    Dimensiones: Universidad · Anio · Categoria · Proveedor
    Hechos:      Pagos (agregado por universidad, año, trimestre, unidad, categoría y proveedor)
                 Alertas (HU8) · ProveedoresComunes (HU6) · RankingCategorias (HU6)

Se usa Excel y no CSV porque Power BI lee los números de Excel sin depender de la
configuración regional (en CSV, la coma o el punto decimal dan problemas).

Uso:
    python -m observatorio.powerbi --entrada UP_UV_Final.csv --uv-crudos data --salida outputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .alertas import ORDEN_PRIORIDAD, UNIDAD_UV, detectar
from .proveedores_comunes import (
    TIPO_COMERCIAL,
    filtrar_comerciales,
    gasto_por_proveedor,
    ranking_categorias,
    resumen_comunes,
)
from .seudonimizacion import es_persona_fisica, obtener_sal, personas_desde_uv, seudonimo

SIN_CATEGORIA = "Sin categoría"


def seudonimizador(df: pd.DataFrame, sal: bytes, conocidas: frozenset = frozenset()):
    """Función PROVEEDOR_CLAVE -> nombre visible (seudónimo PER-… si es persona física)."""
    base = df.drop_duplicates("PROVEEDOR_CLAVE").set_index("PROVEEDOR_CLAVE")
    tiene_tipo = "TIPO_PROVEEDOR" in base.columns
    cache: dict = {}

    def visible(clave) -> str:
        if clave not in cache:
            nombre = base.at[clave, "Proveedor"] if clave in base.index else clave
            tipo = base.at[clave, "TIPO_PROVEEDOR"] if tiene_tipo and clave in base.index else None
            persona = es_persona_fisica(clave, tipo_proveedor=tipo, personas_conocidas=conocidas) or es_persona_fisica(
                nombre, tipo_proveedor=tipo, personas_conocidas=conocidas
            )
            cache[clave] = seudonimo(clave, sal) if persona else str(clave)
        return cache[clave]

    return visible


def construir_tablas(df: pd.DataFrame, sal: bytes, conocidas: frozenset = frozenset()) -> dict[str, pd.DataFrame]:
    visible = seudonimizador(df, sal, conocidas)
    d = df.copy()
    d["Proveedor_visible"] = d["PROVEEDOR_CLAVE"].map(visible)
    d["Unidad"] = np.where(d["UNIVERSIDAD"] == "UPV", d["CENTRO DIRECTIVO"], UNIDAD_UV)
    d["Categoria"] = d["GRUPO_GASTO"].fillna(SIN_CATEGORIA)
    if "Trimestre" in d.columns:  # texto homogéneo (T1…T4) para que Power BI no mezcle tipos
        t = pd.to_numeric(d["Trimestre"], errors="coerce")
        d["Trimestre"] = np.where(t.notna(), "T" + t.fillna(0).astype(int).astype(str),
                                  d["Trimestre"].fillna("Sin dato (UPV)").astype(str))
    else:
        d["Trimestre"] = "Sin dato"

    # Pagos: agregado, para KPIs, evolución y filtros
    pagos = (
        d.groupby(["UNIVERSIDAD", "AÑO", "Trimestre", "Unidad", "Categoria", "Proveedor_visible", "TIPO_PROVEEDOR"],
                  dropna=False)
        .agg(NumPagos=("Importe_num", "size"), Gasto=("Importe_num", "sum"))
        .reset_index()
        .rename(columns={"UNIVERSIDAD": "Universidad", "AÑO": "Anio", "Proveedor_visible": "Proveedor",
                         "TIPO_PROVEEDOR": "TipoProveedor"})
    )
    pagos["Gasto"] = pagos["Gasto"].round(2)

    # Alertas (HU8)
    al = detectar(df)
    alertas = pd.DataFrame(
        {
            "ID": al["ID"],
            "Prioridad": al["PRIORIDAD"],
            "OrdenPrioridad": al["PRIORIDAD"].map(ORDEN_PRIORIDAD) + 1,
            "Patron": al["PATRON"],
            "Universidad": al["UNIVERSIDAD"],
            "Anio": al["AÑO"].astype(int),
            "Unidad": al["UNIDAD"],
            "Proveedor": al["PROVEEDOR_CLAVE"].map(visible),
            "Categoria": al.get("CATEGORIA", pd.Series(index=al.index, dtype=object)).fillna(SIN_CATEGORIA),
            "TipoContrato": al["TIPO"],
            "NumPagos": al["N_PAGOS"].astype(int),
            "Importe": al["IMPORTE_TOTAL"],
            "Umbral": al["UMBRAL"],
            "VecesUmbral": al["VECES_UMBRAL"],
            "SuperaEnUnTrimestre": np.where(al["SUPERA_EN_UN_TRIMESTRE"], "Sí", "No"),
            "Motivo": al["MOTIVO"],
        }
    )

    # Proveedores comunes y ranking (HU6)
    com = filtrar_comerciales(df)
    por_prov = gasto_por_proveedor(com)
    c = por_prov[por_prov["COMUN"]].reset_index()
    comunes = pd.DataFrame(
        {
            "Proveedor": c["PROVEEDOR_CLAVE"].map(visible),
            "Categoria": c["CATEGORIA_PRINCIPAL"].fillna(SIN_CATEGORIA),
            "GastoUPV": c["GASTO_UPV"].round(2),
            "GastoUV": c["GASTO_UV"].round(2),
            "GastoTotal": c["GASTO_TOTAL"].round(2),
            "GastoSolapado": c["GASTO_SOLAPADO"].round(2),
            "PagosUPV": c["PAGOS_UPV"].astype(int),
            "PagosUV": c["PAGOS_UV"].astype(int),
            "Candidato": np.where(c["CANDIDATO"], "Sí", "No"),
        }
    ).sort_values("GastoSolapado", ascending=False)

    rk = ranking_categorias(com)
    ranking = pd.DataFrame(
        {
            "Ranking": rk["RANKING"],
            "Categoria": rk["GRUPO_GASTO"],
            "ProveedoresComunes": rk["PROVEEDORES_COMUNES"],
            "GastoUPV": rk["GASTO_UPV"].round(2),
            "GastoUV": rk["GASTO_UV"].round(2),
            "GastoSolapado": rk["GASTO_SOLAPADO"].round(2),
            "ConcentracionTop3": (rk["CONCENTRACION_TOP3_PCT"] / 100).round(3),
            "PrincipalesProveedores": rk["PRINCIPALES_PROVEEDORES"].map(
                lambda s: " · ".join(visible(x) for x in str(s).split(" · "))
            ),
        }
    )

    # Dimensiones
    universidades = pd.DataFrame(
        {"Universidad": ["UPV", "UV"],
         "Nombre": ["Universitat Politècnica de València", "Universitat de València"]}
    )
    anios = pd.DataFrame({"Anio": sorted(pagos["Anio"].dropna().astype(int).unique())})
    categorias = pd.DataFrame({"Categoria": sorted(set(pagos["Categoria"]) | set(alertas["Categoria"]))})
    categorias["SinClasificar"] = np.where(
        categorias["Categoria"].isin(["Suministros/servicios (sin detalle)", "Otros / sin clasificar", SIN_CATEGORIA]),
        "Sí", "No",
    )
    comunes_set = set(comunes["Proveedor"])
    candidatos = set(comunes.loc[comunes["Candidato"] == "Sí", "Proveedor"])
    prov = pagos.groupby("Proveedor").agg(TipoProveedor=("TipoProveedor", "first")).reset_index()
    prov["Comun"] = np.where(prov["Proveedor"].isin(comunes_set), "Sí", "No")
    prov["Candidato"] = np.where(prov["Proveedor"].isin(candidatos), "Sí", "No")
    prov["Seudonimizado"] = np.where(prov["Proveedor"].str.startswith("PER-"), "Sí", "No")
    prov["Comercial"] = np.where(prov["TipoProveedor"] == TIPO_COMERCIAL, "Sí", "No")

    return {
        "Universidad": universidades,
        "Anio": anios,
        "Categoria": categorias,
        "Proveedor": prov,
        "Pagos": pagos,
        "Alertas": alertas,
        "ProveedoresComunes": comunes,
        "RankingCategorias": ranking,
    }


def exportar_excel(tablas: dict[str, pd.DataFrame], ruta: Path) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta, engine="openpyxl") as xw:
        for nombre, t in tablas.items():
            t.to_excel(xw, sheet_name=nombre, index=False)
    return ruta


def comprobaciones(df: pd.DataFrame, tablas: dict[str, pd.DataFrame]) -> dict:
    """Cifras de control: lo que el informe de Power BI debe mostrar al abrirlo."""
    pagos, al, comunes = tablas["Pagos"], tablas["Alertas"], tablas["ProveedoresComunes"]
    rc = resumen_comunes(filtrar_comerciales(df), gasto_por_proveedor(filtrar_comerciales(df)))
    return {
        "pagos_total": int(pagos["NumPagos"].sum()),
        "gasto_total": round(float(pagos["Gasto"].sum()), 2),
        "gasto_total_original": round(float(df["Importe_num"].sum()), 2),
        "alertas": int(len(al)),
        "alertas_alta": int((al["Prioridad"] == "Alta").sum()),
        "proveedores_comunes": int(len(comunes)),
        "candidatos": int((comunes["Candidato"] == "Sí").sum()),
        "pct_gasto_UPV_en_comunes": rc["pct_gasto_UPV_en_comunes"],
        "pct_gasto_UV_en_comunes": rc["pct_gasto_UV_en_comunes"],
        "proveedores_seudonimizados": int((tablas["Proveedor"]["Seudonimizado"] == "Sí").sum()),
        "filas_por_tabla": {k: int(len(v)) for k, v in tablas.items()},
    }


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", required=True, help="UP_UV_Final.csv")
    p.add_argument("--uv-crudos", help="Carpeta con los XLS de la UV (mejora la detección de personas físicas)")
    p.add_argument("--salida", default="outputs")
    a = p.parse_args(argv)

    from .carga import leer_dataset_final

    df = leer_dataset_final(a.entrada)
    conocidas = personas_desde_uv(a.uv_crudos) if a.uv_crudos else frozenset()
    tablas = construir_tablas(df, obtener_sal(), conocidas)
    ruta = exportar_excel(tablas, Path(a.salida) / "observatorio_powerbi.xlsx")
    control = comprobaciones(df, tablas)
    (Path(a.salida) / "observatorio_powerbi_control.json").write_text(json.dumps(control, indent=2, ensure_ascii=False))
    print(f"Excel para Power BI en {ruta}")
    print(json.dumps(control, indent=2, ensure_ascii=False))
    return control


if __name__ == "__main__":
    main()
