"""
generar_datos_establecimientos.py
══════════════════════════════════
Procesa el Registro de Turismo de Castilla y León (bares, restaurantes,
cafeterías, hoteles, turismo rural...) y genera datos_establecimientos.js
con el número de establecimientos por municipio, normalizado por población.

Fuente:
  - Registro de Turismo de CyL (datosabiertos.jcyl.es)
    → Hoteles,bares,cafeterias/registro-de-turismo-de-castilla-y-leon.xls

Cómo ejecutar:
    python generar_datos_establecimientos.py
"""

import xml.etree.ElementTree as ET
import json
import os
import unicodedata
import re

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
XLS     = os.path.join(BASE, 'Hoteles,bares,cafeterias', 'registro-de-turismo-de-castilla-y-leon.xls')
EDADES  = os.path.join(BASE, 'datos_edades.js')
SALIDA  = os.path.join(BASE, 'datos_establecimientos.js')

CYL_PROV = {'05', '09', '24', '34', '37', '40', '42', '47', '49'}

# ── Agrupación de tipos de establecimientos ───────────────────────────────────
# Mapeamos el campo 'establecimiento' a una de las 4 categorías del dashboard
TIPO_MAP = {
    'Bares':                      'bares',
    'Cafeterías':                 'cafeterias',
    'Restaurantes':               'restaurantes',
    'Alojamientos Hoteleros':     'alojamiento',
    'Alojam. Turismo Rural':      'alojamiento',
    'Apartamentos Turísticos':    'alojamiento',
    'Vivienda turística':         'alojamiento',
    'Albergues':                  'alojamiento',
    'Campings':                   'alojamiento',
}


# ── Utilidades ────────────────────────────────────────────────────────────────
def normalizar(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^A-Z0-9 ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def variantes(nombre_norm):
    v = [nombre_norm]
    for art in ['LA ', 'EL ', 'LOS ', 'LAS ', 'LO ']:
        if nombre_norm.startswith(art):
            sin_art = nombre_norm[len(art):]
            v.append(f'{sin_art}, {art.strip()}')
            v.append(sin_art)
        elif f', {art.strip()}' in nombre_norm:
            base = nombre_norm.replace(f', {art.strip()}', '').strip()
            v.append(f'{art}{base}')
            v.append(base)
    return v


# ── 1. Cargar referencia INE (código → nombre, población) ─────────────────────
print('Cargando referencia de municipios...')
with open(EDADES, encoding='utf-8') as f:
    contenido = f.read()
json_str = contenido.split('const DATOS_EDADES = ')[1].rstrip(';')
edades = json.loads(json_str)

# Índice: (prefijo_provincia, nombre_norm) → codigo_ine
idx_ine = {}
for codigo, datos in edades.items():
    pref = codigo[:2]
    for v in variantes(normalizar(datos['nombre'])):
        idx_ine[(pref, v)] = codigo

# Mapa codigo_ine → población (para calcular por 1000 hab)
pob_muni = {codigo: datos.get('total', datos.get('pob_total', 0))
            for codigo, datos in edades.items()}

PREF_PROV = {
    'Ávila': '05', 'Burgos': '09', 'León': '24', 'Palencia': '34',
    'Salamanca': '37', 'Segovia': '40', 'Soria': '42', 'Valladolid': '47', 'Zamora': '49'
}


# ── 2. Parsear el XML del registro de turismo ─────────────────────────────────
print('Leyendo registro de turismo...')
NS = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
tree = ET.parse(XLS)
root = tree.getroot()
worksheet = root.find('.//ss:Worksheet', NS)
table = worksheet.find('ss:Table', NS)
rows = table.findall('ss:Row', NS)

raw_data = []
headers = []
for i, row in enumerate(rows):
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
registros = []
for row_dict in raw_data[1:]:
    fila = {headers_map.get(k, k): v for k, v in row_dict.items()}
    registros.append(fila)

print(f'  {len(registros)} registros leídos')


# ── 3. Agrupar por municipio ──────────────────────────────────────────────────
print('Agrupando por municipio...')
conteos = {}  # codigo_ine → {bares, cafeterias, restaurantes, alojamiento}

sin_cruce = 0
for reg in registros:
    tipo_raw   = (reg.get('establecimiento') or '').strip()
    muni_raw   = (reg.get('municipio') or '').strip()
    prov_raw   = (reg.get('provincia') or '').strip()

    tipo_cat = TIPO_MAP.get(tipo_raw)
    if not tipo_cat or not muni_raw:
        continue

    pref = PREF_PROV.get(prov_raw)
    if not pref:
        continue

    # Intentar cruzar con INE
    codigo = None
    for v in variantes(normalizar(muni_raw)):
        codigo = idx_ine.get((pref, v))
        if codigo:
            break

    if not codigo:
        sin_cruce += 1
        continue

    if codigo not in conteos:
        conteos[codigo] = {'bares': 0, 'cafeterias': 0, 'restaurantes': 0, 'alojamiento': 0}
    conteos[codigo][tipo_cat] += 1

print(f'  Municipios con datos: {len(conteos)}')
print(f'  Registros sin cruce INE: {sin_cruce}')


# ── 4. Construir el objeto final con totales y ratios por 1000 hab ────────────
resultado = {}
for codigo, cnts in conteos.items():
    datos_edad = edades.get(codigo, {})
    nombre = datos_edad.get('nombre', codigo)
    pob = pob_muni.get(codigo, 0)

    total = sum(cnts.values())

    def ratio(n):
        return round(n / pob * 1000, 1) if pob > 0 else 0

    resultado[codigo] = {
        'nombre':            nombre,
        'total':             total,
        'bares':             cnts['bares'],
        'cafeterias':        cnts['cafeterias'],
        'restaurantes':      cnts['restaurantes'],
        'alojamiento':       cnts['alojamiento'],
        'total_1000':        ratio(total),
        'bares_1000':        ratio(cnts['bares']),
        'cafeterias_1000':   ratio(cnts['cafeterias']),
        'restaurantes_1000': ratio(cnts['restaurantes']),
        'alojamiento_1000':  ratio(cnts['alojamiento']),
    }

# Ordenar por código INE
resultado = dict(sorted(resultado.items()))

# ── 5. Guardar ────────────────────────────────────────────────────────────────
json_str = json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))
with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write('// datos_establecimientos.js — Generado automáticamente por generar_datos_establecimientos.py\n')
    f.write('// Establecimientos turísticos por municipio de Castilla y León (Registro Junta de CyL)\n')
    f.write('// NO editar manualmente.\n\n')
    f.write(f'const DATOS_ESTABLECIMIENTOS = {json_str};\n')

print(f'\nGenerado: {SALIDA}')
print(f'Municipios incluidos: {len(resultado)}')
