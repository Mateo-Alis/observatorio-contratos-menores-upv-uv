# Dashboard en Power BI (HU10 · GPR-108, GPR-109, GPR-110)

Guía para montar el informe `Observatorio.pbix` en Power BI Desktop. Los datos llegan ya calculados y seudonimizados en un único Excel, así que en Power BI solo hay que cargar, relacionar, pegar las medidas y colocar los visuales. Tiempo estimado: 2–3 horas.

- **Tecnología (GPR-108):** Power BI Desktop, decisión del equipo. El informe se entrega como `.pbix` y, si hay cuenta de la UPV, se publica en Power BI Service.
- **Datos (GPR-109):** `outputs/observatorio_powerbi.xlsx`, generado por `observatorio.powerbi`.
- **Informe (GPR-110):** tres páginas: Resumen, Alertas y Compra conjunta.

## 1. Generar el Excel

```bash
export OBSERVATORIO_SAL=...        # o ~/.observatorio/sal.txt; la misma sal para todo el equipo
PYTHONPATH=src python -m observatorio.powerbi --entrada UP_UV_Final.csv --uv-crudos data --salida outputs
```

Tarda unos 30 segundos. Además del Excel, deja `outputs/observatorio_powerbi_control.json` con las cifras que el informe debe mostrar (apartado 6).

Se usa Excel y no CSV porque Power BI lee los números de Excel sin depender de la configuración regional. En CSV, la coma decimal da problemas.

**No subas el Excel ni el `.pbix` al repositorio** (están en `outputs/`). Los proveedores que son persona física salen como `PER-xxxxxxxx`, pero la detección no es perfecta (ver [`../datos_personales.md`](../datos_personales.md)).

## 2. Cargar los datos

1. Power BI Desktop → **Obtener datos → Libro de Excel** → `observatorio_powerbi.xlsx`.
2. Marca las 8 hojas → **Cargar**. No hace falta transformar nada.
3. **Vista → Temas → Buscar temas** → `docs/powerbi/tema_observatorio.json`.
4. Comprueba en la vista de datos que `Gasto`, `Importe`, `GastoUPV`, `GastoUV` y `GastoSolapado` son **número decimal** y `Anio` es **número entero**. Ponles formato moneda en euros (`€ Euro (123 €)`).

| Hoja | Filas | Qué es |
|---|---|---|
| `Universidad` | 2 | Dimensión: UPV, UV |
| `Anio` | 5 | Dimensión: 2019–2023 |
| `Categoria` | 25 | Dimensión: categorías de gasto (`SinClasificar` = Sí/No) |
| `Proveedor` | 25.986 | Dimensión: proveedor visible, tipo y marcas `Comun`, `Candidato`, `Comercial`, `Seudonimizado` |
| `Pagos` | 126.296 | Hechos: pagos agregados por universidad, año, trimestre, unidad, categoría y proveedor (`NumPagos`, `Gasto`) |
| `Alertas` | 2.712 | Hechos: alertas de fraccionamiento (HU8) |
| `ProveedoresComunes` | 2.778 | Hechos: proveedores con gasto en las dos universidades (HU6), totales 2019–2023 |
| `RankingCategorias` | 19 | Hechos: oportunidades de compra conjunta por categoría (HU6) |

## 3. Relaciones

En **Vista de modelo**, borra las relaciones que Power BI haya creado solo y crea estas. Todas **de varios a uno (*:1)** y con dirección de filtro **única**, de la dimensión al hecho:

| Hecho (varios) | Columna | Dimensión (uno) |
|---|---|---|
| `Pagos` | `Universidad` | `Universidad[Universidad]` |
| `Pagos` | `Anio` | `Anio[Anio]` |
| `Pagos` | `Categoria` | `Categoria[Categoria]` |
| `Pagos` | `Proveedor` | `Proveedor[Proveedor]` |
| `Alertas` | `Universidad` | `Universidad[Universidad]` |
| `Alertas` | `Anio` | `Anio[Anio]` |
| `Alertas` | `Categoria` | `Categoria[Categoria]` |
| `Alertas` | `Proveedor` | `Proveedor[Proveedor]` |
| `ProveedoresComunes` | `Proveedor` | `Proveedor[Proveedor]` |
| `ProveedoresComunes` | `Categoria` | `Categoria[Categoria]` |
| `RankingCategorias` | `Categoria` | `Categoria[Categoria]` (Power BI la pondrá 1:1; déjala así) |

`ProveedoresComunes` y `RankingCategorias` son totales de 2019–2023: **los filtros de año y de universidad no les afectan**. Pon una nota en la página 3.

Ordena columnas (**Herramientas de columnas → Ordenar por columna**): `Alertas[Prioridad]` por `Alertas[OrdenPrioridad]`, `RankingCategorias[Categoria]` por `RankingCategorias[Ranking]`.

## 4. Medidas DAX

Crea una tabla vacía para las medidas (**Inicio → Especificar datos** → nombre `_Medidas` → Cargar) y añade estas con **Nueva medida**:

```dax
Gasto total = SUM ( Pagos[Gasto] )
Nº pagos = SUM ( Pagos[NumPagos] )
Nº proveedores = DISTINCTCOUNT ( Pagos[Proveedor] )
Gasto UPV = CALCULATE ( [Gasto total], Universidad[Universidad] = "UPV" )
Gasto UV = CALCULATE ( [Gasto total], Universidad[Universidad] = "UV" )
Pago medio = DIVIDE ( [Gasto total], [Nº pagos] )

% gasto con proveedores comunes =
DIVIDE (
    CALCULATE ( [Gasto total], Proveedor[Comercial] = "Sí", Proveedor[Comun] = "Sí" ),
    CALCULATE ( [Gasto total], Proveedor[Comercial] = "Sí" )
)

% pagos sin clasificar =
DIVIDE ( CALCULATE ( [Nº pagos], Categoria[SinClasificar] = "Sí" ), [Nº pagos] )

Alertas = COUNTROWS ( Alertas )
Alertas prioridad alta = CALCULATE ( [Alertas], Alertas[Prioridad] = "Alta" )
Importe en alertas = SUM ( Alertas[Importe] )
% gasto en alertas = DIVIDE ( [Importe en alertas], [Gasto total] )

Proveedores comunes = COUNTROWS ( ProveedoresComunes )
Candidatos compra conjunta = CALCULATE ( COUNTROWS ( ProveedoresComunes ), ProveedoresComunes[Candidato] = "Sí" )
Gasto candidatos = CALCULATE ( SUM ( ProveedoresComunes[GastoTotal] ), ProveedoresComunes[Candidato] = "Sí" )
Gasto solapado candidatos = CALCULATE ( SUM ( ProveedoresComunes[GastoSolapado] ), ProveedoresComunes[Candidato] = "Sí" )
```

Formato: las de gasto e importe en moneda sin decimales; las de `%` en porcentaje con 1 decimal.

`% gasto con proveedores comunes` usa `Pagos`, así que **sí responde** a los filtros de año y universidad. Con la universidad filtrada da el 44,4 % (UPV) y el 63,4 % (UV).

## 5. Páginas

Tamaño de página 16:9. En las tres, arriba a la derecha, una **segmentación** de `Universidad[Universidad]` (botones) y otra de `Anio[Anio]` (desplegable, selección múltiple). Sincronízalas entre páginas: **Vista → Sincronizar segmentaciones**.

Abajo, en todas, un cuadro de texto: *«Datos públicos de contratos menores 2019–2023 (UPV y UV). Las personas físicas aparecen seudonimizadas (PER-…). Una alerta es un indicio a revisar, no una acusación.»*

### Página 1 · Resumen

| Visual | Campos |
|---|---|
| 4 **tarjetas** | `Gasto total`, `Nº pagos`, `Alertas prioridad alta`, `% gasto con proveedores comunes` |
| **Gráfico de columnas agrupadas** «Gasto por año» | Eje `Anio[Anio]`, leyenda `Universidad[Universidad]`, valores `Gasto total` |
| **Gráfico de barras** «Gasto por categoría» | Eje `Categoria[Categoria]`, valores `Gasto total`, ordenado de mayor a menor (top 10 con filtro de *N superior*) |
| **Tarjeta** pequeña | `% pagos sin clasificar` con el título «Pagos sin categoría concreta» |

### Página 2 · Alertas de fraccionamiento

| Visual | Campos |
|---|---|
| Segmentaciones extra | `Alertas[Prioridad]`, `Alertas[Patron]`, `Categoria[Categoria]`, `Alertas[Unidad]` (con búsqueda) |
| 3 **tarjetas** | `Alertas`, `Alertas prioridad alta`, `Importe en alertas` |
| **Columnas apiladas** «Alertas por universidad y prioridad» | Eje `Universidad[Universidad]`, leyenda `Alertas[Prioridad]`, valores `Alertas`. Colores: Alta `#C0392B`, Media `#E6A23C`, Baja `#8C9BAB` |
| **Barras** «Unidades con más alertas» | Eje `Alertas[Unidad]`, valores `Alertas`, top 10 |
| **Tabla** de alertas | `ID`, `Prioridad`, `Universidad`, `Anio`, `Unidad`, `Proveedor`, `Categoria`, `NumPagos`, `Importe`, `VecesUmbral`, `Motivo`. Ordenada por `Prioridad` y luego `Importe` descendente. Formato condicional en `VecesUmbral` (escala de colores) |

### Página 3 · Compra conjunta

| Visual | Campos |
|---|---|
| 3 **tarjetas** | `Proveedores comunes`, `Candidatos compra conjunta`, `Gasto solapado candidatos` |
| **Barras** «Oportunidades por categoría» | Eje `RankingCategorias[Categoria]`, valores `GastoSolapado`, top 10 |
| **Tabla** de categorías | `Ranking`, `Categoria`, `ProveedoresComunes`, `GastoUPV`, `GastoUV`, `GastoSolapado`, `ConcentracionTop3` (porcentaje), `PrincipalesProveedores` |
| **Tabla** de candidatos | `ProveedoresComunes`: `Proveedor`, `Categoria`, `GastoUPV`, `GastoUV`, `GastoSolapado`, con filtro de visual `Candidato = Sí`, ordenada por `GastoSolapado` |
| **Gráfico de dispersión** (opcional) | X `GastoUPV`, Y `GastoUV`, detalles `Proveedor`, filtro `Candidato = Sí` |

Nota en la página: *«Totales 2019–2023: los filtros de año y universidad no se aplican a esta página. Gasto solapado = mínimo entre lo que gasta cada universidad con el proveedor.»*

## 6. Comprobar el informe (criterios de aceptación)

Sin ningún filtro, el informe tiene que mostrar estas cifras (están también en `observatorio_powerbi_control.json`):

| Medida | Valor esperado |
|---|---|
| Gasto total | 343.902.529 € (UPV 186,6 M€ · UV 157,3 M€) |
| Nº pagos | 431.538 (UPV 217.244 · UV 214.294) |
| Alertas | 2.712 (UPV 1.370 · UV 1.342) |
| Alertas prioridad alta | 581 (UPV 312 · UV 269) · Media 1.104 · Baja 1.027 |
| Importe en alertas | 102,36 M€ |
| % gasto con proveedores comunes | UPV 44,4 % · UV 63,4 % |
| Proveedores comunes | 2.778 |
| Candidatos compra conjunta | 147 · gasto 85,7 M€ · solapado 25,3 M€ |
| Top 3 categorías (gasto solapado) | Laboratorio 8,4 M€ · Informática 4,3 M€ · Libros 2,4 M€ |
| % pagos sin clasificar (UV) | 35,3 % |
| Gasto por año (M€) | UPV 31,4 · 30,2 · 35,4 · 40,8 · 48,9 — UV 26,9 · 24,6 · 32,2 · 35,2 · 38,4 |

Si alguna no cuadra, revisa primero las relaciones (apartado 3) y el tipo de las columnas (apartado 2.4).

Prueba también:

- Filtrar **UV + 2023** cambia todas las tarjetas de las páginas 1 y 2.
- Pulsar una barra de prioridad filtra la tabla de alertas.
- Buscar un proveedor en la segmentación encuentra sus alertas.
- No aparece ningún nombre de persona física en las tablas: busca, por ejemplo, apellidos frecuentes como «GARCIA» o «MARTINEZ» y comprueba que solo salen empresas.

## 7. Entregar

1. Guarda como `Observatorio.pbix` y súbelo a la carpeta compartida del equipo, **no al repositorio**.
2. Opcional: **Publicar** en Power BI Service con la cuenta de la UPV, en un área de trabajo del equipo. Comparte con el profesor, no con «Publicar en la web», porque eso hace público el informe.
3. Exporta las tres páginas a PDF (**Archivo → Exportar → PDF**) y adjúntalo a GPR-110 como evidencia.
