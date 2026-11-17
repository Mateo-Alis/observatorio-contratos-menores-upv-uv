"""Observatorio de contratos menores UPV–UV: pipeline de análisis.

Módulos:
    carga                     lectura de los ficheros publicados y del dataset unificado
    expedientes               HU3 · agregación de las líneas de la UPV por expediente
    seudonimizacion           HU7 · detección de personas físicas y seudónimos con sal
    proveedores_comunes       HU6 · proveedores comunes UPV–UV y ranking de compra conjunta
    evaluacion_clasificacion  HU4 · muestra de etiquetado y evaluación del clasificador
"""

__version__ = "0.2.0"
