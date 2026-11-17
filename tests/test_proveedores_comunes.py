"""Tests de HU6 (GPR-57, GPR-58, GPR-59) con un dataset pequeño construido a mano."""

import pandas as pd
import pytest

from observatorio.proveedores_comunes import (
    filtrar_comerciales,
    gasto_por_proveedor,
    muestra_validacion,
    precision_validacion,
    ranking_categorias,
    resumen_comunes,
)

EMP = "Empresa / persona física / otro"


@pytest.fixture
def df():
    filas = [
        # UNIVERSIDAD, Proveedor, CLAVE, TIPO, GRUPO_GASTO, importe
        ("UPV", "MERCK LIFE SCIENCE SLU", "MERCK LIFE SCIENCE", EMP, "Laboratorio", 60000),
        ("UV", "MERCK LIFE SCIENCE, S.L.U.", "MERCK LIFE SCIENCE", EMP, "Laboratorio", 90000),
        ("UPV", "SCHARLAB SL", "SCHARLAB", EMP, "Laboratorio", 40000),
        ("UV", "SCHARLAB, S.L.", "SCHARLAB", EMP, "Laboratorio", 1000),
        ("UPV", "K-TUIN SL", "K TUIN", EMP, "Informática", 70000),
        ("UV", "K TUIN SISTEMAS", "K TUIN", EMP, "Informática", 55000),
        ("UPV", "SOLO UPV SL", "SOLO UPV", EMP, "Informática", 500000),
        ("UV", "UNIVERSITAT DE VALENCIA", "UNIVERSITAT DE VALENCIA", "Universidad", "Otros", 9000),
        ("UPV", "UNIVERSITAT DE VALENCIA", "UNIVERSITAT DE VALENCIA", "Universidad", "Otros", 9000),
        ("UPV", "PEREZ SOLER ANTONIO", "PEREZ SOLER ANTONIO", EMP, "Informática", 10),
        ("UV", "PEREZ SOLER, ANTONIO", "PEREZ SOLER ANTONIO", EMP, "Informática", 10),
    ]
    return pd.DataFrame(
        filas, columns=["UNIVERSIDAD", "Proveedor", "PROVEEDOR_CLAVE", "TIPO_PROVEEDOR", "GRUPO_GASTO", "Importe_num"]
    )


def test_excluye_no_comerciales(df):
    assert "UNIVERSITAT DE VALENCIA" not in set(filtrar_comerciales(df)["PROVEEDOR_CLAVE"])


def test_gasto_por_proveedor(df):
    p = gasto_por_proveedor(filtrar_comerciales(df))
    assert p.loc["MERCK LIFE SCIENCE", "GASTO_SOLAPADO"] == 60000
    assert p.loc["MERCK LIFE SCIENCE", "CANDIDATO"]
    assert p.loc["K TUIN", "CANDIDATO"]
    assert p.loc["SCHARLAB", "COMUN"] and not p.loc["SCHARLAB", "CANDIDATO"]  # UV < 50.000 €
    assert not p.loc["SOLO UPV", "COMUN"]
    # Ordenado por gasto solapado: MERCK (60.000) y después K TUIN (55.000)
    assert list(p.index[:2]) == ["MERCK LIFE SCIENCE", "K TUIN"]


def test_resumen(df):
    c = filtrar_comerciales(df)
    r = resumen_comunes(c, gasto_por_proveedor(c))
    assert r["proveedores_comunes"] == 4
    assert r["candidatos_compra_conjunta"] == 2
    # UPV comercial: 60.000 + 40.000 + 70.000 + 500.000 + 10 ; en comunes: 170.010
    assert r["pct_gasto_UPV_en_comunes"] == round(100 * 170010 / 670010, 1)


def test_ranking_categorias(df):
    r = ranking_categorias(filtrar_comerciales(df)).set_index("GRUPO_GASTO")
    assert r.loc["Laboratorio", "RANKING"] == 1  # solapado 60.000 + 1.000
    assert r.loc["Laboratorio", "GASTO_SOLAPADO"] == 61000
    assert r.loc["Laboratorio", "PROVEEDORES_COMUNES"] == 2
    assert r.loc["Informática", "GASTO_SOLAPADO"] == 55010
    assert r.loc["Laboratorio", "PRINCIPALES_PROVEEDORES"].startswith("MERCK LIFE SCIENCE")


def test_muestra_validacion_sin_personas(df):
    m = muestra_validacion(filtrar_comerciales(df), n=50)
    assert "PEREZ SOLER ANTONIO" not in set(m["CLAVE_UNIFICADA"])
    assert set(m["CLAVE_UNIFICADA"]) == {"MERCK LIFE SCIENCE", "SCHARLAB", "K TUIN"}
    assert (m["CORRECTO_SN"] == "").all()


def test_precision_validacion():
    rev = pd.DataFrame({"CORRECTO_SN": ["S", "s", "N", "", "Sí"]})
    assert precision_validacion(rev) == {"revisados": 4, "correctos": 3, "precision": 0.75}
