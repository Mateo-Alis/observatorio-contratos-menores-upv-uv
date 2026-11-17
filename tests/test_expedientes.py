"""GPR-47 · Tests de HU3 con casos reales verificados a mano.

Las filas de tests/fixtures/upv/ están copiadas tal cual de los CSV publicados por la UPV
(2019, 2020 y 2023). Los totales esperados se han sumado a mano a partir de esas filas.
"""

import pytest

from conftest import FIXTURES
from observatorio.carga import importe_a_numero, leer_upv_carpeta
from observatorio.expedientes import (
    agregar_por_expediente,
    anadir_expediente,
    comprobar_consistencia,
    resumen,
    separar_expediente,
)


@pytest.fixture(scope="module")
def lineas():
    return anadir_expediente(leer_upv_carpeta(FIXTURES / "upv"))


@pytest.fixture(scope="module")
def expedientes(lineas):
    return agregar_por_expediente(lineas).set_index("EXPEDIENTE_ID")


@pytest.mark.parametrize(
    "texto, esperado",
    [(" 1.088,52   ", 1088.52), ("6,8", 6.8), ("363", 363.0), (" 83,77   ", 83.77), ("", None)],
)
def test_importe_a_numero(texto, esperado):
    valor = importe_a_numero(texto)
    if esperado is None:
        assert valor != valor  # NaN
    else:
        assert valor == pytest.approx(esperado)


def test_separar_expediente():
    assert separar_expediente("PV000301547/386522") == ("PV000301547", "386522")
    assert separar_expediente(" 073824 ") == ("073824", None)


def test_lectura_fixtures(lineas):
    # 6 filas de 2019 + 6 de 2020 + 8 de 2023
    assert len(lineas) == 20
    assert sorted(lineas["AÑO"].unique()) == [2019, 2020, 2023]


def test_expediente_aquablue_8_lineas(expedientes):
    # 48,79 + 10,61 + 48,79 + 10,61 + 118,48 + 10,61 + 20,91 + 10,61 = 279,41
    e = expedientes.loc["PV000301547"]
    assert e["N_LINEAS"] == 8
    assert e["IMPORTE_TOTAL"] == pytest.approx(279.41)
    assert e["IMPORTE_MAX_LINEA"] == pytest.approx(118.48)
    assert e["TERCERO"] == "AQUABLUE PREMIUM WATER S.L.U"
    assert e["AÑO"] == 2023


def test_expediente_byprint_6_lineas(expedientes):
    # 154,08 + 7,43 + 6,8 + 15,04 + 56,7 + 108,07 = 348,12
    e = expedientes.loc["PY000107991"]
    assert e["N_LINEAS"] == 6
    assert e["IMPORTE_TOTAL"] == pytest.approx(348.12)
    assert e["CENTRO_DIRECTIVO"] == "DEP. ING. CONSTRUCCION Y PROY. ING. CIVIL"


def test_expediente_con_dos_conceptos(expedientes):
    # 764,80 (inmovilizado) + 50,00 (otros productos) = 814,80
    e = expedientes.loc["P0000038754"]
    assert e["N_LINEAS"] == 2
    assert e["N_CONCEPTOS"] == 2
    assert e["IMPORTE_TOTAL"] == pytest.approx(814.80)
    assert e["CONCEPTO_PRINCIPAL"] == "Adquisición de otro inmovilizado material"


def test_expedientes_sin_barra_son_de_una_linea(expedientes):
    assert expedientes.loc["073824", "N_LINEAS"] == 1
    assert expedientes.loc["073824", "IMPORTE_TOTAL"] == pytest.approx(14.19)
    assert expedientes.loc["483508", "IMPORTE_TOTAL"] == pytest.approx(1088.52)


def test_filas_iguales_salvo_expediente_no_se_fusionan(expedientes):
    # Dos pagos de 12,09 € a 1&1 en ETSI del Diseño (2019) con expediente distinto:
    # son pagos distintos y deben quedar como dos expedientes.
    assert expedientes.loc["PM000084415", "IMPORTE_TOTAL"] == pytest.approx(12.09)
    assert expedientes.loc["PY000084416", "IMPORTE_TOTAL"] == pytest.approx(12.09)


def test_total_se_conserva(lineas, expedientes):
    assert expedientes["IMPORTE_TOTAL"].sum() == pytest.approx(lineas["IMPORTE_NUM"].sum())


def test_resumen(lineas, expedientes):
    res = resumen(lineas, expedientes.reset_index())
    assert res["lineas"] == 20
    # P0000038754, 073824, 483508, PM000084415, PY000084416, PY000107991, PV000301547
    assert res["expedientes"] == 7
    assert res["expedientes_multilinea"] == 3
    # 1&1 (12,09 repetido: 1) + AQUABLUE (48,79 dos veces: 1; 10,61 cuatro veces: 3) = 5
    assert res["filas_iguales_salvo_expediente"] == 5


def test_consistencia_detecta_mezclas(lineas):
    assert comprobar_consistencia(lineas).empty
    roto = lineas.copy()
    roto.loc[roto["EXPEDIENTE_ID"] == "PY000107991", "TERCERO"] = ["OTRO"] + ["BYPRINT PERCOM, S.L."] * 5
    assert list(comprobar_consistencia(roto).index) == ["PY000107991"]
    with pytest.raises(ValueError):
        agregar_por_expediente(roto)
