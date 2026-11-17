# Validaciones manuales del Sprint 2

Estas tareas las tiene que hacer una persona del equipo: el código prepara los ficheros y, cuando están rellenos, calcula las métricas.

## GPR-58 · Validar 50 emparejamientos de proveedores (HU6)

Fichero: `GPR-58_emparejamientos_muestra50.csv`. Son 50 proveedores comunes cuyo nombre se publica distinto en la UPV y en la UV. Están elegidos al azar (semilla 2026) y no incluye personas físicas.

1. Para cada fila, decide si `NOMBRE_EN_UPV` y `NOMBRE_EN_UV` son **la misma empresa**.
2. Escribe `S` o `N` en `CORRECTO_SN`, tus iniciales en `REVISADO_POR` y, si dudas, un `COMENTARIO`.
3. Calcula la precisión:

   ```python
   import pandas as pd
   from observatorio.proveedores_comunes import precision_validacion
   precision_validacion(pd.read_csv("docs/validacion/GPR-58_emparejamientos_muestra50.csv", sep=";"))
   ```

4. Anota el resultado en GPR-58 y en la HU6.

## GPR-52 · Etiquetar 100 objetos de la UV (HU4)

Fichero: `GPR-52_etiquetado_muestra100.csv`. Son 100 objetos de contrato de la UV: la mitad los deja el clasificador "sin detalle" y la otra mitad los clasifica. Los nombres de personas del texto ya aparecen como `[PERSONA]`.

1. **No abras** `GPR-52_etiquetado_muestra100_prediccion.csv` hasta haber terminado: es la respuesta del clasificador.
2. Cada miembro rellena **solo su columna** `ETIQUETA_<NOMBRE>`, sin mirar las de los demás.
3. Usa una categoría de esta lista (vale el número o el nombre):

| Nº | Categoría | Nº | Categoría |
|---|---|---|---|
| 1 | Laboratorio e investigación | 12 | Transporte, correo y comunicaciones |
| 2 | Equipos y material informático | 13 | Atenciones, reuniones y formación |
| 3 | Software y licencias | 14 | Traducción y revisión lingüística |
| 4 | Libros y publicaciones | 15 | Publicidad y propaganda |
| 5 | Material de oficina | 16 | Trabajos y servicios por otras empresas |
| 6 | Mobiliario | 17 | Arrendamientos |
| 7 | Impresión y reprografía | 18 | Limpieza |
| 8 | Mantenimiento y reparación | 19 | Seguros |
| 9 | Instalaciones y maquinaria | 20 | Suministros (agua, energía, combustible) |
| 10 | Obras y construcción | 21 | Otros suministros |
| 11 | Viajes y dietas | 22 | Otros / sin clasificar |

4. Con al menos tres columnas rellenas, calcula el acuerdo entre anotadores, la exactitud y la matriz de confusión (GPR-54):

   ```bash
   PYTHONPATH=src python -m observatorio.evaluacion_clasificacion evaluar \
       --etiquetado docs/validacion/GPR-52_etiquetado_muestra100.csv \
       --prediccion docs/validacion/GPR-52_etiquetado_muestra100_prediccion.csv \
       --salida outputs
   ```

**Cómo leer el resultado:**
- `kappa_fleiss` mide el acuerdo entre vosotros. Por encima de 0,6 la taxonomía se entiende igual entre anotadores.
- `exactitud` compara el clasificador con la etiqueta mayoritaria.
- `cobertura` es la parte de objetos que el clasificador no deja "sin detalle".
