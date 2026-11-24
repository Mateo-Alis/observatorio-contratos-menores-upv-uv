# Pipeline del Observatorio (GPR-115)

De los ficheros publicados a las alertas y las oportunidades de compra conjunta. Las cifras son de la ejecución sobre 2019–2023.

```
 UPV: 5 CSV (líneas de gasto)      UV: 5 XLS/XLSX (contratos/gastos)
            │                                   │
            └────────── 1. Ingesta y limpieza ──┘      notebook CRUCE_BASE_DATOS_UPV (HU1, HU2)
                              │
                  2. Esquema común + unificación de proveedores
                              │                         UP_UV_Final.csv: 431.538 pagos · 343,9 M€
            ┌─────────────────┼──────────────────────┬──────────────────────┐
   3. Expedientes UPV   4. Seudonimización     5. Clasificación        6. Proveedores comunes
      (HU3)                (HU7)                  del objeto (HU4)        y compra conjunta (HU6)
            └─────────────────┴───────────┬──────────┴──────────────────────┘
                                 7. Alertas de fraccionamiento (HU8)
                                 8. Dashboard (HU10) e informe (HU11)
```

## 1–2. Ingesta, limpieza y esquema común (HU1, HU2 · Sprint 1)

Lo hace el notebook `CRUCE_BASE_DATOS_UPV.ipynb` (rama `DATASET_FINAL`).

- **Lectura:** UPV en latin-1 con `;` y coma decimal; UV con la cabecera en la segunda fila y sin las filas de avisos legales del pie.
- **Limpieza:** corrige la codificación, pasa los importes a número y quita los importes nulos o cero.
- **Unificación de proveedores** (`PROVEEDOR_CLAVE`), en tres capas:
  1. Nombre normalizado y con las palabras ordenadas.
  2. Mismo NIF en la UV.
  3. Fusiones por similitud revisadas a mano.

  Encima se calcula `GRUPO_EMPRESARIAL`, que agrupa filiales como Amazon EU y Amazon Business.
- **Tipo de proveedor:** empresa, universidad, entidad pública, fundación…
- **Categoría de gasto:** `GRUPO_GASTO`, con 22 categorías. En la UPV sale del concepto económico y en la UV del texto del objeto.

**Salida:** `UP_UV_Final.csv`, con 431.538 pagos (UPV 217.244, UV 214.294) y 343,9 M€.

## 3. Agregación por expediente · `observatorio.expedientes` (HU3)

- En la UPV, el campo `EXPEDIENTE` es `<expediente>/<línea>`. Agrupando por la parte anterior a la barra, las **217.244 líneas** se convierten en **210.897 expedientes**. De ellos, 5.450 tienen varias líneas (hasta 8) y 546 mezclan conceptos.
- Dentro de un expediente, el proveedor, el centro y el año no cambian nunca. El módulo lo comprueba y falla si no se cumple.
- **Hallazgo:** las **19.740 filas** que repiten proveedor, concepto, importe, centro y año tienen expedientes distintos. Son **pagos distintos, no duplicados**. Esto responde a la pregunta de la review del Sprint 1.
- La suma de importes se conserva exactamente (186.628.500,46 €).
- 1.380 expedientes superan por sí solos los 15.000 €. Conviene revisarlos con el cliente, porque por encima de ese umbral no debería tratarse de un contrato menor de servicios o suministros.

## 4. Seudonimización · `observatorio.seudonimizacion` (HU7)

Detalle completo en [`datos_personales.md`](datos_personales.md).

- **Detección de persona física:**
  1. Por el NIF de la UV, que ya viene enmascarado.
  2. Por la lista de personas de la UV.
  3. Por una regla sobre el nombre. Medida contra el NIF: precisión 99,9 % y exhaustividad 83,4 %.
- **Seudónimo:** `PER-xxxxxxxx`, calculado con HMAC-SHA256 y una sal que no está en el repositorio. Es estable, así que los análisis por proveedor siguen funcionando.
- Los nombres que aparecen tras "D.", "Dª", "Sr." en el texto del objeto se sustituyen por `[PERSONA]`.
- **Resultado:** 68.307 filas y 6.730 proveedores tratados como persona física.

## 5. Clasificación del objeto (HU4)

- El clasificador por reglas está en el notebook y asigna `GRUPO_GASTO`.
- En la UV, el **35,3 %** de los pagos (37,7 % del gasto) queda como "Suministros/servicios (sin detalle)". Este es el margen de mejora de la HU4.
- `observatorio.evaluacion_clasificacion` genera una muestra ciega de 100 objetos para que la etiquete cada miembro del equipo. Después calcula el acuerdo entre anotadores (kappa de Cohen y de Fleiss), la exactitud, la cobertura y la matriz de confusión. Instrucciones en [`validacion/README.md`](validacion/README.md).

## 6. Proveedores comunes y compra conjunta · `observatorio.proveedores_comunes` (HU6)

Solo cuentan empresas y personas físicas: universidades, entidades públicas y fundaciones suelen trabajar por convenio.

| Indicador | Valor |
|---|---|
| Proveedores comunes | **2.778** |
| Gasto de la UPV con proveedores comunes | **44,4 %** |
| Gasto de la UV con proveedores comunes | **63,4 %** |
| Candidatos a compra conjunta (≥ 50.000 € en **cada** universidad) | **147**, con 85,7 M€ en total |
| Gasto solapado de los candidatos (Σ min(UPV, UV)) | 25,3 M€ |

- **Ranking por categoría:** ordena las categorías por el gasto solapado de los proveedores comunes dentro de cada una. Las tres primeras son laboratorio, informática y libros.
- **Validación manual:** muestra de 50 emparejamientos para revisar a mano (GPR-58).

## 7–8. Alertas, dashboard e informe

- **Alertas (HU8) · `observatorio.alertas`:** mismo proveedor, unidad, tipo y año, con al menos 2 pagos, todos por debajo del umbral (15.000 €; 40.000 € en obras) y que juntos lo superan. Salen **2.712 alertas** (UPV 1.370, UV 1.342) por 102,36 M€. Con la regla de prioridad v2, documentada en el módulo: **581 Alta**, 1.104 Media y 1.027 Baja.
- **Dashboard (HU10) · `observatorio.powerbi`:** genera `observatorio_powerbi.xlsx`, con un modelo en estrella seudonimizado. El informe se monta en Power BI siguiendo [`powerbi/guia_powerbi.md`](powerbi/guia_powerbi.md).
- **Informe de compra conjunta (HU11):** parte de las salidas del paso 6.

## Ficheros de salida (`outputs/`, no se suben)

| Fichero | Paso |
|---|---|
| `upv_expedientes.csv`, `upv_lineas_con_expediente.csv`, `upv_expedientes_resumen.json` | 3 |
| `UP_UV_Final_seudonimizado.csv` | 4 |
| `proveedores_comunes.csv`, `candidatos_compra_conjunta.csv`, `ranking_categorias_compra_conjunta.csv`, `proveedores_comunes_resumen.json` | 6 |
| `evaluacion_clasificador.json`, `matriz_confusion_clasificador.csv` | 5 |
| `alertas_fraccionamiento.csv`, `alertas_resumen.json` | 7 |
| `observatorio_powerbi.xlsx`, `observatorio_powerbi_control.json` | 8 |
