# Pruebas con personas ajenas al equipo (GPR-111, GPR-116)

Las dos pruebas tiene que hacerlas **una persona que no haya trabajado en el proyecto**, por ejemplo alguien de otro grupo de la asignatura. Cada una dura unos 20 minutos. Quien la acompaña **solo observa y apunta**: no ayuda salvo que la persona se bloquee más de 3 minutos, y en ese caso lo anota.

Al terminar, rellena la tabla de la prueba en este fichero, súbelo y enlaza el commit en la tarea de Jira.

## GPR-111 · Prueba del dashboard

**Material:** el portátil con `Observatorio.pbix` abierto en la página 1 y sin filtros, y el [manual de uso](../manual_dashboard.md) disponible pero sin enseñarlo.

**Tareas que se le piden, en este orden:**

| # | Tarea | Respuesta correcta | Tiempo | ¿Lo consigue sin ayuda? | Observaciones |
|---|---|---|---|---|---|
| 1 | ¿Cuánto gastó la UV en contratos menores en 2022? | 35,2 M€ | | | |
| 2 | ¿Cuántas alertas de prioridad alta tiene la UPV? | 312 | | | |
| 3 | Busca la alerta de prioridad alta con más importe y explica con tus palabras por qué salta | La primera de la tabla; leer el motivo | | | |
| 4 | ¿Qué categoría tiene más potencial de compra conjunta? | Laboratorio e investigación | | | |
| 5 | Nombra un proveedor candidato a compra conjunta y cuánto le paga cada universidad | Cualquiera de la tabla de candidatos | | | |
| 6 | Deja el informe como estaba, sin filtros | Botón de restablecer | | | |

**Preguntas al final:**

| Pregunta | Respuesta |
|---|---|
| Del 1 al 5, ¿qué tan fácil ha sido encontrar lo que se pedía? | |
| ¿Qué te ha costado más? | |
| ¿Has entendido qué es una alerta y que no es una acusación? | |
| ¿Qué cambiarías? | |

**Datos de la prueba:** fecha ___ · probador (nombre o iniciales) ___ · acompañante ___

**Cambios que se hacen por el feedback:** _(crear un ticket en Jira por cada uno y enlazarlo aquí)_

## GPR-116 · Prueba de reproducción

**Material:** un ordenador con Python 3.10 o superior y Git, que no haya tenido nunca el proyecto. Se le da **solo** el enlace al repositorio y la sal del equipo, por un canal privado y nunca por el repositorio.

**Instrucción:** «Sigue el README para instalar el proyecto, pasar los tests y generar el Excel del dashboard».

| Paso del README | ¿Funciona? | Tiempo | Problema encontrado |
|---|---|---|---|
| Clonar e instalar dependencias | | | |
| Sacar `UP_UV_Final.csv` de la rama `DATASET_FINAL` | | | |
| `python -m pytest` (deben pasar todos) | | | |
| Expedientes (HU3) | | | |
| Proveedores comunes (HU6) | | | |
| Alertas (HU8): 2.712 alertas, 581 altas | | | |
| Excel de Power BI (HU10) | | | |

**Datos de la prueba:** fecha ___ · probador ___ · sistema operativo ___ · versión de Python ___

### Ensayo previo hecho por el equipo (24/11)

Antes de la prueba externa se repitió el README entero en un clon limpio (Linux, Python 3, entorno virtual nuevo):

- Los 93 tests pasan.
- Todos los pasos dan las cifras documentadas: 210.897 expedientes, 2.778 proveedores comunes, 147 candidatos, 2.712 alertas y el Excel de 8 tablas.

Problemas encontrados y corregidos en el README:

- Faltaba cómo poner las variables en Windows (PowerShell).
- No se decía que la evaluación del clasificador falla hasta que esté hecho el etiquetado de GPR-52.
- Un aviso de pandas en los tests.
