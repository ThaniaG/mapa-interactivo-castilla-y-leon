# Datos de origen

Esta carpeta contiene los ficheros originales (Excel, CSV, JSON, GeoJSON) descargados
de las fuentes oficiales que utilizan los scripts de `scripts/` para generar los
`datos_*.js` que consume el dashboard. Se incluyen para que el proceso sea
reproducible sin depender de que las webs de origen mantengan el mismo contenido
en el futuro.

La procedencia exacta de cada fichero (organismo, URL de descarga y módulo del
dashboard al que alimenta) está documentada en la Tabla C.1 de la memoria del TFM
(Apéndice C, Documento de Diseño).

## Excepción: microdatos de nacimientos y defunciones

Los microdatos de nacimientos y defunciones del INE (Movimiento Natural de la
Población) **no** se incluyen en este repositorio: son ficheros nacionales (no
solo de Castilla y León) distribuidos en varios formatos redundantes (CSV, SAS,
SPSS, STATA, R), y varios de ellos superan el límite de 100 MB por fichero de
GitHub. El script `scripts/generar_datos_vital.py` descarga y filtra estos datos
automáticamente para Castilla y León; los ficheros de origen pueden obtenerse de
nuevo desde la URL indicada en la Tabla C.1.
