# Manual de uso del dashboard (GPR-115)

Para quien consulta el informe de Power BI `Observatorio.pbix`: personal de contratación, de gerencia o de control interno de la UPV o la UV. Para montarlo, ver [`powerbi/guia_powerbi.md`](powerbi/guia_powerbi.md).

## Qué es

El dashboard reúne los **contratos menores que publican la UPV y la UV entre 2019 y 2023**: 431.538 pagos y 343,9 M€. Responde a tres preguntas:

1. **¿En qué se gasta?** Página *Resumen*.
2. **¿Dónde puede haber contratos partidos para no superar el umbral del contrato menor?** Página *Alertas*.
3. **¿A qué proveedores compran las dos universidades y podrían negociar juntas?** Página *Compra conjunta*.

Las personas físicas que aparecen como proveedor se muestran con un código `PER-xxxxxxxx` en lugar de su nombre.

## Filtros

Arriba a la derecha de cada página hay dos filtros que se aplican a la vez en las tres:

- **Universidad:** pulsa UPV o UV. Para volver a las dos, pulsa la que está marcada.
- **Año:** marca uno o varios. Sin ninguno marcado, se ven todos.

En la página de alertas hay además filtros de prioridad, patrón, categoría y unidad. En el de unidad se puede escribir para buscar.

Pulsar una barra o un sector de un gráfico **filtra el resto de la página**. Pulsa de nuevo para quitarlo. Para borrar todos los filtros, usa el botón de la goma de la barra superior (**Restablecer valores predeterminados**).

## Página 1 · Resumen

| Elemento | Qué muestra |
|---|---|
| Gasto total, Nº pagos | Volumen de contratos menores con los filtros puestos |
| Alertas de prioridad alta | Cuántas alertas merecen revisión preferente |
| % gasto con proveedores comunes | Parte del gasto con empresas que venden a las dos universidades |
| Gasto por año | Evolución anual de cada universidad |
| Gasto por categoría | Las 10 categorías con más gasto |
| Pagos sin categoría concreta | Parte de los pagos cuyo texto no permite saber qué se compró. Casi todos son de la UV. |

## Página 2 · Alertas de posible fraccionamiento

**Cuándo salta una alerta:** cuando una misma unidad paga a un mismo proveedor, en un mismo año y por el mismo tipo de contrato, **varios pagos que están todos por debajo de 15.000 €** (40.000 € en obras) **y que juntos superan esa cifra**. En la UV no se publica la unidad que compra, así que se agrupa la universidad entera.

**Prioridad:**

- **Alta:** pocos pagos grandes que juntos llegan al menos a 1,5 veces el umbral, o que lo superan dentro de un solo trimestre (solo la UV publica el trimestre). Es el patrón típico de un contrato partido.
- **Media:** pocos pagos grandes que superan el umbral por poco, o muchos pagos pequeños que suman al menos 3 veces el umbral. Estos últimos suelen ser gasto recurrente que podría ir a un contrato o acuerdo marco.
- **Baja:** muchos pagos pequeños que superan el umbral por poco.

**Cómo usar la tabla:**

1. Filtra tu universidad y tu unidad.
2. Ordena por **Prioridad** y después por **Importe**: pulsa la cabecera de la columna.
3. Lee la columna **Motivo**: explica con cifras por qué salta la alerta.
4. Revisa los expedientes de esa unidad y ese proveedor en el sistema de contabilidad.

> **Una alerta es un indicio a revisar, no una acusación.** Hay explicaciones legítimas: pedidos de material fungible a lo largo del año, encargos de distintos grupos de investigación de una misma unidad…

## Página 3 · Compra conjunta

| Elemento | Qué muestra |
|---|---|
| Proveedores comunes | Empresas a las que compran las dos universidades (2.778) |
| Candidatos a compra conjunta | Las que superan 50.000 € en **cada** universidad (147) |
| Gasto solapado | Para cada proveedor, lo menor entre lo que le paga cada universidad. Es una estimación prudente de lo que se podría negociar en común. |
| Oportunidades por categoría | Categorías ordenadas por gasto solapado: laboratorio, informática, libros… |
| Tabla de candidatos | Proveedor a proveedor, ordenados por gasto solapado |

Esta página usa los **totales de 2019–2023**: los filtros de año y universidad no la cambian. El informe de compra conjunta (HU11) amplía estas cifras.

## Limitaciones

- **Fechas:** la UPV no publica la fecha de cada pago, así que las alertas trabajan por año.
- **Categorías:** en la UV, el 35,3 % de los pagos no describe qué se compra y queda como «sin detalle».
- **Proveedores:** se unifican por nombre y NIF. Una misma empresa con nombres muy distintos puede aparecer dos veces.
- **Seudonimización:** una regla detecta los nombres de persona, pero no los reconoce todos. Por eso el informe **no se publica en abierto**.

## Preguntas frecuentes

**¿Por qué no cuadran las cifras con otra fuente?** Se usan los importes publicados por cada universidad y no se cuentan los pagos de importe cero. En la UPV, una línea de gasto es un pago; varias líneas pueden pertenecer al mismo expediente.

**¿Cómo se actualiza?** Con los ficheros de un año nuevo se vuelve a ejecutar el pipeline (`README.md`) y, en Power BI, se pulsa **Inicio → Actualizar**.
