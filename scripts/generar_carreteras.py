"""
generar_carreteras.py
Descarga la red viaria principal de Castilla y León desde OpenStreetMap (Overpass API)
y genera datos_carreteras.js para visualizarla en el dashboard Leaflet.

Tipos incluidos:
  motorway / motorway_link  → Autopistas y autovías (A-1, AP-51…)
  trunk    / trunk_link     → Carreteras nacionales (N-620, N-122…)
  primary  / primary_link   → Carreteras autonómicas (CL-610…)
  secondary / secondary_link → Carreteras provinciales (BU-V-1001…)
"""

import json, math, time, urllib.request, urllib.parse, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

TIPOS = {
    'motorway':        {'label': 'Autopista / Autovía',    'color': '#c0392b', 'weight': 4},
    'motorway_link':   {'label': 'Autopista / Autovía',    'color': '#c0392b', 'weight': 3},
    'trunk':           {'label': 'Carretera Nacional',      'color': '#e67e22', 'weight': 3},
    'trunk_link':      {'label': 'Carretera Nacional',      'color': '#e67e22', 'weight': 2},
    'primary':         {'label': 'Carretera Autonómica',   'color': '#f39c12', 'weight': 2},
    'primary_link':    {'label': 'Carretera Autonómica',   'color': '#f39c12', 'weight': 1.5},
    'secondary':       {'label': 'Carretera Provincial',   'color': '#27ae60', 'weight': 1.5},
    'secondary_link':  {'label': 'Carretera Provincial',   'color': '#27ae60', 'weight': 1},
}

# ── 1. Consultar Overpass ──────────────────────────────────────────────────────

print("Consultando Overpass API (puede tardar 1-3 minutos)...")

query = """
[out:json][timeout:180];
area["ISO3166-2"="ES-CL"]->.cyl;
(
  way["highway"~"^(motorway|trunk|primary|secondary|motorway_link|trunk_link|primary_link|secondary_link)$"](area.cyl);
);
out geom;
"""

url  = "https://overpass-api.de/api/interpreter"
data = urllib.parse.urlencode({'data': query}).encode()
req  = urllib.request.Request(url, data=data, headers={'User-Agent': 'TFM-CyL-dashboard/1.0'})

try:
    with urllib.request.urlopen(req, timeout=200) as resp:
        osm = json.loads(resp.read())
except Exception as e:
    print(f"  ERROR al consultar Overpass: {e}")
    raise

elementos = osm.get('elements', [])
print(f"  {len(elementos)} segmentos descargados")

# ── 2. Simplificación de coordenadas ──────────────────────────────────────────

def haversine(a, b):
    R = 6371
    dlat = math.radians(b['lat'] - a['lat'])
    dlon = math.radians(b['lon'] - a['lon'])
    s = math.sin(dlat/2)**2 + math.cos(math.radians(a['lat'])) * math.cos(math.radians(b['lat'])) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(s))

def simplificar(puntos, min_dist_km=0.05):
    """Elimina puntos intermedios más cercanos que min_dist_km al anterior retenido."""
    if len(puntos) <= 2:
        return puntos
    result = [puntos[0]]
    for p in puntos[1:-1]:
        if haversine(result[-1], p) >= min_dist_km:
            result.append(p)
    result.append(puntos[-1])
    return result

# ── 3. Construir GeoJSON ───────────────────────────────────────────────────────

features  = []
km_total  = 0.0
stats_tipo = defaultdict(float)

for elem in elementos:
    if elem.get('type') != 'way':
        continue
    geom = elem.get('geometry', [])
    if len(geom) < 2:
        continue

    tags    = elem.get('tags', {})
    hw_type = tags.get('highway', '')
    info    = TIPOS.get(hw_type, {'label': hw_type, 'color': '#95a5a6', 'weight': 1})

    # Simplificar puntos (mantiene visual correcto a zoom habitual)
    geom_s = simplificar(geom, min_dist_km=0.15)

    # Longitud del segmento original (antes de simplificar, para estadísticas reales)
    km_seg = sum(haversine(geom[i], geom[i+1]) for i in range(len(geom)-1))
    km_total += km_seg
    stats_tipo[info['label']] += km_seg

    coords = [[round(p['lon'], 5), round(p['lat'], 5)] for p in geom_s]

    features.append({
        'type': 'Feature',
        'properties': {
            'tipo':   hw_type,
            'label':  info['label'],
            'color':  info['color'],
            'weight': info['weight'],
            'ref':    tags.get('ref', ''),
            'nombre': tags.get('name', tags.get('ref', '')),
            'km':     round(km_seg, 2),
        },
        'geometry': {
            'type': 'LineString',
            'coordinates': coords,
        }
    })

print(f"  {len(features)} segmentos | {km_total:.0f} km totales estimados")
print("\n  Por tipo de vía:")
for label, km in sorted(stats_tipo.items(), key=lambda x: -x[1]):
    print(f"    {label:30s}: {km:8.0f} km")

# ── 4. Guardar datos_carreteras.js ────────────────────────────────────────────

# Metadatos globales para el panel del dashboard
meta = {
    'total_km':   round(km_total),
    'stats_tipo': {k: round(v) for k, v in sorted(stats_tipo.items(), key=lambda x: -x[1])},
    'n_segmentos': len(features),
}

salida = os.path.join(BASE, 'datos_carreteras.js')
with open(salida, 'w', encoding='utf-8') as f:
    f.write('// Red viaria de Castilla y León — fuente: OpenStreetMap\n')
    f.write('// Generado por generar_carreteras.py\n')
    f.write('const CARRETERAS_META = ')
    json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const DATOS_CARRETERAS = ')
    json.dump({'type': 'FeatureCollection', 'features': features},
              f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')

size_mb = os.path.getsize(salida) / 1024 / 1024
print(f"\n  Guardado: datos_carreteras.js ({size_mb:.1f} MB)")
if size_mb > 20:
    print("  AVISO: archivo grande — considera reducir min_dist_km o excluir secondary_link")
