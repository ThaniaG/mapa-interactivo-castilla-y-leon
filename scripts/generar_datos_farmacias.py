"""
generar_datos_farmacias.py
══════════════════════════════════════════════════════════════════
Genera datos_farmacias.js y datos_puntos_farmacias.js con las
farmacias de Castilla y León por municipio.

Fuente: registro-de-establecimientos-farmaceuticos-de-castilla-y-leon.csv
        (datosabiertos.jcyl.es — descarga directa, actualización diaria)

Salidas:
  - datos_farmacias.js      → número de farmacias por municipio INE
  - datos_puntos_farmacias.js → punto por farmacia (geocodificado o centroide)

Cómo ejecutar:
    python generar_datos_farmacias.py
"""

import csv
import json
import os
import re
import time
import unicodedata
import urllib.request
import urllib.parse

BASE      = os.path.dirname(os.path.abspath(__file__))
F_CSV     = os.path.join(BASE, 'farmacias', 'registro-de-establecimientos-farmaceuticos-de-castilla-y-leon.csv')
F_EDADES  = os.path.join(BASE, 'datos_edades.js')
F_GEO     = os.path.join(BASE, 'datos_municipios.js')
F_GEOCACHE = os.path.join(BASE, 'farmacias', 'geocode_cache_farmacias.json')

SALIDA_VAR    = os.path.join(BASE, 'datos_farmacias.js')
SALIDA_PUNTOS = os.path.join(BASE, 'datos_puntos_farmacias.js')

PROV_PREF = {
    'AVILA': '05', 'ÁVILA': '05',
    'BURGOS': '09',
    'LEON': '24', 'LEÓN': '24',
    'PALENCIA': '34',
    'SALAMANCA': '37',
    'SEGOVIA': '40',
    'SORIA': '42',
    'VALLADOLID': '47',
    'ZAMORA': '49',
}


# ── Utilidades ────────────────────────────────────────────────────────────────

def norm(texto):
    t = str(texto).upper().strip()
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'[^A-Z0-9 ]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def variantes(n):
    v = [n]
    for art in ['LA', 'EL', 'LOS', 'LAS', 'LO']:
        art_sp = art + ' '
        if n.startswith(art_sp):
            sin = n[len(art_sp):]
            v += [f'{sin}, {art}', sin, f'{sin} {art}']
        elif f', {art}' in n:
            base = n.replace(f', {art}', '').strip()
            v += [f'{art_sp}{base}', base, f'{base} {art}']
        elif n.endswith(f' {art}'):
            base = n[:-len(art)-1].strip()
            v += [f'{art_sp}{base}', f'{base}, {art}', base]
    return list(dict.fromkeys(v))


# ── Geocodificación ───────────────────────────────────────────────────────────

print('Cargando caché de geocodificación...')
if os.path.exists(F_GEOCACHE):
    with open(F_GEOCACHE, encoding='utf-8') as f:
        geocache = json.load(f)
else:
    geocache = {}
print(f'  {len(geocache)} entradas en caché')

def geocodificar(query):
    if query in geocache:
        return geocache[query]
    params = urllib.parse.urlencode({
        'q': query, 'format': 'json', 'limit': '1', 'countrycodes': 'es'
    })
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': 'CyLDashboard/1.0 academic'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = (round(float(data[0]['lat']), 6), round(float(data[0]['lon']), 6)) if data else None
    except Exception:
        result = None
    geocache[query] = result
    time.sleep(1.1)
    return result

def guardar_cache():
    with open(F_GEOCACHE, 'w', encoding='utf-8') as f:
        json.dump(geocache, f, ensure_ascii=False)


# ── 1. Referencia INE ─────────────────────────────────────────────────────────

print('Cargando referencia INE...')
with open(F_EDADES, encoding='utf-8') as f:
    edades_js = f.read()
edades = json.loads(edades_js.split('const DATOS_EDADES = ')[1].rstrip(';\n'))

idx_ine = {}
for cod, d in edades.items():
    pref = cod[:2]
    for v in variantes(norm(d['nombre'])):
        idx_ine[(pref, v)] = cod
print(f'  {len(edades)} municipios en referencia INE')

def buscar_ine(nombre_muni, pref):
    if not pref:
        return None
    for v in variantes(norm(nombre_muni)):
        cod = idx_ine.get((pref, v))
        if cod:
            return cod
    return None


# ── 2. Centroides ─────────────────────────────────────────────────────────────

print('Calculando centroides...')
with open(F_GEO, encoding='utf-8') as f:
    geo_js = f.read()
geo = json.loads(geo_js.split('const DATOS_GEO = ')[1].rstrip(';\n'))

def centroide(ring):
    lats = [c[1] for c in ring]
    lons = [c[0] for c in ring]
    return sum(lats)/len(lats), sum(lons)/len(lons)

centroides = {}
for feat in geo['features']:
    cod = feat['properties']['codigo']
    geom = feat['geometry']
    rings = [geom['coordinates'][0]] if geom['type'] == 'Polygon' \
            else [p[0] for p in geom['coordinates']]
    pts = [centroide(r) for r in rings]
    centroides[cod] = (
        sum(p[0] for p in pts)/len(pts),
        sum(p[1] for p in pts)/len(pts)
    )
print(f'  {len(centroides)} centroides calculados')


# ── 3. Leer farmacias ─────────────────────────────────────────────────────────

print('Cargando farmacias...')
farmacias_raw = []
sin_match = 0

with open(F_CSV, encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f, delimiter=';')
    for r in reader:
        provincia = r.get('PROVINCIA', '').strip().upper()
        municipio = r.get('MUNICIPIO', '').strip()
        localidad = r.get('LOCALIDAD', '').strip()
        calle     = r.get('CALLE', '').strip()
        numero    = r.get('NUMERO', '').strip()
        cp        = str(r.get('CODIGO_POSTAL', '') or '').strip().zfill(5)
        nombre    = r.get('NOMBRE_COMERCIAL', '').strip()
        telefono  = r.get('TELEFONO', '').strip()
        num_reg   = r.get('NUM_REG', '').strip()

        pref = PROV_PREF.get(norm(provincia))
        cod_ine = buscar_ine(municipio, pref) if pref else None
        if not cod_ine:
            sin_match += 1
            continue

        dir_completa = f'{calle} {numero}'.strip() if numero and numero != 'S/N' else calle
        dir_query = f'{dir_completa}, {cp}, {localidad}, España' if dir_completa and cp != '00000' else None

        farmacias_raw.append({
            'cod_ine':   cod_ine,
            'nombre':    nombre,
            'municipio': municipio,
            'localidad': localidad,
            'telefono':  telefono,
            'num_reg':   num_reg,
            'dir_query': dir_query,
        })

print(f'  {len(farmacias_raw)} farmacias resueltas, {sin_match} sin coincidencia INE')


# ── 4. Geocodificar farmacias ─────────────────────────────────────────────────

nuevas = sum(1 for f in farmacias_raw if f['dir_query'] and f['dir_query'] not in geocache)
print(f'\nGeocod. necesarias: {nuevas} peticiones (~{nuevas} segundos)')

puntos_farmacias = []
geo_ok = 0

for i, farm in enumerate(farmacias_raw):
    lat, lon = None, None

    if farm['dir_query']:
        res = geocodificar(farm['dir_query'])
        if res:
            lat, lon = res
            geo_ok += 1

    if lat is None and farm['cod_ine'] in centroides:
        c_lat, c_lon = centroides[farm['cod_ine']]
        lat, lon = round(c_lat, 6), round(c_lon, 6)

    if lat is None:
        continue

    puntos_farmacias.append({
        'lat':      lat,
        'lon':      lon,
        'nombre':   farm['nombre'],
        'municipio': farm['municipio'],
        'localidad': farm['localidad'],
        'telefono':  farm['telefono'],
        'num_reg':   farm['num_reg'],
    })

    # Guardar caché cada 50 farmacias para no perder progreso
    if (i + 1) % 50 == 0:
        guardar_cache()
        print(f'  [{i+1}/{len(farmacias_raw)}] caché guardada ({geo_ok} geocodificadas)')

guardar_cache()
print(f'  {geo_ok}/{len(puntos_farmacias)} geocodificadas, resto centroide')
print(f'  Caché guardada: {len(geocache)} entradas')


# ── 5. Agrupar por municipio ──────────────────────────────────────────────────

print('\nAgrupando por municipio...')
conteo = {}
for farm in farmacias_raw:
    cod = farm['cod_ine']
    conteo[cod] = conteo.get(cod, 0) + 1

print(f'  {len(conteo)} municipios con al menos 1 farmacia')
print(f'  {len(edades) - len(conteo)} municipios sin farmacia')
print(f'  Total farmacias: {sum(conteo.values())}')


# ── 6. Construir datos_farmacias (por municipio) ──────────────────────────────

resultado = {}
for cod_ine in edades:
    n_farm = conteo.get(cod_ine, 0)
    pob    = edades[cod_ine].get('total', 0) or 0
    ratio  = round(n_farm / pob * 1000, 2) if pob > 0 else 0
    resultado[cod_ine] = {
        'nombre':    edades[cod_ine]['nombre'],
        'farmacias': n_farm,
        'ratio_1000': ratio,
    }

resultado = dict(sorted(resultado.items()))
json_str = json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))
with open(SALIDA_VAR, 'w', encoding='utf-8') as f:
    f.write('// datos_farmacias.js — Generado por generar_datos_farmacias.py\n')
    f.write('// Farmacias por municipio de Castilla y León\n')
    f.write('// Fuente: datosabiertos.jcyl.es — Registro establecimientos farmacéuticos\n')
    f.write('// NO editar manualmente.\n\n')
    f.write(f'const DATOS_FARMACIAS = {json_str};\n')
print(f'Generado: {SALIDA_VAR}')


# ── 7. Guardar datos_puntos_farmacias.js ──────────────────────────────────────

json_pts = json.dumps(puntos_farmacias, ensure_ascii=False, separators=(',', ':'))
with open(SALIDA_PUNTOS, 'w', encoding='utf-8') as f:
    f.write('// datos_puntos_farmacias.js — Generado por generar_datos_farmacias.py\n')
    f.write(f'// {len(puntos_farmacias)} farmacias en Castilla y León\n')
    f.write('// Coordenadas: Nominatim + centroide municipal como respaldo\n')
    f.write('// NO editar manualmente.\n\n')
    f.write(f'const datosPuntosFarmacias = {json_pts};\n')
print(f'Generado: {SALIDA_PUNTOS}')
print(f'\nTotal puntos farmacias: {len(puntos_farmacias):,}')
