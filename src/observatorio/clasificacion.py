"""HU4 · Clasificación del gasto en una taxonomía común (GPR-53).

Lleva al repositorio el clasificador por reglas del notebook ``CRUCE_BASE_DATOS_UPV``
(rama ``DATASET_FINAL``), que es el que genera ``GRUPO_GASTO`` en ``UP_UV_Final.csv``:

- **UPV:** reglas sobre el ``CONCEPTO ECONÓMICO`` (partida presupuestaria).
- **UV:** reglas sobre el texto del ``Objeto_UV``. Los contratos de tipo obras van a
  «Obras y construcción». Los suministros o servicios que ninguna regla reconoce quedan como
  «Suministros/servicios (sin detalle)».
- Lo que queda sin regla es «Otros / sin clasificar».

Gana la primera regla que encaja, así que el orden importa.

La versión 2 (``version=2``) añade reglas para los objetos de la UV que la versión 1 deja
sin detalle. No cambia el dataset del equipo: es una propuesta que se valida con el
etiquetado manual de GPR-52 antes de adoptarla.

Uso:
    python -m observatorio.clasificacion --entrada UP_UV_Final.csv --salida outputs [--version 2]
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

SIN_DETALLE = "Suministros/servicios (sin detalle)"
SIN_CLASIFICAR = "Otros / sin clasificar"
OBRAS = "Obras y construcción"
TIPOS_OBRA = {"Obras", "Concesión obra pública"}
TIPOS_SIN_DETALLE = {"Suministros", "Servicios"}

REGLAS_GASTO = [
    (r"LIMPIEZA", "Limpieza"),
    (r"ARREND", "Arrendamientos"),
    (r"CONSERV|REPAR|REPRAR", "Mantenimiento y reparación"),
    (r"FONDOS BIBLIOGR|LIBROS|PRENSA, REVISTAS|PUBLICACIONES PERIOD|REVISTAS Y PUBLIC", "Libros y publicaciones"),
    (r"APLICACIONES INFORM|SOFTWARE|LICENCIAS DE USO", "Software y licencias"),
    (r"INFORM", "Equipos y material informático"),
    (r"LABORATORIO|EQUIPOS DIDACTICOS", "Laboratorio e investigación"),
    (r"MOBILIARIO", "Mobiliario"),
    (r"FOTOCOPIA", "Impresión y reprografía"),
    (r"OFICINA", "Material de oficina"),
    (r"OBRAS|CONSTRUCCION|EDIFICIOS|INVERSIONES EN TERRENOS", "Obras y construcción"),
    (r"INSTALACION|MAQUINARI|UTILLAJE|HERRAMIENTAS|OTRO INMOVILIZADO|EQUIPOS DE OFICINA|MATERIAL DE TRANSPORTE",
     "Instalaciones y maquinaria"),
    (r"VIAJE|LOCOMOCION|DIETAS|INDEMNIZ", "Viajes y dietas"),
    (r"TRANSP|CORREO|MENSAJ|POSTAL|TELEF|COMUNICACIONES|PARQUE MOVIL", "Transporte, correo y comunicaciones"),
    (r"PROTOC|REPRESENT|REUNIONES|CURSOS|CURSILLOS|CONFERENCIAS|CUOTAS INSC|ACTOS", "Atenciones, reuniones y formación"),
    (r"PUBLICIDAD|PROPAGANDA|PUBLICACIONES INSTITUCIONALES", "Publicidad y propaganda"),
    (r"SEGUROS|PRIMAS", "Seguros"),
    (r"\bAGUA\b|ENERGIA|\bGAS\b|COMBUSTIBLE|ELECTRIC", "Suministros (agua, energía, combustible)"),
    (r"TRIBUTOS|BANCARIOS", "Tributos y gastos bancarios"),
    (r"ESTUDIOS Y|TRABAJOS POR OTRAS|JURIDICO|SERVICIO PUBLICO|COLABORACION|SEGURIDAD|CUSTODIA",
     "Trabajos y servicios por otras empresas"),
    (r"ALIMENTICIOS|VESTUARIO|DEPORTIV|AUDIOVISUAL|OTROS PRODUCTOS", "Otros suministros"),
    (r"GASTOS DIVERSOS", "Otros gastos diversos"),
]
REGLAS_OBJETO = [
    (r"SOFTWARE|LICENCIA|APLICACION INFORM|SUSCRIPCION A?L? ?SERVICIO", "Software y licencias"),
    (r"LIBRO|LLIBRE|MANUAL|BIBLIOGRAF|\bREVISTAS?\b|SUSCRIPCION|BASE.? DE DATOS|PUBLICACION|MONOGRAF|EDITORIAL",
     "Libros y publicaciones"),
    (r"CERRAJ|COPIAS? DE LLAVES?|COPIA LLAVES?", "Mantenimiento y reparación"),
    (r"REACTIVO|FUNGIBLE|LABORATORIO|PIPETA|ANTICUERPO|OLIGO|SECUENCIACION|\bKIT\b|CULTIVO|PETRI|NITROGENO|"
     r"HIELO SECO|ETANOL|ACETONA|DISOLVENTE|PELET|FRICARBO|GARRAFA|\bPUNTAS\b|\bTUBOS?\b|GUANTES|NITRILO|"
     r"\bFILTROS?\b|\bPLACAS\b|BOTELLAS?|ENVASES?|VIDRIO", "Laboratorio e investigación"),
    (r"ORDENADOR|PORTATIL|INFORMATIC|IMPRESORA|MONITOR|TECLADO|DISCO DURO|SERVIDOR|TABLET|TONER|CARTUCHO|"
     r"MEMORIA (USB|RAM|FLASH)|\bRAM\b|\bUSB\b|CABLE|RATON", "Equipos y material informático"),
    (r"VIAJE|BILLETE|VUELO|HOTEL|ALOJAMIENTO|DESPLAZAMIENTO|AVION|\bTREN\b|ALQUILER DE VEHICULO|DIETA",
     "Viajes y dietas"),
    (r"AUTOBUS|AUTOCAR|TRASLADO|FURGONETA|ENVIO|MENSAJERIA|TRANSPORTE|PORTES|FLETE",
     "Transporte, correo y comunicaciones"),
    (r"CATERING|COMIDA|\bCAFE\b|COFFEE|ALMUERZO|\bCENA\b|RESTAURA|REFRIGERIO|\bMENU\b|BUFFET|INSCRIPCION|"
     r"CONGRESO|\bCURSOS?\b|JORNADAS?|SEMINARIO|CONFERENCIA", "Atenciones, reuniones y formación"),
    (r"TRADUCCION|CORRECCION|REVISION DEL|INGLES|LINGUISTIC", "Traducción y revisión lingüística"),
    (r"IMPRESION|IMPRENTA|FOTOCOPI|\bCOPIAS?\b|CARTEL|FOLLETO|DIPTICO|TRIPTICO|ROTULO|PANCARTA|\bLONA\b|"
     r"ENCUADERN", "Impresión y reprografía"),
    (r"REPARACION|MANTENIMIENTO|CALIBRACION|REVISION TECNICA|SUSTITUCION", "Mantenimiento y reparación"),
    (r"INSTALACION|MONTAJE", "Instalaciones y maquinaria"),
    (r"MOBILIARIO|\bSILLA|\bMESA\b|ARMARIO|ESTANTERIA", "Mobiliario"),
    (r"MATERIAL (DE )?OFICINA|\bPAPEL\b|PAPELERIA|CARPETA|BOLIGRAFO", "Material de oficina"),
    (r"ARRENDAMIENTO|\bALQUILER\b", "Arrendamientos"),
    (r"\bAGUA\b|SUMINISTRO DE (AGUA|ENERGIA|GAS|ELECTRICIDAD)|ELECTRICIDAD", "Suministros (agua, energía, combustible)"),
    (r"SEGURO", "Seguros"),
    (r"LIMPIEZA", "Limpieza"),
    (r"PUBLICIDAD|DIFUSION|PROMOCION", "Publicidad y propaganda"),
    (r"DISENO|ASESOR|CONSULTOR|ESTUDIO|INFORME|AUDITORIA|INCINERACION", "Trabajos y servicios por otras empresas"),
]

# Versión 2: reglas añadidas para objetos de la UV que la v1 deja sin detalle.
# Se aplican DESPUÉS de las de la v1, así que no cambian nada de lo que la v1 ya clasifica.
REGLAS_OBJETO_V2: list[tuple[str, str]] = [
    (r"PATENTE", "Trabajos y servicios por otras empresas"),
    (r"TRADUCCIO|CORRECCIO|REVISIO LINGUISTIC", "Traducción y revisión lingüística"),
    (r"\bTAXI|PEAJE|APARCAMIENTO|PARKING", "Viajes y dietas"),
    (r"\bPOSTER|\bPOSTERS\b|VINILO|PEGATINA", "Impresión y reprografía"),
    (r"BOMBILLA|FLUORESCENTE|LAMPARA|\bLLAVES\b|FONTANER|ELECTRICIST|PINTURA (DE )?(DESPACHO|PARED|PUERTA|AULA)", "Mantenimiento y reparación"),
    (r"MASCARILLA|\bFFP|HIDROALCOHOLIC|\bEPIS?\b|DESINFECT", "Otros suministros"),
    (r"\bACIDO|\bACID\b|ANTIBOD|ANTICUERP|\bANTI[- ]|\bDNA\b|\bRNA\b|\bPCR\b|PROTEIN|SODIO|SODIUM|"
     r"\bVIALE?S?\b|CRIOVIAL|MUESTRAS|\bCELL|CELULA|ENZIM|BUFFER|PLASMID|PRIMER|\bAGAR\b|SUERO|"
     r"MICROSCOP|CENTRIFUG|ERLENMEYER|MATRAZ|PROBETA|EPPENDORF|PARAFILM|PIPET|CUBETA|REACTIV|"
     r"\bANALISIS\b|CROMATOGRAF|ESPECTRO|REAGENT|ASSAY|ELISA|\bBSA\b|TRIS\b|METANOL|CLORURO|SULFATO|"
     r"HIDROXIDO|NITRATO|FOSFATO|ARGON|HELIO|\bCO2\b|PROBE|SIGMA|MERCK", "Laboratorio e investigación"),
    (r"\bSSD\b|\bHDD\b|DISCOS? DUROS?|\bDISCOS?\b|AURICULAR|\bMOUSE\b|ADAPTADOR|\bIPAD|APPLE|MACBOOK|"
     r"BATERIA|MICROFONO|\bCAMARA|MEMORIA|HDMI|WEBCAM|\bPC\b|PANTALLA|ALTAVOZ|PROYECTOR|CARGADOR|\bHUB\b|"
     r"ROUTER|SWITCH|LOGITECH|SAMSUNG|LENOVO|\bHP\b|\bDELL\b|COMPONENTES ELECTRONIC|ARDUINO|RASPBERRY|"
     r"ALTAVOCES", "Equipos y material informático"),
    (r"CINTA ADHESIVA|\bCELO\b|\bSELLOS?\b|\bSOBRES?\b|\bPILAS\b|GRAPA|ARCHIVADOR|TIJERA|POST-?IT|"
     r"ROTULADOR|\bLAPIZ|LAPICES|CUADERNO|AGENDA|\bFOLIOS?\b|SUBRAYADOR|CORRECTOR|CALCULADORA", "Material de oficina"),
    (r"PAGINA WEB|\bWEB\b|HOSTING|DOMINIO", "Trabajos y servicios por otras empresas"),
    (r"\bBOLSAS?\b|\bCAJAS?\b|PLASTICO|EMBALAJE", "Otros suministros"),
]


def mayus(t) -> str:
    """Mayúsculas y sin acentos; cadena vacía para nulos."""
    if not isinstance(t, str) or not t:
        return ""
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).upper()


def aplicar_reglas(texto: str, reglas) -> str | None:
    for patron, etiqueta in reglas:
        if re.search(patron, texto):
            return etiqueta
    return None


def clasificar(df: pd.DataFrame, version: int = 1) -> pd.DataFrame:
    """Devuelve ``GRUPO_GASTO`` y ``GRUPO_GASTO_FUENTE`` para cada fila de ``df``."""
    reglas_objeto = REGLAS_OBJETO + (REGLAS_OBJETO_V2 if version >= 2 else [])
    es_uv = (df["UNIVERSIDAD"] == "UV").to_numpy()
    cat = df["CONCEPTO ECONÓMICO"].map(mayus)
    obj = df["Objeto_UV"].map(mayus)
    g_upv = cat.map({c: aplicar_reglas(c, REGLAS_GASTO) for c in cat.unique()})
    g_uv = obj.map({o: aplicar_reglas(o, reglas_objeto) for o in obj[es_uv].unique()})
    tipo = df["Tipo_Contrato_UV"]
    es_obra_uv = es_uv & tipo.isin(TIPOS_OBRA).to_numpy()

    gasto = pd.Series(np.where(es_uv, g_uv, g_upv), index=df.index, dtype="object")
    fuente = pd.Series(np.where(es_uv, "objeto", "concepto_economico"), index=df.index, dtype="object")
    gasto[es_obra_uv] = OBRAS
    fuente[es_obra_uv] = "tipo_contrato"
    gasto[gasto.isna() & es_uv & tipo.isin(TIPOS_SIN_DETALLE).to_numpy()] = SIN_DETALLE
    gasto = gasto.fillna(SIN_CLASIFICAR)
    fuente[gasto.isin([SIN_DETALLE, SIN_CLASIFICAR])] = "sin_clasificar"
    return pd.DataFrame({"GRUPO_GASTO": gasto, "GRUPO_GASTO_FUENTE": fuente})


def cobertura(df: pd.DataFrame, grupo: pd.Series) -> dict:
    """Porcentaje de pagos y de gasto con una categoría concreta, por universidad."""
    out = {}
    for u in sorted(df["UNIVERSIDAD"].unique()):
        m = (df["UNIVERSIDAD"] == u).to_numpy()
        concreta = ~grupo[m].isin([SIN_DETALLE, SIN_CLASIFICAR])
        imp = df.loc[m, "Importe_num"]
        out[u] = {
            "pct_pagos_clasificados": round(float(100 * concreta.mean()), 1),
            "pct_gasto_clasificado": round(float(100 * imp[concreta.to_numpy()].sum() / imp.sum()), 1),
        }
    return out


def sin_detalle_frecuentes(df: pd.DataFrame, grupo: pd.Series, n: int = 50) -> pd.DataFrame:
    """Objetos de la UV sin categoría concreta más frecuentes: punto de partida para nuevas reglas."""
    m = (df["UNIVERSIDAD"] == "UV").to_numpy() & grupo.isin([SIN_DETALLE, SIN_CLASIFICAR]).to_numpy()
    d = df.loc[m].assign(OBJ=df.loc[m, "Objeto_UV"].map(mayus))
    return (
        d.groupby("OBJ").agg(PAGOS=("Importe_num", "size"), GASTO=("Importe_num", "sum"))
        .sort_values("PAGOS", ascending=False).head(n).reset_index()
    )


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entrada", required=True, help="UP_UV_Final.csv")
    p.add_argument("--salida", default="outputs")
    p.add_argument("--version", type=int, default=1, choices=[1, 2])
    a = p.parse_args(argv)

    from .carga import leer_dataset_final

    df = leer_dataset_final(a.entrada)
    res = clasificar(df, a.version)
    informe = {"version": a.version, "cobertura": cobertura(df, res["GRUPO_GASTO"])}
    if "GRUPO_GASTO" in df.columns:
        informe["coincide_con_dataset_pct"] = round(100 * (res["GRUPO_GASTO"] == df["GRUPO_GASTO"]).mean(), 2)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / f"clasificacion_v{a.version}_resumen.json").write_text(json.dumps(informe, indent=2, ensure_ascii=False))
    print(json.dumps(informe, indent=2, ensure_ascii=False))
    return informe


if __name__ == "__main__":
    main()
