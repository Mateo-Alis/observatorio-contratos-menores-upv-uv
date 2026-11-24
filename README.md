# Observatorio de contratos menores UPV–UV

Proyecto de equipo de la asignatura de Gestión de Proyectos (GPR). Gestión en Jira (proyecto **GPR**), metodología Scrum.

Une los contratos menores que publican la UPV y la Universitat de València (2019–2023) y produce:

- **Alertas de posible fraccionamiento** (HU8).
- **Proveedores comunes** y **oportunidades de compra conjunta** (HU6, HU11).
- **Clasificación del objeto** del contrato en una taxonomía común (HU4).
- Todo ello con los proveedores que son personas físicas **seudonimizados** (HU7).

## Equipo

| Rol | Nombre |
|---|---|
| Miembro | Mateo Alís |
| Miembro | Pablo Huguet |
| Miembro | Jiale Mao |
| Miembro | Manuel Caballero |
| Miembro | Vicente Llácer |

## Instalación (GPR-114)

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/Mateo-Alis/observatorio-contratos-menores-upv-uv
cd observatorio-contratos-menores-upv-uv
python -m venv .venv && source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Datos de entrada:**
- `data/*_UPV.csv` y `data/*_UV.xls(x)`: ficheros publicados por cada universidad, uno por año.
- `UP_UV_Final.csv`: dataset unificado del equipo. Está comprimido en la rama `DATASET_FINAL` (`data/DATASET_FINAL.zip`). Para sacarlo:

  ```bash
  git show origin/DATASET_FINAL:data/DATASET_FINAL.zip > DATASET_FINAL.zip && unzip DATASET_FINAL.zip
  ```

## Ejecución

Todos los módulos se lanzan con `PYTHONPATH=src python -m observatorio.<módulo>` y escriben en `outputs/`, que no se sube al repositorio.

En **Windows (PowerShell)**, en lugar de `export` se usa:

```powershell
$env:PYTHONPATH = "src"; $env:OBSERVATORIO_SAL = "<la sal del equipo>"; $DATASET = "DATASET_FINAL/UP_UV_Final.csv"
```

**Tiempos aproximados** en un portátil:

| Paso | Tiempo |
|---|---|
| Expedientes | 30 s |
| Seudonimización | 20 s |
| Proveedores comunes | 10 s |
| Alertas | 2 s |
| Excel de Power BI | 40 s |

La evaluación del clasificador da error hasta que la muestra de GPR-52 esté etiquetada.

```bash
export PYTHONPATH=src
DATASET=DATASET_FINAL/UP_UV_Final.csv

# HU3 · Agregar las líneas de la UPV por expediente
python -m observatorio.expedientes --datos data --salida outputs

# HU7 · Seudonimizar personas físicas (la sal se crea una vez, fuera del repositorio)
python -m observatorio.seudonimizacion --generar-sal
python -m observatorio.seudonimizacion --entrada $DATASET --uv-crudos data --salida outputs

# HU6 · Proveedores comunes, candidatos y ranking de compra conjunta
python -m observatorio.proveedores_comunes --entrada $DATASET --salida outputs

# HU4 · Clasificador por reglas (la v2 es una propuesta, ver docs/pipeline.md)
python -m observatorio.clasificacion --entrada $DATASET --salida outputs --version 2

# HU4 · Evaluación del clasificador (cuando GPR-52 esté etiquetado, ver docs/validacion/README.md)
python -m observatorio.evaluacion_clasificacion evaluar \
    --etiquetado docs/validacion/GPR-52_etiquetado_muestra100.csv \
    --prediccion docs/validacion/GPR-52_etiquetado_muestra100_prediccion.csv

# HU8 · Alertas de posible fraccionamiento
python -m observatorio.alertas --entrada $DATASET --salida outputs

# HU10 · Excel para el dashboard de Power BI (ver docs/powerbi/guia_powerbi.md)
python -m observatorio.powerbi --entrada $DATASET --uv-crudos data --salida outputs
```

**Tests:**

```bash
python -m pytest
```

## Estructura del repositorio

```
data/               Ficheros publicados por la UPV y la UV (ver docs/datos_personales.md)
docs/               Documentos del proyecto, pipeline, datos personales y validaciones manuales
  pipeline.md       Descripción del pipeline paso a paso (GPR-115)
  datos_personales.md
  validacion/       Muestras para revisar a mano (GPR-52, GPR-58)
  powerbi/          Guía de montaje del dashboard y tema de colores (HU10)
  manual_dashboard.md  Manual de uso del dashboard (GPR-115)
  pruebas/          Protocolos de prueba con personas ajenas (GPR-111, GPR-116)
notebooks/          Exploración y EDA
src/observatorio/   Código del pipeline
  carga.py                    Lectura de ficheros
  expedientes.py              HU3 · agregación por expediente
  seudonimizacion.py          HU7 · seudonimización
  proveedores_comunes.py      HU6 · proveedores comunes y compra conjunta
  clasificacion.py            HU4 · clasificador por reglas (v1 y v2)
  evaluacion_clasificacion.py HU4 · etiquetado y evaluación
  alertas.py                  HU8 · alertas de fraccionamiento
  powerbi.py                  HU10 · datos para el dashboard de Power BI
tests/              Tests (pytest) con casos reales de los ficheros publicados
outputs/            Resultados (no se sube)
```

## Flujo de trabajo

1. Toda tarea parte de una incidencia de Jira (clave `GPR-n`).
2. `main` está **protegida**: no se hace push directo. Todo cambio entra por Pull Request.
3. Cada PR necesita **al menos 1 aprobación** de otro miembro del equipo antes de fusionarse.
4. Al abrir el PR, la incidencia pasa a **En revisión**; al fusionarlo, a **finalizada**.

## Convención de ramas

`<tipo>/GPR-<n>-<descripcion-corta>`

| Tipo | Uso |
|---|---|
| `feature` | Nueva funcionalidad o historia de usuario |
| `fix` | Corrección de errores |
| `docs` | Documentación |
| `chore` | Configuración, mantenimiento |

Ejemplos: `feature/GPR-40-carga-datos-upv`, `docs/GPR-21-readme`.

## Convención de commits

`GPR-<n>: <verbo en infinitivo/imperativo> <qué se hace>`

Ejemplos:

- `GPR-20: Crear estructura inicial del repositorio`
- `GPR-40: Añadir carga del CSV de la UPV`

Reglas: la clave de Jira siempre al principio, mensaje breve (≤ 72 caracteres) y un cambio lógico por commit.

## Pull Requests

- Título: `GPR-<n>: <resumen>`.
- Descripción: qué se hace, cómo se ha probado y enlace a la incidencia.
- Se asigna a otro miembro como revisor y se fusiona con *squash*.

## Registro de horas

Cada miembro registra el tiempo dedicado en la incidencia correspondiente de Jira (worklog) y lo contrasta con la estimación.
