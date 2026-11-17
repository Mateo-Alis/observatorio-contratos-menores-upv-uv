"""GPR-80 · Tests de la seudonimización (HU7). Nombres tomados de los ficheros publicados."""

import pandas as pd
import pytest

from observatorio.seudonimizacion import (
    anonimizar_texto,
    es_persona_fisica,
    generar_sal,
    obtener_sal,
    parece_persona,
    seudonimizar,
    seudonimo,
    tipo_por_nif,
)

SAL = b"sal-de-prueba"


@pytest.mark.parametrize(
    "nif, esperado",
    [
        ("292****1P", True),  # DNI enmascarado por la UV
        ("048*****8*", True),
        ("12345678Z", True),
        ("X1234567L", True),
        ("B84498955", False),
        ("A28017895", False),
        ("G46980207", False),
        ("EXTSK20203338", None),
        (None, None),
        ("", None),
    ],
)
def test_tipo_por_nif(nif, esperado):
    assert tipo_por_nif(nif) is esperado


@pytest.mark.parametrize(
    "nombre",
    [
        "MARTINEZ GALLEGO ANTONIO",
        "VICÓ CRESPO, AGUSTÍ",
        "PEREZ-GALDOS ENRIQUEZ DE SALAMANCA, NATALIA",
        "FERNANDO SAEZ OLIVARES (VANGUARDIAS SONORAS PRODUCCIONES)",
        "GRAU EXPOSITO, FAUSTINO",
        "Mª PAZ CABALLERO LÓPEZ",
    ],
)
def test_detecta_personas(nombre):
    assert parece_persona(nombre)


@pytest.mark.parametrize(
    "nombre",
    [
        "LIBROS T.L.B., S.L.",
        "AQUABLUE PREMIUM WATER S.L.U",
        "1&1 INTERNET ESPAÑA S.L.U",
        "FISHER SCIENTIFIC",
        "UNIVERSITAT DE VALENCIA",
        "EXCLUSIVAS PASCUAL Y FURIO",
        "MARCIAL PONS LIBRERO",
        "CRUZ ROJA ESPAÑOLA",
        "KODIKA WEB, O.E.",
        "",
        None,
    ],
)
def test_no_marca_organizaciones(nombre):
    assert not parece_persona(nombre)


def test_nif_manda_sobre_el_nombre():
    assert es_persona_fisica("FARMACIA PATRICIA ALBERT GUARDIOLA", nif="194****8J")
    assert not es_persona_fisica("JUAN RUEDA SEVILLA", nif="B96102355")


def test_tipo_proveedor_no_empresa_no_es_persona():
    assert not es_persona_fisica("JOSE GARCIA LOPEZ", tipo_proveedor="Universidad")


def test_personas_conocidas():
    # "THAIS CAPELLA SOLANO" no tiene un nombre de pila de la lista: la heurística no lo
    # reconoce, pero si la UV lo publica con NIF de persona física, se seudonimiza igual.
    assert not parece_persona("THAIS CAPELLA SOLANO")
    conocidas = frozenset({"THAIS CAPELLA SOLANO"})
    assert es_persona_fisica("Thais Capella Solano", personas_conocidas=conocidas)


def test_seudonimo_estable_y_sin_nombre():
    a = seudonimo("MARTINEZ GALLEGO ANTONIO", SAL)
    assert a == seudonimo("Martínez  Gallego, Antonio".replace(",", ""), SAL)
    assert a.startswith("PER-") and len(a) == 12
    assert "MARTINEZ" not in a
    assert a != seudonimo("MARTINEZ GALLEGO ANTONIO", b"otra-sal")


def test_sal_vacia_no_vale():
    with pytest.raises(ValueError):
        seudonimo("X", b"")


def test_obtener_sal(tmp_path, monkeypatch):
    monkeypatch.delenv("OBSERVATORIO_SAL", raising=False)
    monkeypatch.delenv("OBSERVATORIO_SAL_FICHERO", raising=False)
    ruta = tmp_path / "sal.txt"
    with pytest.raises(RuntimeError):
        obtener_sal(ruta)
    generar_sal(ruta)
    sal = obtener_sal(ruta)
    assert len(sal) == 64
    assert generar_sal(ruta).read_text().encode() == sal  # no se sobrescribe
    monkeypatch.setenv("OBSERVATORIO_SAL", "desde-entorno")
    assert obtener_sal(ruta) == b"desde-entorno"


def test_seudonimizar_dataframe_conserva_agrupacion():
    df = pd.DataFrame(
        {
            "Proveedor": ["MARTINEZ GALLEGO ANTONIO", "MARTINEZ GALLEGO, ANTONIO", "FISHER SCIENTIFIC"],
            "PROVEEDOR_CLAVE": ["MARTINEZ GALLEGO ANTONIO"] * 2 + ["FISHER SCIENTIFIC"],
            "TIPO_PROVEEDOR": ["Empresa / persona física / otro"] * 3,
            "Importe_num": [10.0, 20.0, 30.0],
        }
    )
    out = seudonimizar(df, ["Proveedor", "PROVEEDOR_CLAVE"], SAL, col_tipo="TIPO_PROVEEDOR")
    assert out["ES_PERSONA_FISICA"].tolist() == [True, True, False]
    assert out.loc[2, "Proveedor"] == "FISHER SCIENTIFIC"
    assert not out["Proveedor"].str.contains("MARTINEZ").any()
    # La clave unificada sigue agrupando a la misma persona en un único código
    assert out.loc[0, "PROVEEDOR_CLAVE"] == out.loc[1, "PROVEEDOR_CLAVE"]
    assert out.groupby("PROVEEDOR_CLAVE")["Importe_num"].sum().max() == 30.0


@pytest.mark.parametrize(
    "texto, esperado",
    [
        (
            "Compra de billetes de tren para D. Javier Cubero, ponente en el workshop",
            "Compra de billetes de tren para D. [PERSONA] , ponente en el workshop",
        ),
        ("HOTEL DEL 24 AL 27/10/2021 PARA D. ADOLFO CORDERO", "HOTEL DEL 24 AL 27/10/2021 PARA D. [PERSONA]"),
        ("Billete de avión de la tesis doctoral de Dª Andrea Sixto Costoya", "Billete de avión de la tesis doctoral de Dª [PERSONA]"),
        ("Compra de PROTEAN Short Plates", "Compra de PROTEAN Short Plates"),
    ],
)
def test_anonimizar_texto(texto, esperado):
    assert anonimizar_texto(texto) == esperado
