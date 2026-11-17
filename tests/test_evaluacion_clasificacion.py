"""Tests de la evaluación del clasificador (GPR-54) con etiquetas de ejemplo."""

import pandas as pd
import pytest

from observatorio.evaluacion_clasificacion import (
    SIN_DETALLE,
    TAXONOMIA,
    etiqueta_mayoria,
    evaluar,
    kappa_cohen,
    kappa_fleiss,
    muestra,
    normalizar_etiqueta,
)

LAB, INF, VIA = "Laboratorio e investigación", "Equipos y material informático", "Viajes y dietas"


def test_normalizar_etiqueta():
    assert normalizar_etiqueta("1") == TAXONOMIA[0]
    assert normalizar_etiqueta(" viajes y dietas ") == VIA
    assert normalizar_etiqueta("") is None
    with pytest.raises(ValueError):
        normalizar_etiqueta("no existe")


def test_kappa_cohen():
    assert kappa_cohen([LAB, INF, VIA, LAB], [LAB, INF, VIA, LAB]) == 1.0
    # po = 0,5; pe = 0,5 -> kappa 0
    assert kappa_cohen([LAB, LAB, INF, INF], [LAB, INF, LAB, INF]) == 0.0


def test_kappa_fleiss_acuerdo_total():
    assert kappa_fleiss([[LAB, LAB, LAB], [INF, INF, INF], [VIA, VIA, VIA]]) == 1.0


def test_kappa_fleiss_ejemplo_clasico():
    # 4 ítems, 3 anotadores: valor calculado a mano = 0,25
    filas = [[LAB, LAB, LAB], [LAB, LAB, INF], [INF, INF, LAB], [INF, INF, INF]]
    p_bar = (1 + 1 / 3 + 1 / 3 + 1) / 4
    assert kappa_fleiss(filas) == round((p_bar - 0.5) / 0.5, 3)


def test_mayoria():
    assert etiqueta_mayoria([LAB, LAB, INF]) == LAB
    assert etiqueta_mayoria([LAB, INF]) is None
    assert etiqueta_mayoria([None, None]) is None


def test_evaluar():
    etiquetado = pd.DataFrame(
        {
            "ID": ["E1", "E2", "E3", "E4"],
            "ETIQUETA_MATEO": [LAB, INF, VIA, "1"],
            "ETIQUETA_PABLO": [LAB, INF, VIA, LAB],
            "ETIQUETA_JIALE": [LAB, LAB, VIA, LAB],
            "ETIQUETA_MANUEL": ["", "", "", ""],
        }
    )
    pred = pd.DataFrame({"ID": ["E1", "E2", "E3", "E4"], "PREDICCION_CLASIFICADOR": [LAB, INF, SIN_DETALLE, INF]})
    m, matriz = evaluar(etiquetado, pred)
    assert m["anotadores"] == ["MATEO", "PABLO", "JIALE"]
    assert m["items_con_referencia"] == 4
    assert m["exactitud"] == 0.5  # E1 y E2 bien; E3 sin detalle; E4 mal
    assert m["cobertura"] == 0.75
    assert m["exactitud_en_clasificados"] == round(2 / 3, 3)
    assert matriz.loc[LAB, INF] == 1


def test_muestra_oculta_la_prediccion():
    df = pd.DataFrame(
        {
            "UNIVERSIDAD": ["UV"] * 6 + ["UPV"],
            "Objeto_UV": [
                "Compra de reactivos",
                "Billetes de tren para D. Javier Ortiz",
                "Material diverso",
                "Ordenador portátil",
                "Servicio vario",
                "Cena de trabajo",
                None,
            ],
            "Tipo_Contrato_UV": ["Suministros"] * 7,
            "GRUPO_GASTO": [LAB, VIA, SIN_DETALLE, INF, SIN_DETALLE, SIN_DETALLE, LAB],
        }
    )
    m, pred = muestra(df, n=4, semilla=1)
    assert len(m) == 4 and len(pred) == 4
    assert "PREDICCION_CLASIFICADOR" not in m.columns
    assert (pred["PREDICCION_CLASIFICADOR"] == SIN_DETALLE).sum() == 2
    assert not m["OBJETO"].str.contains("Javier").any()
