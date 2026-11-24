"""Tests de HU10 (GPR-109): tablas para Power BI, cuadre de cifras y seudonimización."""

import pandas as pd
import pytest

from observatorio.powerbi import construir_tablas, exportar_excel

SAL = b"sal-de-prueba"
EMP = "Empresa / persona física / otro"


def fila(uni, anio, prov, imp, centro="CENTRO A", grupo="Laboratorio e investigación", tipo_prov=EMP, trimestre=None):
    return {
        "UNIVERSIDAD": uni,
        "AÑO": anio,
        "CENTRO DIRECTIVO": centro if uni == "UPV" else None,
        "PROVEEDOR_CLAVE": prov,
        "Proveedor": prov,
        "Tipo_Contrato_UV": "Suministros" if uni == "UV" else None,
        "Trimestre": trimestre if uni == "UV" else None,
        "TIPO_PROVEEDOR": tipo_prov,
        "GRUPO_GASTO": grupo,
        "Importe_num": float(imp),
    }


@pytest.fixture(scope="module")
def datos():
    filas = []
    # Proveedor común con mucho gasto en las dos -> candidato a compra conjunta
    filas += [fila("UPV", 2022, "REACTIVOS SA", 9000) for _ in range(8)]
    filas += [fila("UV", 2022, "REACTIVOS SA", 9000, trimestre="T1") for _ in range(8)]
    # Persona física común (debe salir seudonimizada en todas las tablas)
    filas += [fila("UPV", 2021, "PEREZ SOLER ANTONIO", 8000, grupo="Informática") for _ in range(2)]
    filas += [fila("UV", 2021, "PEREZ SOLER ANTONIO", 500, grupo="Informática", trimestre="T2")]
    # Solo en una universidad y sin categoría
    filas += [fila("UPV", 2020, "PAPELERIA CENTRO", 300, grupo=None)]
    # Entidad no comercial: cuenta en el gasto, no en alertas ni comunes
    filas += [fila("UV", 2020, "UNIVERSITAT POLITECNICA", 9000, tipo_prov="Universidad", trimestre="T3") for _ in range(2)]
    df = pd.DataFrame(filas)
    return df, construir_tablas(df, SAL)


def test_tablas_del_modelo(datos):
    _, t = datos
    assert set(t) == {"Universidad", "Anio", "Categoria", "Proveedor", "Pagos", "Alertas",
                      "ProveedoresComunes", "RankingCategorias"}


def test_cuadra_gasto_y_pagos(datos):
    df, t = datos
    assert t["Pagos"]["NumPagos"].sum() == len(df)
    assert t["Pagos"]["Gasto"].sum() == pytest.approx(df["Importe_num"].sum())


def test_ningun_nombre_de_persona_fisica(datos):
    _, t = datos
    for nombre, tabla in t.items():
        texto = tabla.astype(str).apply(" ".join, axis=1).str.cat(sep=" ")
        assert "PEREZ" not in texto, f"Nombre de persona física en la tabla {nombre}"
    seud = t["Proveedor"].set_index("Proveedor")["Seudonimizado"]
    assert seud.filter(like="PER-").eq("Sí").all() and len(seud.filter(like="PER-")) == 1


def test_claves_de_relacion_existen_en_las_dimensiones(datos):
    _, t = datos
    for hecho in ["Pagos", "Alertas", "ProveedoresComunes"]:
        assert set(t[hecho]["Proveedor"]) <= set(t["Proveedor"]["Proveedor"])
        assert set(t[hecho]["Categoria"]) <= set(t["Categoria"]["Categoria"])
    for hecho in ["Pagos", "Alertas"]:
        assert set(t[hecho]["Universidad"]) <= set(t["Universidad"]["Universidad"])
        assert set(t[hecho]["Anio"]) <= set(t["Anio"]["Anio"])
    assert t["Proveedor"]["Proveedor"].is_unique and t["Categoria"]["Categoria"].is_unique


def test_alertas_y_comunes(datos):
    _, t = datos
    al = t["Alertas"]
    assert len(al) == 3  # REACTIVOS SA en UPV y UV, la persona física en UPV
    assert al["Proveedor"].str.startswith("PER-").sum() == 1
    assert "UNIVERSITAT POLITECNICA" not in set(al["Proveedor"])
    com = t["ProveedoresComunes"].set_index("Proveedor")
    assert len(com) == 2
    assert com.loc["REACTIVOS SA", "Candidato"] == "Sí"
    assert com.loc["REACTIVOS SA", "GastoSolapado"] == 72000
    prov = t["Proveedor"].set_index("Proveedor")
    assert prov.loc["PAPELERIA CENTRO", "Comun"] == "No"
    assert prov.loc["UNIVERSITAT POLITECNICA", "Comercial"] == "No"
    assert "Sin categoría" in set(t["Categoria"]["Categoria"])


def test_exporta_excel_con_una_hoja_por_tabla(datos, tmp_path):
    _, t = datos
    ruta = exportar_excel(t, tmp_path / "pbi.xlsx")
    hojas = pd.read_excel(ruta, sheet_name=None)
    assert set(hojas) == set(t)
    assert len(hojas["Alertas"]) == len(t["Alertas"])
