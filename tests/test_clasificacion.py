"""Tests de HU4 (GPR-53): clasificador por reglas del objeto y del concepto económico."""

import pandas as pd
import pytest

from observatorio.clasificacion import (
    OBRAS,
    SIN_CLASIFICAR,
    SIN_DETALLE,
    clasificar,
    cobertura,
    mayus,
)


def uv(objeto, tipo="Suministros"):
    return {"UNIVERSIDAD": "UV", "CONCEPTO ECONÓMICO": None, "Objeto_UV": objeto, "Tipo_Contrato_UV": tipo,
            "Importe_num": 100.0}


def upv(concepto):
    return {"UNIVERSIDAD": "UPV", "CONCEPTO ECONÓMICO": concepto, "Objeto_UV": None, "Tipo_Contrato_UV": None,
            "Importe_num": 100.0}


def grupo(filas, version=1):
    return clasificar(pd.DataFrame(filas), version)["GRUPO_GASTO"].tolist()


def test_mayus():
    assert mayus("Adquisición de Ácido") == "ADQUISICION DE ACIDO"
    assert mayus(None) == "" and mayus("") == ""


@pytest.mark.parametrize(
    "concepto, esperado",
    [
        ("MATERIAL INFORMÁTICO NO INVENTARIABLE", "Equipos y material informático"),
        ("APLICACIONES INFORMÁTICAS", "Software y licencias"),  # la regla de software va antes que la de informática
        ("REPARACIÓN Y CONSERVACIÓN DE EDIFICIOS", "Mantenimiento y reparación"),  # gana la primera regla
        ("MATERIAL DE LABORATORIO", "Laboratorio e investigación"),
        ("LIMPIEZA Y ASEO", "Limpieza"),
        ("CONCEPTO DESCONOCIDO", SIN_CLASIFICAR),
    ],
)
def test_upv_por_concepto(concepto, esperado):
    assert grupo([upv(concepto)]) == [esperado]


def test_uv_por_objeto_y_tipo():
    assert grupo(
        [
            uv("Compra de reactivos y puntas de pipeta"),
            uv("Ordenador portátil para el grupo"),
            uv("Reforma del aula 3", tipo="Obras"),
            uv("Compra de 3 unidades varias"),
            uv("Compra de 3 unidades varias", tipo="Privado"),
        ]
    ) == ["Laboratorio e investigación", "Equipos y material informático", OBRAS, SIN_DETALLE, SIN_CLASIFICAR]


def test_v2_solo_clasifica_lo_que_la_v1_deja_sin_detalle():
    filas = [
        uv("Mascarillas FFP2 para prácticas"),
        uv("Anti-SC35 antibody x1"),
        uv("2 ud SSD de 250 GB"),
        uv("Solicitud de patente española"),
        uv("Poster de 120x90 mate"),
        uv("Compra de reactivos"),  # la v1 ya lo clasifica: la v2 no lo toca
        uv("Por su capacidad técnica y experiencia"),  # no es un objeto: sigue sin detalle
    ]
    v1, v2 = grupo(filas, 1), grupo(filas, 2)
    assert v1[:5] == [SIN_DETALLE] * 5
    assert v2 == [
        "Otros suministros",
        "Laboratorio e investigación",
        "Equipos y material informático",
        "Trabajos y servicios por otras empresas",
        "Impresión y reprografía",
        "Laboratorio e investigación",
        SIN_DETALLE,
    ]
    assert v1[5] == v2[5]


def test_v2_no_cambia_la_upv():
    filas = [upv("MATERIAL DE OFICINA"), upv("CONCEPTO DESCONOCIDO")]
    assert grupo(filas, 1) == grupo(filas, 2)


def test_cobertura():
    df = pd.DataFrame([uv("Ordenador portátil"), uv("Compra varia"), upv("LIMPIEZA")])
    c = cobertura(df, clasificar(df)["GRUPO_GASTO"])
    assert c["UV"]["pct_pagos_clasificados"] == 50.0
    assert c["UPV"]["pct_pagos_clasificados"] == 100.0
