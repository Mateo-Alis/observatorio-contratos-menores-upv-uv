# Datos personales y seudonimización (HU7)

Incidencias: GPR-48 (HU7), GPR-79, GPR-80, GPR-81 · Riesgo R5 (protección de datos)

## 1. Qué datos personales hay (GPR-79)

Revisados los ficheros de la UPV (CSV 2019–2023), de la UV (XLS/XLSX 2019–2023) y el dataset unificado `UP_UV_Final.csv`:

| Campo | Fuente | ¿Dato personal? | Tratamiento |
|---|---|---|---|
| `TERCERO` / `Proveedor` / `Nombre adjudicatario` | UPV, UV, unificado | **Sí, cuando el proveedor es una persona física** (autónomos, profesionales, particulares). No, cuando es una empresa o entidad. | Seudónimo `PER-xxxxxxxx` |
| `PROVEEDOR_CLAVE`, `GRUPO_EMPRESARIAL` | Unificado | Igual que el anterior (derivan del nombre) | Seudónimo a partir de su propio valor, para conservar la agrupación |
| `NIF adjudicatario` | UV | **Sí** en personas físicas. La UV ya lo publica enmascarado (`292****1P`). | Se usa solo para detectar personas físicas y se **elimina** de la salida |
| `Objeto` / `Objeto_UV` | UV | **A veces**: nombra a terceros (p. ej. "billetes de tren para D. Javier …", "tesis doctoral de Dª …"). 270 filas contienen un tratamiento (D., Dª, Sr., …) | El nombre que sigue al tratamiento se sustituye por `[PERSONA]` |
| `EXPEDIENTE`, `Identificador` | UPV, UV | No | Sin cambios |
| `CENTRO DIRECTIVO`, `Unidad funcional`, importes, fechas, conceptos | UPV, UV | No | Sin cambios |

## 2. Cómo se detecta una persona física

1. **Por NIF** (solo UV): enmascarado o con forma de DNI/NIE → persona física. CIF de sociedad (A, B, G, …) → no.
2. **Por lista de la UV**: los nombres que la UV publica con NIF de persona física (1.597) se reconocen también en la UPV, que no publica NIF.
3. **Por el nombre**, cuando no hay NIF: sin forma societaria ni palabras de organización, de 2 a 6 palabras, con un nombre de pila conocido o en formato "APELLIDOS, NOMBRE".

Precisión de la regla por nombre, medida con el NIF de la UV como referencia (5.752 pares nombre–NIF, 1.920 personas):

| | Valor |
|---|---|
| Precisión | 99,9 % (2 falsos positivos) |
| Exhaustividad | 83,4 % (318 personas no detectadas solo por el nombre) |

En la UV, el NIF y la lista cubren a las personas que la regla por nombre no ve. En la UPV, el riesgo residual son esas personas con nombres poco frecuentes. Ante la duda, la regla prefiere seudonimizar de más: una empresa con código es un problema menor que una persona con nombre.

Resultado sobre el dataset unificado (431.538 filas): 68.307 filas y 6.730 proveedores tratados como persona física (UPV 32.279 filas, UV 36.028).

## 3. Cómo se seudonimiza (GPR-80)

- HMAC-SHA256 del nombre normalizado con una **sal secreta**. Código resultante: `PER-` + 8 caracteres.
- La misma persona recibe siempre el mismo código con la misma sal, así que los análisis por proveedor (alertas, proveedores comunes) siguen funcionando.
- Sin la sal no se puede volver al nombre ni comprobar un nombre candidato.
- **La sal nunca está en el repositorio.** Se lee de la variable `OBSERVATORIO_SAL` o del fichero `~/.observatorio/sal.txt` (permisos 600), creado con `python -m observatorio.seudonimizacion --generar-sal`. Solo la tiene quien ejecuta el pipeline.

## 4. Datos crudos en el repositorio (GPR-81)

**Situación actual.** El `.gitignore` excluye `data/*` desde el inicio, pero los ficheros de la UPV y la UV se subieron desde la web de GitHub, que no aplica el `.gitignore`. Además, el repositorio es **público** (se hizo público para poder proteger `main`).

**Valoración.**
- Los ficheros son datos abiertos que ya publican los portales de transparencia de la UPV y la UV, así que tenerlos en el repositorio no expone nada nuevo.
- Lo sensible son las **salidas**: una lista que asocia a una persona con nombre a una "alerta de posible fraccionamiento" no debe publicarse.

**Decisión propuesta (pendiente de aprobar en el equipo):**
1. Ninguna salida con nombres se sube al repositorio. `outputs/` queda excluido en el `.gitignore` y solo se comparten salidas seudonimizadas.
2. El dashboard y el informe usan solo datos seudonimizados.
3. Quitar los ficheros crudos de `data/` en un PR aparte y documentar en el README de dónde descargarlos. Siguen en el historial de git, pero al ser datos públicos no es necesario reescribirlo.

GPR-81 se cierra cuando el equipo apruebe el punto 3 (o decida mantener los ficheros y lo anote aquí).
