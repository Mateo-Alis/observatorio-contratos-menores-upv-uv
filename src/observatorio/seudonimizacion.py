"""HU7 · Seudonimización de datos de terceros (GPR-48: GPR-79, GPR-80).

Qué es un dato personal aquí: el nombre del proveedor cuando es una **persona física**
(autónomos, profesionales, particulares). Los nombres de empresas no son datos personales.

Cómo se detecta una persona física:
1. Por NIF, cuando se tiene (solo la UV lo publica): un NIF enmascarado (``292****1P``) o
   con forma de DNI/NIE es de persona física; uno que empieza por letra de sociedad
   (A, B, G, …) es de persona jurídica.
2. Por el nombre (la UPV no publica NIF): no lleva forma societaria ni palabras de
   organización, tiene entre 2 y 6 palabras y contiene un nombre de pila conocido.

Cómo se seudonimiza: HMAC-SHA256 del nombre normalizado con una **sal secreta que no
está en el repositorio** (variable de entorno ``OBSERVATORIO_SAL`` o fichero
``~/.observatorio/sal.txt``). Con la misma sal, la misma persona recibe siempre el mismo
código (``PER-xxxxxxxx``), así que los análisis por proveedor siguen funcionando; sin la
sal no se puede volver al nombre.

Uso:
    python -m observatorio.seudonimizacion --generar-sal
    python -m observatorio.seudonimizacion --entrada UP_UV_Final.csv --salida outputs
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import unicodedata
from pathlib import Path

import pandas as pd

RUTA_SAL_POR_DEFECTO = Path.home() / ".observatorio" / "sal.txt"
PREFIJO = "PER-"

# Formas societarias y palabras que indican una organización, no una persona.
RE_ORGANIZACION = re.compile(
    r"\b("
    r"S ?L ?U?|S ?A ?U?|S ?L ?L|S ?C ?V|S ?COOP|COOP\w*|C ?B|SOCIEDAD|SDAD|CIA|"
    r"GMBH|LTD|LIMITED|INC|LLC|PLC|B ?V|N ?V|AG|SPA|SRL|SARL|SAS|AB|OY|AS|KG|CORP\w*|CO|"
    r"COMPANY|GROUP|GRUPO|HOLDING|INTERNATIONAL|INTERNACIONAL|GLOBAL|IBERICA|ESPANA|SPAIN|EUROPE\w*|"
    r"SERVICIOS?|SERVEIS|SERVICES|SOLUTIONS|SOLUCIONES|SYSTEMS?|SISTEMAS|INGENIERIA|ENGINEERING|"
    r"CONSULTING|CONSULTOR\w*|ASESOR\w*|TECHNOLOG\w*|TECNOLOG\w*|DISTRIBU\w*|COMERCIAL|INDUSTRIAL\w*|"
    r"EDITORIAL|EDICIONES|EDICIONS|PRESS|PUBLISH\w*|LIBRERIA|LLIBRERIA|IMPRENTA|GRAFICAS|"
    r"HOTEL\w*|RESTAURANTE?|BAR|CAFETERIA|CATERING|VIAJES|TRAVEL|AGENCIA|TRANSPORT\w*|"
    r"FUNDACION|FUNDACIO|FOUNDATION|ASOCIACION|ASSOCIACIO|ASSOCIATION|SOCIETY|SOCIEDAD|"
    r"UNIVERSIDAD|UNIVERSITAT|UNIVERSITY|INSTITUT\w*|CENTRO|CENTRE|CENTER|CLUB|COLEGIO|COL LEGI|"
    r"AYUNTAMIENTO|AJUNTAMENT|GENERALITAT|MINISTERIO|CONSORCI\w*|DIPUTACION|"
    r"LABORATORI\w*|LABS?|SCIENTIFIC|MEDICAL|PHARMA\w*|FARMACIA|CLINICA|HOSPITAL|"
    r"ELECTRONICA|INFORMATICA|AUTOMATISMOS|SUMINISTROS|MATERIALES|EQUIPOS|INSTRUMENT\w*|"
    r"INVERSIONES|PROMOCIONES|GESTION|PRODUCCIONES|ESTUDIO|STUDIO|TALLER\w*|FERRETERIA|"
    r"BODEGAS?|CASA RURAL|ACADEMIA|ESCUELA|ESCOLA|SCHOOL|ONLINE|DIGITAL|NETWORK\w*|SOFTWARE|"
    r"HERMANOS|HNOS|E HIJOS|HIJOS|Y CIA|PARTNERS|ASOCIADOS|ABOGADOS|ADVOCATS|ARQUITECT\w*|"
    r"S ?C|O ?E|FUND|IMPRESOR\w*|EXCLUSIVAS|LIBRER\w*|"
    r"TABERNA|MIRADOR|CRUZ ROJA|PRODUCTOS|EDITOR\w*|AGRUPACION|UNIVERSIDADE|ALBERG\w*|"
    r"MUSEO|MUSEU|TEATRO|TEATRE|ORQUESTA|BANDA|COMPANIA|RESEARCH|ACADEMY|COLLEGE"
    r")\b"
)

# Nombres de pila frecuentes (castellano, valenciano/catalán y otros habituales en los datos).
NOMBRES_PILA = frozenset(
    """
    AARON ABEL ADAM ADELA ADOLFO ADRIA ADRIAN ADRIANA AGUSTI AGUSTIN AINA AINHOA AITANA ALBA
    ALBERT ALBERTO ALEJANDRA ALEJANDRO ALEX ALEXANDRE ALEXIS ALFONSO ALFREDO ALICIA ALVARO
    AMADEO AMALIA AMPARO ANA ANABEL ANDREA ANDREI ANDRES ANDREU ANGEL ANGELA ANGELES ANNA
    ANTONI ANTONIA ANTONIO ARACELI ARANTXA ARMANDO ARNAU ARTURO ASUNCION AURORA BALTASAR
    BARBARA BEATRIZ BEGONA BELEN BENITO BERNARDO BLANCA BORJA BRUNO CAMILO CANDELA CARLA
    CARLES CARLOS CARMEN CAROLINA CATALINA CECILIA CELIA CESAR CLARA CONCEPCION CONSUELO
    CRISTIAN CRISTINA CRUZ DAMIAN DANIEL DANIELA DANIELLE DARIO DAVID DIANA DIEGO DOLORES
    DOMINGO EDUARD EDUARDO ELENA ELISA ELVIRA EMILIA EMILIO ENRIC ENRIQUE ENRIQUETA ERIC
    ERNESTO ESPERANZA ESTEBAN ESTER ESTHER EUGENIA EUGENIO EVA FABIAN FATIMA FEDERICO FELIPE
    FELIX FERNANDO FERRAN FIDEL FRANCESC FRANCISCA FRANCISCO GABRIEL GABRIELA GASPAR GEMA
    GEMMA GERARD GERARDO GERMAN GLORIA GONZALO GRACIA GREGORIO GUILLEM GUILLERMO GUSTAVO
    HECTOR HELENA HUGO IGNACIO IKER INES INMACULADA IRENE ISAAC ISABEL ISIDRO IVAN JACOBO
    JAIME JAUME JAVIER JESUS JOAN JOAQUIM JOAQUIN JOEL JORDI JORGE JOSE JOSEFA JOSEP JUAN
    JUANA JULIA JULIAN JULIO LAIA LAURA LEANDRO LEONOR LIDIA LLUIS LORENA LORENZO LOURDES
    LUCAS LUCIA LUIS LUISA MANUEL MANUELA MAR MARC MARCOS MARGARITA MARI MARIA MARIANO
    MARINA MARIO MARIONA MARTA MARTI MARTIN MATEO MATIAS MERCEDES MIGUEL MIQUEL MIREIA
    MIRACLE MIRIAM MONICA MONTSERRAT NATALIA NEUS NICOLAS NOELIA NURIA OFELIA OLGA OMAR OSCAR PABLO
    PAOLA PASCUAL PATRICIA PAU PAULA PEDRO PEP PERE PILAR PURIFICACION QUIM RAFAEL RAMON
    RAQUEL RAUL REBECA RICARD RICARDO ROBERTO ROCIO RODRIGO ROSA ROSARIO RUBEN SALVADOR
    SAMUEL SANDRA SANTIAGO SARA SEBASTIAN SERGI SERGIO SILVIA SOFIA SONIA SUSANA TERESA
    THOMAS TOMAS VALENTIN VANESA VERONICA VICENT VICENTA VICENTE VICTOR VICTORIA VIRGINIA
    XAVIER XIMO YOLANDA
    AGATA ALEIX AMELIA ARTUR AUSIAS BARTOLOME CAYETANO CIRENIA CLAUDIA CONRADO DOROTEA ELEUTERIO
    ELADIO ENCARNACION ESPERANZA FAUSTINO FLORENCIO GENOVEVA GINES HELENA HORACIO HONORIO
    IRIS JOSEFINA KSENIYA LEOPOLDO LIDIA MACARENA MAGDALENA MARCELINO MARCIAL MAXIMO MILAGROS
    NIEVES NOEMI PALOMA PAULINO PAZ REMEDIOS REYES ROSANA ROSALIA SOLEDAD TAMARA TRINIDAD
    VALERIA VALERIANO YOUSSEF YOUSSAF ZOE MA MERCE MERITXELL MONTSE NEREA OLIVIA OLGA ROGER
    """.split()
)

RE_NIF_PERSONA = re.compile(r"^(\d{8}[A-Z]|[XYZ]\d{7}[A-Z])$")
RE_NIF_SOCIEDAD = re.compile(r"^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$")


def normalizar(texto) -> str:
    """Mayúsculas, sin tildes ni signos, espacios simples."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    t = unicodedata.normalize("NFKD", str(texto).upper()).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tipo_por_nif(nif) -> bool | None:
    """True si el NIF es de persona física, False si es de sociedad, None si no se sabe."""
    if nif is None or (isinstance(nif, float) and pd.isna(nif)):
        return None
    n = str(nif).strip().upper().replace("-", "").replace(" ", "")
    if not n or n == "NAN":
        return None
    if "*" in n or RE_NIF_PERSONA.match(n):
        return True
    if RE_NIF_SOCIEDAD.match(n):
        return False
    return None


def parece_persona(nombre) -> bool:
    """Heurística por nombre, para cuando no hay NIF.

    El texto entre paréntesis se descarta: suele ser el nombre comercial de un autónomo
    ("FERNANDO SAEZ OLIVARES (VANGUARDIAS SONORAS)").
    """
    original = "" if nombre is None else str(nombre)
    sin_parentesis = re.sub(r"\(.*?\)", " ", original)
    n = normalizar(sin_parentesis)
    if not n or RE_ORGANIZACION.search(n):
        return False
    palabras = n.split()
    if not 2 <= len(palabras) <= 6 or any(any(ch.isdigit() for ch in p) for p in palabras):
        return False
    if any(p in NOMBRES_PILA for p in palabras):
        return True
    # Formato "APELLIDOS, NOMBRE": dos o tres apellidos y uno o dos nombres tras la coma.
    if "," in sin_parentesis:
        antes, despues = (normalizar(x) for x in sin_parentesis.split(",", 1))
        return (
            1 <= len(antes.split()) <= 3
            and 1 <= len(despues.split()) <= 2
            and all(len(w) > 1 for w in despues.split())
        )
    return False


def es_persona_fisica(nombre, nif=None, tipo_proveedor=None, personas_conocidas=frozenset()) -> bool:
    """Decide si un proveedor es una persona física (ver la cabecera del módulo).

    ``personas_conocidas``: nombres normalizados que ya se sabe que son personas físicas
    (por ejemplo, los que la UV publica con NIF enmascarado); sirve también para la UPV.
    """
    por_nif = tipo_por_nif(nif)
    if por_nif is not None:
        return por_nif
    if personas_conocidas and normalizar(re.sub(r"\(.*?\)", " ", str(nombre))) in personas_conocidas:
        return True
    if tipo_proveedor is not None and isinstance(tipo_proveedor, str) and tipo_proveedor:
        if not tipo_proveedor.startswith("Empresa / persona"):
            return False
    return parece_persona(nombre)


def generar_sal(ruta: Path = RUTA_SAL_POR_DEFECTO) -> Path:
    """Crea una sal aleatoria fuera del repositorio (no sobrescribe una existente)."""
    ruta = Path(ruta)
    if ruta.exists():
        return ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(secrets.token_hex(32))
    os.chmod(ruta, 0o600)
    return ruta


def obtener_sal(ruta: Path | None = None) -> bytes:
    """Sal desde OBSERVATORIO_SAL, o desde el fichero indicado o el de por defecto."""
    if os.environ.get("OBSERVATORIO_SAL"):
        return os.environ["OBSERVATORIO_SAL"].encode()
    ruta = Path(ruta or os.environ.get("OBSERVATORIO_SAL_FICHERO") or RUTA_SAL_POR_DEFECTO)
    if not ruta.exists():
        raise RuntimeError(
            "No hay sal para seudonimizar. Ejecuta "
            "'python -m observatorio.seudonimizacion --generar-sal' o define OBSERVATORIO_SAL. "
            "La sal nunca se sube al repositorio."
        )
    return ruta.read_text().strip().encode()


def seudonimo(nombre, sal: bytes) -> str:
    """Código estable PER-xxxxxxxx para un nombre, con HMAC-SHA256 y la sal."""
    if not sal:
        raise ValueError("La sal no puede estar vacía")
    digest = hmac.new(sal, normalizar(nombre).encode(), hashlib.sha256).hexdigest()
    return PREFIJO + digest[:8].upper()


# Tratamiento + nombre en textos libres ("billetes para D. Javier Cubero", "tesis de Dª Andrea …").
RE_PERSONA_EN_TEXTO = re.compile(
    r"\b(D\.|Dª|Dña\.?|DÑA\.?|DON|DOÑA|Don|Doña|SR\.|SRA\.|Sr\.|Sra\.)\s+"
    r"((?:[A-ZÁÉÍÓÚÑÇ][\wÁÉÍÓÚÑÇáéíóúñçàèòï'·-]*\.?\s*){1,4})"
)


def anonimizar_texto(texto) -> str:
    """Sustituye por [PERSONA] los nombres que siguen a un tratamiento (D., Dª, Sr., …)."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return texto
    return RE_PERSONA_EN_TEXTO.sub(lambda m: m.group(1) + " [PERSONA] ", str(texto)).replace("  ", " ").strip()


def seudonimizar(
    df: pd.DataFrame,
    columnas_nombre: list[str],
    sal: bytes,
    col_nif: str | None = None,
    col_tipo: str | None = None,
    personas_conocidas: frozenset = frozenset(),
    columnas_texto: tuple = (),
) -> pd.DataFrame:
    """Sustituye por un seudónimo los nombres de personas físicas en las columnas dadas.

    La primera columna de ``columnas_nombre`` decide si la fila es una persona física;
    añade ES_PERSONA_FISICA y elimina la columna de NIF si se indica.
    """
    out = df.copy()
    principal = columnas_nombre[0]
    nifs = out[col_nif] if col_nif else pd.Series([None] * len(out), index=out.index)
    tipos = out[col_tipo] if col_tipo else pd.Series([None] * len(out), index=out.index)

    cache: dict = {}

    def decide(nombre, nif, tipo):
        clave = (nombre, nif, tipo)
        if clave not in cache:
            cache[clave] = es_persona_fisica(nombre, nif, tipo, personas_conocidas)
        return cache[clave]

    out["ES_PERSONA_FISICA"] = [decide(a, b, c) for a, b, c in zip(out[principal], nifs, tipos)]
    mascara = out["ES_PERSONA_FISICA"]
    for col in columnas_nombre:
        # Cada columna se seudonimiza a partir de su propio valor, para que una clave
        # unificada (PROVEEDOR_CLAVE) siga agrupando igual después de seudonimizar.
        out.loc[mascara, col] = out.loc[mascara, col].map(lambda n: seudonimo(n, sal))
    if col_nif:
        out = out.drop(columns=[col_nif])
    for col in columnas_texto:
        out[col] = out[col].map(anonimizar_texto)
    return out


def personas_desde_uv(carpeta: str | Path) -> frozenset:
    """Nombres normalizados que la UV publica con NIF de persona física (enmascarado)."""
    nombres = set()
    for ruta in sorted(Path(carpeta).glob("*UV.xls*")):
        bruto = pd.read_excel(ruta, header=None)
        fila = bruto.index[
            bruto.apply(lambda r: r.astype(str).str.contains("adjudicatario", case=False).any(), axis=1)
        ][0]
        df = pd.read_excel(ruta, header=fila)
        df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
        es_persona = df["NIF adjudicatario"].map(tipo_por_nif) == True  # noqa: E712
        for nombre in df.loc[es_persona, "Nombre adjudicatario"].dropna():
            nombres.add(normalizar(re.sub(r"\(.*?\)", " ", str(nombre))))
    return frozenset(nombres)


def main(argv: list[str] | None = None) -> dict | None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--generar-sal", action="store_true", help="Crea ~/.observatorio/sal.txt si no existe")
    p.add_argument("--entrada", help="Dataset unificado (UP_UV_Final.csv)")
    p.add_argument("--salida", default="outputs")
    p.add_argument("--uv-crudos", help="Carpeta con los XLS de la UV, para usar su NIF enmascarado")
    a = p.parse_args(argv)

    if a.generar_sal:
        print(f"Sal guardada en {generar_sal()} (fuera del repositorio)")
        return None
    if not a.entrada:
        p.error("Indica --entrada o --generar-sal")

    from .carga import leer_dataset_final

    df = leer_dataset_final(a.entrada)
    cols = [c for c in ["Proveedor", "PROVEEDOR_CLAVE", "GRUPO_EMPRESARIAL"] if c in df.columns]
    conocidas = personas_desde_uv(a.uv_crudos) if a.uv_crudos else frozenset()
    textos = tuple(c for c in ["Objeto_UV"] if c in df.columns)
    out = seudonimizar(
        df, cols, obtener_sal(), col_tipo="TIPO_PROVEEDOR", personas_conocidas=conocidas, columnas_texto=textos
    )
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    out.to_csv(salida / "UP_UV_Final_seudonimizado.csv", sep=";", index=False, encoding="utf-8-sig")
    res = {
        "filas": int(len(out)),
        "filas_persona_fisica": int(out["ES_PERSONA_FISICA"].sum()),
        "proveedores_persona_fisica": int(df.loc[out["ES_PERSONA_FISICA"], cols[0]].nunique()),
        "por_universidad": {
            u: int(n) for u, n in out[out["ES_PERSONA_FISICA"]].groupby("UNIVERSIDAD").size().items()
        },
        "personas_conocidas_por_nif_uv": len(conocidas),
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()
