"""
generar_residuos.py
Lee el dataset oficial de la Junta de CyL:
  'Gestores de residuos registrados en Castilla y León: canal doméstico'
Extrae Puntos Limpios y Plantas de Transferencia únicos (por NIMA),
les asigna coordenadas por municipio y genera datos_residuos.js.
"""

import csv, json, re, os, unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Leer GeoJSON para obtener centroides por municipio ─────────────────────

print("Cargando centroides de municipios...")

def leer_js(nombre, var):
    ruta = os.path.join(BASE, nombre)
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(ruta, encoding=enc) as f:
                texto = f.read()
            break
        except Exception:
            continue
    lineas = [l for l in texto.splitlines() if not l.strip().startswith('//')]
    texto  = '\n'.join(lineas)
    texto  = re.sub(rf'const\s+{var}\s*=\s*', '', texto).strip().rstrip(';')
    return json.loads(texto)

geo = leer_js('datos_municipios.js', 'DATOS_GEO')

# Construir lookup: nombre_normalizado → {lat, lon, cod}
def normalizar(nombre):
    s = unicodedata.normalize('NFD', nombre.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]', '', s).strip()

centroide_muni = {}
for feat in geo['features']:
    p    = feat['properties']
    geom = feat['geometry']
    polys = []
    if geom['type'] == 'Polygon':
        polys = [geom['coordinates'][0]]
    elif geom['type'] == 'MultiPolygon':
        polys = [poly[0] for poly in geom['coordinates']]
    n_pts = sum(len(poly) for poly in polys)
    if not n_pts:
        continue
    cx = sum(c[0] for poly in polys for c in poly) / n_pts
    cy = sum(c[1] for poly in polys for c in poly) / n_pts
    clave = normalizar(p['nombre'])
    centroide_muni[clave] = {'lat': round(cy, 5), 'lon': round(cx, 5), 'cod': p['codigo']}

print(f"  {len(centroide_muni)} municipios con centroide")

# ── 2. Leer CSV oficial de residuos ───────────────────────────────────────────

print("\nLeyendo dataset oficial Junta CyL...")

RUTA_CSV = os.path.join(BASE,
    'Gestores de residuos registrados en Castilla y León-canal doméstico',
    'gestores-de-residuos-registrados-en-castilla-y-leon-canal-domestico.csv')

with open(RUTA_CSV, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    rows = list(reader)

cols = list(rows[0].keys())
col_tipo = next(c for c in cols if 'tipo' in c.lower() or 'instalaci' in c.lower())
col_muni = next(c for c in cols if c.lower() == 'municipio')
col_prov = next(c for c in cols if c.lower() == 'provincia')
col_nima = next(c for c in cols if 'nima' in c.lower())
col_nomb = next(c for c in cols if 'nombre' in c.lower() or 'raz' in c.lower())
col_dir  = next(c for c in cols if 'direcci' in c.lower())

print(f"  {len(rows)} registros leídos")

# ── 3. Deduplicar por NIMA y clasificar ──────────────────────────────────────

TIPOS_INTERES = {
    'Punto Limpio':        {'label': 'Punto Limpio',           'color': '#1b5e20', 'radius': 8},
    'Planta de Transferencia': {'label': 'Planta de Transferencia', 'color': '#e65100', 'radius': 6},
}

instalaciones = {}

for r in rows:
    tipo_raw = r.get(col_tipo, '')
    tipo_key = None
    for k in TIPOS_INTERES:
        if k in tipo_raw:
            tipo_key = k
            break
    if not tipo_key:
        continue

    nima = r[col_nima].strip()
    if not nima or nima in instalaciones:
        continue

    municipio = r[col_muni].strip()
    provincia = r[col_prov].strip()
    nombre    = r[col_nomb].strip()
    direccion = r[col_dir].strip()

    # Buscar coordenadas
    clave = normalizar(municipio)
    coords = centroide_muni.get(clave)

    # Si no coincide exacto, buscar por primera palabra
    if not coords:
        primera = clave.split()[0] if clave else ''
        for k, v in centroide_muni.items():
            if k.startswith(primera) and len(primera) > 4:
                coords = v
                break

    instalaciones[nima] = {
        'nima':      nima,
        'nombre':    nombre,
        'municipio': municipio,
        'provincia': provincia,
        'direccion': direccion,
        'tipo':      tipo_key,
        'lat':       coords['lat'] if coords else None,
        'lon':       coords['lon'] if coords else None,
        'cod':       coords['cod'] if coords else None,
    }

# Separar con/sin coordenadas
con_coords = [v for v in instalaciones.values() if v['lat']]
sin_coords  = [v for v in instalaciones.values() if not v['lat']]

print(f"\n  Instalaciones únicas:")
for tipo_key, info in TIPOS_INTERES.items():
    n = sum(1 for v in instalaciones.values() if v['tipo'] == tipo_key)
    print(f"    {info['label']:25s}: {n}")
print(f"  Con coordenadas : {len(con_coords)}")
print(f"  Sin coordenadas : {len(sin_coords)} (se excluyen del mapa)")

if sin_coords:
    print("  Sin coordenadas:")
    for v in sin_coords[:5]:
        print(f"    {v['municipio']} ({v['provincia']})")

# ── 4. Estadísticas por provincia ─────────────────────────────────────────────

from collections import Counter
stats_prov = Counter(v['provincia'] for v in con_coords if v['tipo'] == 'Punto Limpio')
print("\n  Puntos Limpios por provincia:")
for prov, n in sorted(stats_prov.items(), key=lambda x: -x[1]):
    print(f"    {prov:15s}: {n}")

# ── 5. Guardar datos_residuos.js ──────────────────────────────────────────────

puntos_limpios  = [v for v in con_coords if v['tipo'] == 'Punto Limpio']
plantas_transf  = [v for v in con_coords if v['tipo'] == 'Planta de Transferencia']

meta = {
    'n_puntos_limpios':  len(puntos_limpios),
    'n_plantas_transf':  len(plantas_transf),
    'fuente':            'Junta de Castilla y León — Gestores de residuos canal doméstico',
    'tipos_info':        TIPOS_INTERES,
}

salida = os.path.join(BASE, 'datos_residuos.js')
with open(salida, 'w', encoding='utf-8') as f:
    f.write('// Puntos Limpios y Plantas de Transferencia de Castilla y León\n')
    f.write('// Fuente: Junta de CyL — datosabiertos.jcyl.es (Gestores de residuos: canal doméstico)\n')
    f.write('const RESIDUOS_META = ')
    json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const PUNTOS_LIMPIOS = ')
    json.dump(puntos_limpios, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    f.write('const PLANTAS_TRANSFERENCIA = ')
    json.dump(plantas_transf, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
    # Mantener compatibilidad con funciones.js (ya usa CONTENEDORES_RECICLAJE)
    f.write('const CONTENEDORES_RECICLAJE = [];\n')

size_kb = os.path.getsize(salida) / 1024
print(f"\n  Guardado: datos_residuos.js ({size_kb:.0f} KB)")
print(f"\n{'='*50}")
print(f"  Puntos Limpios (mapa)  : {len(puntos_limpios)}")
print(f"  Plantas Transferencia  : {len(plantas_transf)}")
print(f"  Fuente                 : Junta de CyL (oficial)")
print(f"{'='*50}")
