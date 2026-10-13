# Observatorio de contratos menores UPV–UV

Proyecto de equipo de la asignatura de Gestión de Proyectos (GPR). Gestión en Jira (proyecto **GPR**), metodología Scrum.

## Equipo

| Rol | Nombre |
|---|---|
| Miembro | Mateo Alís |
| Miembro | Pablo Huguet |
| Miembro | Jiale |
| Miembro | Manuel Caballero |
| Miembro | Vicente |

## Estructura del repositorio

```
/data        Datos de entrada (no se suben los ficheros pesados)
/notebooks   Exploración y EDA
/src         Código de ingesta, clasificación y detección de anomalías
/docs        Documentación del proyecto
README.md
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
