"""Tests de HU8 (GPR-63): regla de fraccionamiento, patrón y prioridad, con casos construidos a mano."""

import pandas as pd
import pytest

from observatorio.alertas import UNIDAD_UV, detectar, resumen

EMP = "Empresa / persona física / otro"


def pagos(uni, anio, centro, prov, importes, tipo=None, trimestres=None, tipo_prov=EMP, grupo="Laboratorio e investigación"):
    filas = []
    for i, imp in enumerate(importes):
        filas.append(
            {
                "UNIVERSIDAD": uni,
                "AÑO": anio,
                "CENTRO DIRECTIVO": centro if uni == "UPV" else None,
                "PROVEEDOR_CLAVE": prov,
                "Proveedor": prov,
                "Tipo_Contrato_UV": tipo if uni == "UV" else None,
                "Trimestre": (trimestres[i] if trimestres else None) if uni == "UV" else None,
                "TIPO_PROVEEDOR": tipo_prov,
                "GRUPO_GASTO": grupo,
                "Importe_num": float(imp),
            }
        )
    return filas


@pytest.fixture(scope="module")
def alertas():
    filas = []
    # A) UPV: 3 pagos grandes que suman 27.000 (1,8 × 15.000) -> Pocos pagos grandes, Alta
    filas += pagos("UPV", 2022, "INFRAESTRUCTURAS", "OBRAS SUR", [9000, 9000, 9000])
    # B) UPV: 2 pagos de 8.000 = 16.000 (1,07 ×) -> Pocos pagos grandes, Media
    filas += pagos("UPV", 2022, "INFRAESTRUCTURAS", "PINTURAS NORTE", [8000, 8000])
    # C) UPV: un pago supera el umbral -> sin alerta (no es fraccionamiento)
    filas += pagos("UPV", 2022, "INFRAESTRUCTURAS", "GRAN CONTRATO", [16000, 2000])
    # D) UPV: mismo proveedor en dos centros que solo juntos superan el umbral -> sin alerta
    filas += pagos("UPV", 2021, "CENTRO A", "PAPELERIA", [8000])
    filas += pagos("UPV", 2021, "CENTRO B", "PAPELERIA", [8000])
    # E) UPV: 60 pagos de 800 = 48.000 (3,2 ×) -> Muchos pagos pequeños, Media
    filas += pagos("UPV", 2023, "GESTIÓN DE LA INVESTIGACIÓN", "REACTIVOS SA", [800] * 60)
    # F) UPV: 25 pagos de 700 = 17.500 (1,17 ×) -> Muchos pagos pequeños, Baja
    filas += pagos("UPV", 2023, "GESTIÓN DE LA INVESTIGACIÓN", "TONER YA", [700] * 25)
    # G) UV obras: 3 × 14.000 = 42.000 > 40.000 -> alerta con umbral de obras; los 3 en el T2 -> Alta
    filas += pagos("UV", 2020, None, "CONSTRUCCIONES ESTE", [14000, 14000, 14000], tipo="Obras", trimestres=["T2"] * 3)
    # H) UV suministros: 2 × 8.000 en trimestres distintos (1,07 ×) -> Media
    filas += pagos("UV", 2020, None, "MOBILIARIO OESTE", [8000, 8000], tipo="Suministros", trimestres=["T1", "T3"])
    # I) UV suministros: los mismos 2 × 8.000 en el mismo trimestre -> Alta
    filas += pagos("UV", 2021, None, "MOBILIARIO OESTE", [8000, 8000], tipo="Suministros", trimestres=["T1", "T1"])
    # J) Otra universidad como proveedor (convenio) -> excluida
    filas += pagos("UV", 2020, None, "UNIVERSITAT POLITECNICA", [9000, 9000], tipo="Servicios", tipo_prov="Universidad")
    return detectar(pd.DataFrame(filas)).set_index("PROVEEDOR_CLAVE", append=True)


def fila(alertas, prov, anio=None):
    a = alertas.xs(prov, level="PROVEEDOR_CLAVE")
    if anio is not None:
        a = a[a["AÑO"] == anio]
    assert len(a) == 1, f"{prov}: se esperaba una alerta"
    return a.iloc[0]


def proveedores(alertas):
    return set(alertas.index.get_level_values("PROVEEDOR_CLAVE"))


def test_casos_con_alerta(alertas):
    assert proveedores(alertas) == {
        "OBRAS SUR",
        "PINTURAS NORTE",
        "REACTIVOS SA",
        "TONER YA",
        "CONSTRUCCIONES ESTE",
        "MOBILIARIO OESTE",
    }
    assert len(alertas) == 7  # MOBILIARIO OESTE en 2020 y en 2021


def test_un_pago_por_encima_del_umbral_no_es_fraccionamiento(alertas):
    assert "GRAN CONTRATO" not in proveedores(alertas)


def test_centros_distintos_no_se_suman(alertas):
    assert "PAPELERIA" not in proveedores(alertas)


def test_excluye_entidades_no_comerciales(alertas):
    assert "UNIVERSITAT POLITECNICA" not in proveedores(alertas)


def test_pocos_pagos_grandes(alertas):
    a = fila(alertas, "OBRAS SUR")
    assert (a["PATRON"], a["PRIORIDAD"]) == ("Pocos pagos grandes", "Alta")
    assert a["VECES_UMBRAL"] == 1.8 and a["N_PAGOS"] == 3
    b = fila(alertas, "PINTURAS NORTE")
    assert (b["PATRON"], b["PRIORIDAD"]) == ("Pocos pagos grandes", "Media")


def test_muchos_pagos_pequenos(alertas):
    e = fila(alertas, "REACTIVOS SA")
    assert (e["PATRON"], e["PRIORIDAD"]) == ("Muchos pagos pequeños", "Media")
    assert "acuerdo marco" in e["MOTIVO"]
    f = fila(alertas, "TONER YA")
    assert (f["PATRON"], f["PRIORIDAD"]) == ("Muchos pagos pequeños", "Baja")


def test_obras_usan_umbral_de_40000(alertas):
    g = fila(alertas, "CONSTRUCCIONES ESTE")
    assert g["UMBRAL"] == 40000 and g["UNIDAD"] == UNIDAD_UV
    assert g["VECES_UMBRAL"] == 1.05
    assert g["PRIORIDAD"] == "Alta" and g["SUPERA_EN_UN_TRIMESTRE"]


def test_mismo_trimestre_sube_la_prioridad(alertas):
    assert fila(alertas, "MOBILIARIO OESTE", 2020)["PRIORIDAD"] == "Media"
    assert fila(alertas, "MOBILIARIO OESTE", 2021)["PRIORIDAD"] == "Alta"


def test_orden_e_ids(alertas):
    prios = alertas["PRIORIDAD"].tolist()
    assert prios == sorted(prios, key={"Alta": 0, "Media": 1, "Baja": 2}.get)
    assert alertas["ID"].iloc[0] == "A0001"
    assert alertas["CATEGORIA"].eq("Laboratorio e investigación").all()


def test_resumen(alertas):
    r = resumen(alertas.reset_index(level="PROVEEDOR_CLAVE"))
    assert r["alertas"] == 7
    assert r["por_prioridad"] == {"Alta": 3, "Media": 3, "Baja": 1}
