import geopandas as gpd
import json
import os

provincias = {
    'avila':      'AVILA',
    'burgos':     'BURGOS',
    'leon':       'LEON',
    'palencia':   'PALENCIA',
    'salamanca':  'SALAMANCA',
    'segovia':    'SEGOVIA',
    'soria':      'SORIA',
    'valladolid': 'VALLADOLID',
    'zamora':     'ZAMORA',
}

features = []

for clave, nombre_archivo in provincias.items():
    ruta = f'limites/datos/{nombre_archivo}.geojson'
    if not os.path.exists(ruta):
        print(f'No encontrado: {ruta}')
        continue

    gdf = gpd.read_file(ruta)
    # Disolver todos los municipios en un solo polígono de provincia
    disuelto = gdf.dissolve()
    # Simplificar geometría para reducir tamaño del archivo
    disuelto['geometry'] = disuelto['geometry'].simplify(0.002, preserve_topology=True)

    geom = json.loads(disuelto[['geometry']].to_json())['features'][0]['geometry']

    features.append({
        'type': 'Feature',
        'properties': {'prov_key': clave},
        'geometry': geom
    })
    print(f'OK: {nombre_archivo}')

datos = {
    'type': 'FeatureCollection',
    'features': features
}

contenido = 'const DATOS_PROVINCIAS = ' + json.dumps(datos, ensure_ascii=False) + ';'

with open('provincias.js', 'w', encoding='utf-8') as f:
    f.write(contenido)

print(f'\nArchivo provincias.js generado con {len(features)} provincias.')
