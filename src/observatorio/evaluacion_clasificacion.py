"""HU4 · Muestra de etiquetado y evaluación del clasificador del objeto (GPR-51: GPR-52, GPR-54).

El clasificador por reglas (GPR-53) asigna a cada contrato un ``GRUPO_GASTO``: en la UPV a
partir del concepto económico y en la UV a partir del texto del objeto. Este módulo sirve
para medir lo bien que lo hace sobre la UV, donde la clasificación es más difícil:

1. ``muestra``  · genera 100 objetos de la UV para que **cada miembro del equipo** los
   etiquete a mano (GPR-52). La predicción del clasificador va en un fichero aparte
   (``*_prediccion.csv``) para que nadie la vea mientras etiqueta.
2. ``evaluar``  · con las etiquetas ya puestas, calcula el acuerdo entre anotadores
   (kappa de Cohen por parejas y kappa de Fleiss), la etiqueta de referencia por mayoría
   y la exactitud y la matriz de confusión del clasificador frente a ella (GPR-54).

Uso:
    python -m observatorio.evaluacion_clasificacion muestra --entrada UP_UV_Final.csv \
        --salida docs/validacion/GPR-52_etiquetado_muestra100.csv
    python -m observatorio.evaluacion_clasificacion evaluar \
        --etiquetado docs/validacion/GPR-52_etiquetado_muestra100.csv \
        --prediccion docs/validacion/GPR-52_etiquetado_muestra100_prediccion.csv --salida outputs
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

import pandas as pd

TAXONOMIA = [
    "Laboratorio e investigación",
    "Equipos y material informático",
    "Software y licencias",
    "Libros y publicaciones",
    "Material de oficina",
    "Mobiliario",
    "Impresión y reprografía",
    "Mantenimiento y reparación",
    "Instalaciones y maquinaria",
    "Obras y construcción",
    "Viajes y dietas",
    "Transporte, correo y comunicaciones",
    "Atenciones, reuniones y formación",
    "Traducción y revisión lingüística",
    "Publicidad y propaganda",
    "Trabajos y servicios por otras empresas",
    "Arrendamientos",
    "Limpieza",
    "Seguros",
    "Suministros (agua, energía, combustible)",
    "Otros suministros",
    "Otros / sin clasificar",
]
SIN_DETALLE = "Suministros/servicios (sin detalle)"
ANOTADORES = ["MATEO", "MANUEL", "PABLO", "VICENTE", "JIALE"]


def normalizar_etiqueta(valor) -> str | None:
    """Acepta la etiqueta completa o su número en TAXONOMIA (1..N); devuelve None si está vacía."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.isdigit() and 1 <= int(texto) <= len(TAXONOMIA):
        return TAXONOMIA[int(texto) - 1]
    for etiqueta in TAXONOMIA:
        if texto.lower() == etiqueta.lower():
            return etiqueta
    raise ValueError(f"Etiqueta desconocida: {valor!r}. Usa una de TAXONOMIA o su número.")


def muestra(df: pd.DataFrame, n: int = 100, semilla: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Muestra estratificada de objetos de la UV: la mitad entre los que el clasificador deja
    'sin detalle' y la otra mitad entre los clasificados, en proporción a cada categoría."""
    from .seudonimizacion import anonimizar_texto

    uv = df[(df["UNIVERSIDAD"] == "UV") & df["Objeto_UV"].notna()].copy()
    uv["Objeto_UV"] = uv["Objeto_UV"].astype(str).str.strip()
    uv = uv[uv["Objeto_UV"].str.len() >= 4].drop_duplicates("Objeto_UV")
    sin = uv[uv["GRUPO_GASTO"] == SIN_DETALLE]
    con = uv[uv["GRUPO_GASTO"] != SIN_DETALLE]
    n_sin = n // 2
    parte_sin = sin.sample(n=min(n_sin, len(sin)), random_state=semilla)
    parte_con = con.sample(n=min(n - len(parte_sin), len(con)), random_state=semilla, weights=None)
    m = pd.concat([parte_sin, parte_con]).sample(frac=1, random_state=semilla).reset_index(drop=True)
    ids = [f"E{i:03d}" for i in range(1, len(m) + 1)]
    out = pd.DataFrame(
        {"ID": ids, "OBJETO": m["Objeto_UV"].map(anonimizar_texto), "TIPO_CONTRATO": m["Tipo_Contrato_UV"]}
    )
    for a in ANOTADORES:
        out[f"ETIQUETA_{a}"] = ""
    prediccion = pd.DataFrame({"ID": ids, "PREDICCION_CLASIFICADOR": m["GRUPO_GASTO"].tolist()})
    return out, prediccion


def kappa_cohen(a: list, b: list) -> float | None:
    pares = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pares:
        return None
    n = len(pares)
    po = sum(x == y for x, y in pares) / n
    ca, cb = Counter(x for x, _ in pares), Counter(y for _, y in pares)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 3)


def kappa_fleiss(filas: list[list]) -> float | None:
    """Kappa de Fleiss sobre los ítems que tienen el mismo número (≥2) de etiquetas."""
    filas = [[x for x in f if x is not None] for f in filas]
    if not filas:
        return None
    m = max(len(f) for f in filas)
    filas = [f for f in filas if len(f) == m]
    if m < 2 or not filas:
        return None
    n = len(filas)
    categorias = sorted({x for f in filas for x in f})
    p_j = {c: sum(f.count(c) for f in filas) / (n * m) for c in categorias}
    p_i = [(sum(f.count(c) ** 2 for c in categorias) - m) / (m * (m - 1)) for f in filas]
    p_bar = sum(p_i) / n
    pe = sum(v * v for v in p_j.values())
    return 1.0 if pe == 1 else round((p_bar - pe) / (1 - pe), 3)


def etiqueta_mayoria(etiquetas: list) -> str | None:
    """Etiqueta con más votos; None si no hay etiquetas o hay empate en cabeza."""
    votos = Counter(x for x in etiquetas if x is not None)
    if not votos:
        return None
    (primera, n1), *resto = votos.most_common()
    if resto and resto[0][1] == n1:
        return None
    return primera


def evaluar(etiquetado: pd.DataFrame, prediccion: pd.DataFrame | None = None) -> tuple[dict, pd.DataFrame]:
    """Devuelve (métricas, matriz de confusión clasificador × referencia por mayoría)."""
    if prediccion is not None:
        etiquetado = etiquetado.merge(prediccion, on="ID", how="left")
    cols = [c for c in etiquetado.columns if c.startswith("ETIQUETA_")]
    etiq = etiquetado[cols].apply(lambda s: s.map(normalizar_etiqueta))
    activos = [c for c in cols if etiq[c].notna().any()]
    if not activos:
        raise ValueError("Ninguna columna ETIQUETA_* tiene etiquetas todavía")

    filas = etiq[activos].values.tolist()
    referencia = [etiqueta_mayoria(f) for f in filas]
    pred = etiquetado["PREDICCION_CLASIFICADOR"].tolist()

    validos = [(p, r) for p, r in zip(pred, referencia) if r is not None]
    aciertos = sum(p == r for p, r in validos)
    sin_detalle = sum(p == SIN_DETALLE for p, _ in validos)
    clasificados = [(p, r) for p, r in validos if p != SIN_DETALLE]

    metricas = {
        "items": int(len(etiquetado)),
        "anotadores": [c.replace("ETIQUETA_", "") for c in activos],
        "items_con_referencia": len(validos),
        "exactitud": round(aciertos / len(validos), 3) if validos else None,
        "cobertura": round(1 - sin_detalle / len(validos), 3) if validos else None,
        "exactitud_en_clasificados": (
            round(sum(p == r for p, r in clasificados) / len(clasificados), 3) if clasificados else None
        ),
        "kappa_fleiss": kappa_fleiss(filas) if len(activos) > 2 else None,
        "kappa_cohen_por_parejas": {
            f"{a.replace('ETIQUETA_', '')}-{b.replace('ETIQUETA_', '')}": kappa_cohen(
                etiq[a].tolist(), etiq[b].tolist()
            )
            for a, b in itertools.combinations(activos, 2)
        },
    }
    matriz = pd.crosstab(
        pd.Series([r for _, r in validos], name="REFERENCIA"),
        pd.Series([p for p, _ in validos], name="CLASIFICADOR"),
    )
    return metricas, matriz


def main(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="orden", required=True)
    pm = sub.add_parser("muestra")
    pm.add_argument("--entrada", required=True)
    pm.add_argument("--salida", required=True)
    pm.add_argument("--n", type=int, default=100)
    pe = sub.add_parser("evaluar")
    pe.add_argument("--etiquetado", required=True)
    pe.add_argument("--prediccion", help="Fichero *_prediccion.csv generado con la muestra")
    pe.add_argument("--salida", default="outputs")
    a = p.parse_args(argv)

    if a.orden == "muestra":
        from .carga import leer_dataset_final

        m, pred = muestra(leer_dataset_final(a.entrada), n=a.n)
        ruta = Path(a.salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        m.to_csv(ruta, sep=";", index=False, encoding="utf-8-sig")
        pred.to_csv(ruta.with_name(ruta.stem + "_prediccion.csv"), sep=";", index=False, encoding="utf-8-sig")
        print(f"{len(m)} objetos en {ruta}")
        return m

    etiquetado = pd.read_csv(a.etiquetado, sep=";", encoding="utf-8-sig", dtype=str)
    pred = pd.read_csv(a.prediccion, sep=";", encoding="utf-8-sig", dtype=str) if a.prediccion else None
    metricas, matriz = evaluar(etiquetado, pred)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "evaluacion_clasificador.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    matriz.to_csv(salida / "matriz_confusion_clasificador.csv", sep=";", encoding="utf-8-sig")
    print(json.dumps(metricas, indent=2, ensure_ascii=False))
    return metricas


if __name__ == "__main__":
    main()
