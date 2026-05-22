"""
generar_puntos_establecimientos.py
════════════════════════════════════
Genera datos_puntos_establecimientos.js con TODOS los establecimientos
del Registro de Turismo de CyL como puntos sobre el mapa.

Estrategia de coordenadas (por orden de prioridad):
  1. GPS propio del registro (si existe y es válido para CyL)
  2. Centroide del municipio calculado desde el GeoJSON del dashboard
     + pequeño desplazamiento aleatorio para evitar solapamiento

Fuente:
  - Registro de Turismo de CyL (datosabiertos.jcyl.es)
  - GeoJSON de municipios: datos_municipios.js (ya en el proyecto)

Cómo ejecutar:
    python generar_puntos_establecimientos.py
"""

import xml.etree.ElementTree as ET
import json
import os
import re
import unicodedata
import random

random.seed(42)  # reproducible

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
XLS    = os.path.join(BASE, 'Hoteles,bares,cafeterias', 'registro-de-turismo-de-castilla-y-leon.xls')
GEO    = os.path.join(BASE, 'datos_municipios.js')
EDADES = os.path.join(BASE, 'datos_edades.js')
SALIDA = os.path.join(BASE, 'datos_puntos_establecimientos.js')

TIPO_MAP = {
    'Bares':                   'bares',
    'Cafeterías':              'cafeterias',
    'Restaurantes':            'restaurantes',
    'Alojamientos Hoteleros':  'alojamiento',
    'Alojam. Turismo Rural':   'alojamiento',
    'Apartamentos Turísticos': 'alojamiento',
    'Vivienda turística':      'alojamiento',
    'Albergues':               'alojamiento',
    'Campings':                'alojamiento',
}

PREF_PROV = {
    'Ávila': '05', 'Burgos': '09', 'León': '24', 'Palencia': '34',
    'Salamanca': '37', 'Segovia': '40', 'Soria': '42', 'Valladolid': '47', 'Zamora': '49'
}


# ── Utilidades de normalización (igual que en otros scripts) ──────────────────
def normalizar(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^A-Z0-9 ]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def variantes(nombre_norm):
    v = [nombre_norm]
    for art in ['LA ', 'EL ', 'LOS ', 'LAS ', 'LO ']:
        if nombre_norm.startswith(art):
            sin_art = nombre_norm[len(art):]
            v += [f'{sin_art}, {art.strip()}', sin_art]
        elif f', {art.strip()}' in nombre_norm:
            base = nombre_norm.replace(f', {art.strip()}', '').strip()
            v += [f'{art}{base}', base]
    return v


# ── 1. Calcular centroides de municipio desde el GeoJSON ──────────────────────
print('Calculando centroides de municipios...')
with open(GEO, encoding='utf-8') as f:
    geo_js = f.read()
json_geo = geo_js.split('const DATOS_GEO = ')[1].rstrip(';\n')
geo_data = json.loads(json_geo)

def centroide_poligono(coords_externas):
    """Media aritmética de los vértices del polígono exterior."""
    lats = [c[1] for c in coords_externas]
    lons = [c[0] for c in coords_externas]
    return sum(lats) / len(lats), sum(lons) / len(lons)

# codigo_ine → (lat_centroide, lon_centroide)  — promedio si hay varios polígonos
centroides_raw = {}
for feat in geo_data['features']:
    codigo = feat['properties']['codigo']
    geom   = feat['geometry']
    if geom['type'] == 'Polygon':
        rings = [geom['coordinates'][0]]
    else:  # MultiPolygon
        rings = [p[0] for p in geom['coordinates']]
    for ring in rings:
        lat, lon = centroide_poligono(ring)
        if codigo not in centroides_raw:
            centroides_raw[codigo] = []
        centroides_raw[codigo].append((lat, lon))

centroides = {
    cod: (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts)
    )
    for cod, pts in centroides_raw.items()
}
print(f'  Centroides calculados: {len(centroides)} municipios')


# ── 2. Construir índice nombre→código INE (igual que otros scripts) ───────────
print('Cargando referencia INE...')
with open(EDADES, encoding='utf-8') as f:
    edades_js = f.read()
edades = json.loads(edades_js.split('const DATOS_EDADES = ')[1].rstrip(';\n'))

idx_ine = {}
for codigo, datos in edades.items():
    pref = codigo[:2]
    for v in variantes(normalizar(datos['nombre'])):
        idx_ine[(pref, v)] = codigo


# ── 3. Parsear el XML del registro de turismo ─────────────────────────────────
print('Leyendo registro de turismo...')
NS = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
tree = ET.parse(XLS)
root = tree.getroot()
worksheet = root.find('.//ss:Worksheet', NS)
table = worksheet.find('ss:Table', NS)
rows = table.findall('ss:Row', NS)

raw_data = []
for row in rows:
    cells = row.findall('ss:Cell', NS)
    row_dict = {}
    col_idx = 0
    for cell in cells:
        idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
        if idx_attr:
            col_idx = int(idx_attr) - 1
        data_el = cell.find('ss:Data', NS)
        row_dict[col_idx] = data_el.text if data_el is not None else ''
        col_idx += 1
    raw_data.append(row_dict)

headers_map = {k: v for k, v in raw_data[0].items()}
registros = [{headers_map.get(k, k): v for k, v in row.items()} for row in raw_data[1:]]
print(f'  {len(registros)} registros leídos')


# ── 4. Construir lista de puntos ──────────────────────────────────────────────
print('Generando puntos...')
puntos       = []
con_gps      = 0
con_centroide = 0
sin_ubicacion = 0

# Radio del desplazamiento aleatorio en grados (~0.008° ≈ 800m)
OFFSET = 0.008

for r in registros:
    tipo_raw = (r.get('establecimiento') or '').strip()
    tipo_cat = TIPO_MAP.get(tipo_raw)
    if not tipo_cat:
        continue

    nombre    = (r.get('nombre')    or '').strip()
    muni_raw  = (r.get('municipio') or '').strip()
    prov_raw  = (r.get('provincia') or '').strip()
    categoria = (r.get('categoria') or '').strip()

    # — Intentar usar GPS propio —
    lat_str = (r.get('gps_latitud')  or '').strip().replace(',', '.')
    lon_str = (r.get('gps_longitud') or '').strip().replace(',', '.')
    lat = lon = None
    try:
        lat_f = float(lat_str)
        lon_f = float(lon_str)
        if 39.5 <= lat_f <= 44.5 and -8.0 <= lon_f <= -1.5:
            lat, lon = lat_f, lon_f
            con_gps += 1
    except (ValueError, TypeError):
        pass

    # — Si no hay GPS, usar centroide del municipio —
    if lat is None:
        pref = PREF_PROV.get(prov_raw)
        codigo = None
        if pref and muni_raw:
            for v in variantes(normalizar(muni_raw)):
                codigo = idx_ine.get((pref, v))
                if codigo:
                    break
        if codigo and codigo in centroides:
            c_lat, c_lon = centroides[codigo]
            # Desplazamiento aleatorio pequeño para evitar solapamiento exacto
            lat = round(c_lat + random.uniform(-OFFSET, OFFSET), 6)
            lon = round(c_lon + random.uniform(-OFFSET, OFFSET), 6)
            con_centroide += 1
        else:
            sin_ubicacion += 1
            continue

    puntos.append({
        'lat':       round(lat, 6),
        'lon':       round(lon, 6),
        'tipo':      tipo_cat,
        'nombre':    nombre,
        'municipio': muni_raw,
        'provincia': prov_raw,
        'categoria': categoria if categoria else tipo_raw,
    })

print(f'\n  Total puntos generados : {len(puntos):,}')
print(f'  Con GPS propio         : {con_gps:,}')
print(f'  Con centroide          : {con_centroide:,}')
print(f'  Sin ubicación posible  : {sin_ubicacion:,}')
print()
for t in ['bares', 'cafeterias', 'restaurantes', 'alojamiento']:
    n = sum(1 for p in puntos if p['tipo'] == t)
    print(f'  {t:15}: {n:,}')


# ── 5. Guardar ────────────────────────────────────────────────────────────────
json_str = json.dumps(puntos, ensure_ascii=False, separators=(',', ':'))
with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write('// datos_puntos_establecimientos.js — Generado por generar_puntos_establecimientos.py\n')
    f.write(f'// {len(puntos):,} establecimientos (GPS propio: {con_gps:,} · centroide: {con_centroide:,})\n')
    f.write('// NO editar manualmente.\n\n')
    f.write(f'const datosPuntosEstab = {json_str};\n')

print(f'\nGenerado: {SALIDA}')
