"""
generar_naturaleza.py
Descarga desde OpenStreetMap (Overpass API):
  1. Rutas de senderismo y cicloturismo en Castilla y León
     (GR, PR, SL, Camino de Santiago + vías verdes/cicloturismo)
  2. Espacios Naturales Protegidos (parques, reservas, ZEPA, ZEC…)

Salida: datos_naturaleza.js
"""

import json, math, re, urllib.request, urllib.parse, os, time
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))


def haversine(a, b):
    R = 6371
    dlat = math.radians(b[1] - a[1])
    dlon = math.radians(b[0] - a[0])
    s = math.sin(dlat/2)**2 + math.cos(math.radians(a[1])) * math.cos(math.radians(b[1])) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(s))


def simplificar(coords, min_km=0.20):
    if len(coords) <= 2:
        return coords
    res = [coords[0]]
    for c in coords[1:-1]:
        if haversine(res[-1], c) >= min_km:
            res.append(c)
    res.append(coords[-1])
    return res


def overpass(query, desc):
    print(f"  Consultando: {desc}...")
    url  = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({'data': query}).encode()
    req  = urllib.request.Request(url, data=data, headers={'User-Agent': 'TFM-CyL-naturaleza/1.0'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read())
    elems = result.get('elements', [])
    print(f"    -> {len(elems)} elementos")
    return elems


# ── 1. RUTAS DE SENDERISMO (ways con ref GR/PR/SL) ───────────────────────────

print("\n[1/3] Rutas de senderismo (GR / PR / SL)...")
time.sleep(2)

q_rutas = """
[out:json][timeout:120];
area["ISO3166-2"="ES-CL"]->.cyl;
(
  way["ref"~"^(GR|PR|SL)"][highway](area.cyl);
  way["ref"~"^(GR|PR|SL)"][foot](area.cyl);
);
out geom;
"""
elems_rutas = overpass(q_rutas, "GR/PR/SL trail ways")

# ── 2. CAMINO DE SANTIAGO Y VÍAS VERDES ──────────────────────────────────────

print("\n[2/3] Camino de Santiago + vías verdes...")
time.sleep(3)

q_camino = """
[out:json][timeout:120];
area["ISO3166-2"="ES-CL"]->.cyl;
(
  way["ref"~"GR 65|Camino"][highway](area.cyl);
  way[highway]["designation"~"camino_de_santiago"](area.cyl);
  way["route"="pilgrimage"][highway](area.cyl);
  way["railway"="abandoned"]["tourism"](area.cyl);
  way["highway"~"^(cycleway|path)$"]["surface"]["lit"!="yes"]["name"~"[Vv]ía [Vv]erde"](area.cyl);
);
out geom;
"""
# Alternativa más amplia para Camino de Santiago
q_camino2 = """
[out:json][timeout:120];
area["ISO3166-2"="ES-CL"]->.cyl;
relation["route"~"^(hiking|foot|pilgrimage)$"]["name"~"[Cc]amino"](area.cyl);
out center tags;
"""
elems_camino = overpass(q_camino2, "Camino de Santiago (relations)")

# ── 3. ESPACIOS NATURALES PROTEGIDOS ──────────────────────────────────────────

print("\n[3/3] Espacios Naturales Protegidos...")
time.sleep(3)

q_espacios = """
[out:json][timeout:120];
area["ISO3166-2"="ES-CL"]->.cyl;
(
  node[boundary=protected_area](area.cyl);
  way[boundary=protected_area](area.cyl);
  relation[boundary=protected_area](area.cyl);
  way[leisure=nature_reserve](area.cyl);
  relation[leisure=nature_reserve](area.cyl);
  relation[boundary=national_park](area.cyl);
);
out center tags;
"""
elems_espacios = overpass(q_espacios, "protected areas")


# ── Procesar rutas de senderismo ──────────────────────────────────────────────

TIPO_RUTA = {
    'GR':  {'label': 'Gran Recorrido (GR)',      'color': '#c0392b', 'weight': 2.5},
    'PR':  {'label': 'Pequeño Recorrido (PR)',   'color': '#e67e22', 'weight': 2},
    'SL':  {'label': 'Sendero Local (SL)',        'color': '#f39c12', 'weight': 1.5},
}

rutas = []
km_rutas = defaultdict(float)

for elem in elems_rutas:
    if elem.get('type') != 'way':
        continue
    geom = elem.get('geometry', [])
    if len(geom) < 2:
        continue
    tags = elem.get('tags', {})
    ref  = tags.get('ref', '')
    m = re.match(r'^(GR|PR|SL)', ref.upper().replace('-', '').replace(' ', ''))
    tipo = m.group(1) if m else 'GR'
    info = TIPO_RUTA.get(tipo, TIPO_RUTA['GR'])

    coords_orig = [[p['lon'], p['lat']] for p in geom]
    coords_s    = simplificar(coords_orig, min_km=0.15)
    coords_r    = [[round(c[0], 4), round(c[1], 4)] for c in coords_s]

    km = sum(haversine(coords_orig[i], coords_orig[i+1]) for i in range(len(coords_orig)-1))
    km_rutas[tipo] += km

    rutas.append({
        'tipo':  tipo,
        'ref':   ref,
        'nombre': tags.get('name', ref),
        'color':  info['color'],
        'weight': info['weight'],
        'coords': coords_r,
        'km':     round(km, 2),
    })

print(f"\n  Rutas procesadas: {len(rutas)}")
for t, km in sorted(km_rutas.items()):
    print(f"    {t}: {km:.0f} km")

# ── Procesar Camino de Santiago (relations → center points) ───────────────────

caminos = []
for elem in elems_camino:
    tags = elem.get('tags', {})
    nombre = tags.get('name', tags.get('ref', 'Camino'))
    lat = elem.get('center', {}).get('lat') or elem.get('lat')
    lon = elem.get('center', {}).get('lon') or elem.get('lon')
    if not lat or not lon:
        continue
    caminos.append({
        'nombre': nombre,
        'red':    tags.get('network', tags.get('route', '')),
        'lat': round(lat, 4),
        'lon': round(lon, 4),
    })

print(f"  Caminos: {len(caminos)}")

# ── Procesar Espacios Naturales ───────────────────────────────────────────────

PROT_CLASS = {
    '1': 'Parque Nacional',
    '2': 'Parque Nacional',
    '3': 'Parque Natural',
    '4': 'Parque Natural',
    '5': 'Reserva Natural',
    '6': 'Paisaje Protegido',
    '7': 'Zona de Especial Protección (ZEPA)',
    '8': 'Zona de Especial Conservación (ZEC)',
}

espacios = []
nombres_vistos = set()

for elem in elems_espacios:
    tags = elem.get('tags', {})
    nombre = tags.get('name', tags.get('name:es', '')).strip()
    if not nombre or nombre in nombres_vistos:
        continue
    nombres_vistos.add(nombre)

    lat = elem.get('center', {}).get('lat') or elem.get('lat')
    lon = elem.get('center', {}).get('lon') or elem.get('lon')
    if not lat or not lon:
        continue

    pc    = str(tags.get('protect_class', ''))
    tipo  = PROT_CLASS.get(pc, tags.get('boundary', 'Espacio Natural'))
    area_ha = tags.get('area', '')

    espacios.append({
        'nombre':  nombre,
        'tipo':    tipo,
        'pc':      pc,
        'lat': round(lat, 4),
        'lon': round(lon, 4),
    })

# Ordenar: parques nacionales primero
espacios.sort(key=lambda x: int(x['pc']) if x['pc'].isdigit() else 99)
print(f"  Espacios naturales: {len(espacios)}")

# Tipos de espacios
tipos_esp = defaultdict(int)
for e in espacios:
    tipos_esp[e['tipo']] += 1
for t, n in sorted(tipos_esp.items(), key=lambda x: -x[1]):
    print(f"    {t}: {n}")

# ── Guardar datos_naturaleza.js ───────────────────────────────────────────────

# Agrupar rutas por tipo para carga eficiente
rutas_por_tipo = {'GR': [], 'PR': [], 'SL': []}
for r in rutas:
    rutas_por_tipo[r['tipo']].append({'ref': r['ref'], 'nombre': r['nombre'], 'coords': r['coords'], 'km': r['km']})

meta = {
    'n_rutas':    len(rutas),
    'km_rutas':   {t: round(v) for t, v in km_rutas.items()},
    'n_espacios': len(espacios),
    'tipos_GR':   TIPO_RUTA,
}

salida = os.path.join(BASE, 'datos_naturaleza.js')
with open(salida, 'w', encoding='utf-8') as f:
    f.write('// Rutas naturales y espacios protegidos de Castilla y León — fuente: OpenStreetMap\n')
    f.write('// Generado por generar_naturaleza.py\n')
    f.write('const NATURALEZA_META = ')
    json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const RUTAS_NATURALEZA = ')
    json.dump(rutas_por_tipo, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const ESPACIOS_NATURALES = ')
    json.dump(espacios, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const CAMINOS_SANTIAGO = ')
    json.dump(caminos, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')

size_mb = os.path.getsize(salida) / 1024 / 1024
print(f"\n  Guardado: datos_naturaleza.js ({size_mb:.1f} MB)")

print(f"""
{'='*50}
  RESUMEN
{'='*50}
  Rutas GR/PR/SL : {len(rutas)} segmentos
  Caminos        : {len(caminos)} rutas
  Espacios Nat.  : {len(espacios)} áreas protegidas
  Archivo        : {size_mb:.1f} MB
""")
