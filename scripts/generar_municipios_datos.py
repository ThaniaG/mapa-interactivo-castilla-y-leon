"""
generar_datos.py
════════════════
Script que combina los archivos GeoJSON (geometrías de municipios)
con los datos de población del INE (JSON 2025) y genera un único
archivo datos.js listo para usar en el dashboard web.

¿Por qué es necesario este script?
Al abrir un HTML directamente desde el explorador de archivos (doble clic),
el navegador bloquea la carga de archivos externos por seguridad (protocolo file://).
La solución es generar un archivo .js con los datos ya embebidos,
que el navegador sí permite cargar.

Cómo ejecutar:
    python generar_datos.py

Resultado:
    Genera el archivo datos.js en la carpeta del proyecto.
"""

import json
import os

# ── Rutas de los archivos ──────────────────────────────────────────
# Carpeta raíz del proyecto (donde está este script)
BASE = os.path.dirname(os.path.abspath(__file__))

# Carpeta con los GeoJSON de límites municipales
BASE_GEO = os.path.join(BASE, 'limites', 'datos')

# Carpeta con los JSON de población (generados en el Paso anterior)
BASE_POB = os.path.join(BASE, 'Poblacion JSON 2025')

# Archivo de salida que usará el dashboard
SALIDA = os.path.join(BASE, 'datos_municipios.js')

# ── Definición de provincias ───────────────────────────────────────
# Cada entrada: (archivo GeoJSON, archivo población, nombre visible, clave interna)
# La clave interna debe coincidir con los valores del selector de provincia en el HTML
PROVINCIAS = [
    ('AVILA',      'Avila2025',      'Ávila',      'avila'),
    ('BURGOS',     'Burgos2025',     'Burgos',     'burgos'),
    ('LEON',       'Leon2025',       'León',       'leon'),
    ('PALENCIA',   'Palencia2025',   'Palencia',   'palencia'),
    ('SALAMANCA',  'Salamanca2025',  'Salamanca',  'salamanca'),
    ('SEGOVIA',    'Segovia2025',    'Segovia',    'segovia'),
    ('SORIA',      'Soria2025',      'Soria',      'soria'),
    ('VALLADOLID', 'Valladolid2025', 'Valladolid', 'valladolid'),
    ('ZAMORA',     'Zamora2025',     'Zamora',     'zamora'),
]

# ── Procesamiento ─────────────────────────────────────────────────
features_combinados = []   # Lista final de features del GeoJSON combinado
total_sin_datos = 0        # Contador de municipios sin datos de población

print('Procesando provincias...')

for geo_file, pob_file, nombre_prov, clave_prov in PROVINCIAS:

    # Leer el GeoJSON de límites municipales
    ruta_geo = os.path.join(BASE_GEO, geo_file + '.geojson')
    with open(ruta_geo, encoding='utf-8') as f:
        geo = json.load(f)

    # Leer el JSON de población
    ruta_pob = os.path.join(BASE_POB, pob_file + '.json')
    with open(ruta_pob, encoding='utf-8') as f:
        pob = json.load(f)

    # Crear un índice de población por código INE para búsqueda rápida
    # Ejemplo: {'05001': {'nombre': 'Adanero', 'total': 207, ...}, ...}
    indice_pob = {m['codigo']: m for m in pob['municipios']}

    municipios_procesados = 0
    municipios_sin_datos  = 0

    for feature in geo['features']:
        # El GeoJSON guarda el código INE como número (ej: 5070)
        # Lo convertimos a string de 5 dígitos con cero inicial (ej: "05070")
        codigo_ine  = feature['properties']['CODIGO_INE']
        codigo_str  = str(int(codigo_ine)).zfill(5)

        datos_muni = indice_pob.get(codigo_str)

        if datos_muni:
            # Municipio encontrado: añadir datos de población a las propiedades
            feature['properties'] = {
                'codigo':    codigo_str,
                'nombre':    datos_muni['nombre'],
                'provincia': nombre_prov,
                'prov_key':  clave_prov,      # Clave para el filtro del selector
                'total':     datos_muni['total'],
                'hombres':   datos_muni['hombres'],
                'mujeres':   datos_muni['mujeres'],
            }
            municipios_procesados += 1
        else:
            # Entidad geográfica sin datos de población en el INE — se omite del mapa
            municipios_sin_datos += 1
            total_sin_datos      += 1
            continue

        features_combinados.append(feature)

    print(f'  {nombre_prov}: {municipios_procesados} municipios con datos, {municipios_sin_datos} sin datos')

# ── Crear el GeoJSON combinado ────────────────────────────────────
geojson_combinado = {
    'type': 'FeatureCollection',
    'features': features_combinados
}

# ── Escribir el archivo datos.js ──────────────────────────────────
# Se usa separators=(',', ':') para generar JSON compacto (sin espacios extra)
# ensure_ascii=False para conservar tildes y caracteres especiales
contenido_js = (
    '// datos.js — Generado automáticamente por generar_datos.py\n'
    '// Contiene los límites municipales de Castilla y León\n'
    '// combinados con los datos de población del INE (2025).\n'
    '// NO editar manualmente. Para regenerar, ejecutar: python generar_datos.py\n\n'
    'const DATOS_GEO = '
    + json.dumps(geojson_combinado, ensure_ascii=False, separators=(',', ':'))
    + ';'
)

with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write(contenido_js)

# ── Resumen ───────────────────────────────────────────────────────
tamano_mb = os.path.getsize(SALIDA) / 1024 / 1024
print(f'\nArchivo generado: datos.js')
print(f'Total municipios: {len(features_combinados)}')
print(f'Sin datos de población: {total_sin_datos}')
print(f'Tamaño del archivo: {tamano_mb:.1f} MB')
print('\nListo. Ahora abre index.html en el navegador.')
