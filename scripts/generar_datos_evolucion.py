"""
generar_datos_evolucion.py
══════════════════════════
Procesa los JSON del INE (Padrón Municipal 1996-2025) y genera:

  1. datos_evolucion.js         — archivo único para el dashboard web con
                                  la evolución de población de todos los
                                  municipios de CyL (Total, Hombres, Mujeres).

  2. Evolucion por municipios/  — carpeta con un JSON por provincia,
                                  con el mismo contenido estructurado por provincia.

Fuente: INE > Padrón Municipal > Cifras de población > Municipios
        Carpeta local: "Pobacion varios años/"

Cómo ejecutar:
    python generar_datos_evolucion.py

Resultado:
    - datos_evolucion.js (en la raíz del proyecto)
    - Evolucion por municipios/Avila.json ... Zamora.json
"""

import json
import os

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.abspath(__file__))
DIR_ENTRADA = os.path.join(BASE, 'Pobacion varios años')
DIR_SALIDA  = os.path.join(BASE, 'Evolucion por municipios')
SALIDA_JS   = os.path.join(BASE, 'datos_evolucion.js')

os.makedirs(DIR_SALIDA, exist_ok=True)

# ── Provincias: (archivo JSON entrada, nombre visible, clave, código INE) ─────
PROVINCIAS = [
    ('Avila.json',      'Ávila',      'avila',      '05'),
    ('Burgos.json',     'Burgos',     'burgos',     '09'),
    ('Leon.json',       'León',       'leon',       '24'),
    ('Palencia.json',   'Palencia',   'palencia',   '34'),
    ('Salamanca.json',  'Salamanca',  'salamanca',  '37'),
    ('Segovia.json',    'Segovia',    'segovia',    '40'),
    ('Soria.json',      'Soria',      'soria',      '42'),
    ('Valladolid.json', 'Valladolid', 'valladolid', '47'),
    ('Zamora.json',     'Zamora',     'zamora',     '49'),
]

# ── Procesar ──────────────────────────────────────────────────────────────────
resultado_global = {}   # {codigo: {años:[...], total:[...], hombres:[...], mujeres:[...]}}
total_procesados = 0

print('Procesando provincias...')

for archivo, nombre_prov, clave_prov, cod_prov in PROVINCIAS:
    ruta = os.path.join(DIR_ENTRADA, archivo)
    with open(ruta, encoding='utf-8') as f:
        items = json.load(f)

    municipios_prov = {}   # {codigo: {...}} para el JSON de provincia

    for item in items:
        # Extraer código de municipio y sexo desde MetaData
        codigo = None
        sexo   = None
        nombre = None
        for m in item['MetaData']:
            if m['T3_Variable'] == 'Municipios':
                codigo = m['Codigo']
                nombre = m['Nombre']
            elif m['T3_Variable'] == 'Sexo':
                sexo = m['Nombre'].lower()   # 'total', 'hombres', 'mujeres'

        if not codigo or not sexo:
            continue
        if codigo[:2] != cod_prov:
            continue

        # Ordenar datos por año ascendente
        data_sorted = sorted(item['Data'], key=lambda x: x['Anyo'])
        años   = [d['Anyo'] for d in data_sorted]
        valores = [int(d['Valor']) if d['Valor'] is not None else 0 for d in data_sorted]

        # Añadir al resultado global
        if codigo not in resultado_global:
            resultado_global[codigo] = {
                'nombre':   nombre,
                'provincia': nombre_prov,
                'prov_key':  clave_prov,
                'años':      años,
            }
        resultado_global[codigo][sexo] = valores

        # Añadir al resultado de provincia
        if codigo not in municipios_prov:
            municipios_prov[codigo] = {
                'codigo':   codigo,
                'nombre':   nombre,
                'provincia': nombre_prov,
                'prov_key':  clave_prov,
                'años':      años,
            }
        municipios_prov[codigo][sexo] = valores

    # Guardar JSON de provincia
    salida_prov = os.path.join(DIR_SALIDA, archivo)
    with open(salida_prov, 'w', encoding='utf-8') as f:
        json.dump(list(municipios_prov.values()), f, ensure_ascii=False, separators=(',', ':'))

    print(f'  {nombre_prov}: {len(municipios_prov)} municipios')
    total_procesados += len(municipios_prov)

# ── Escribir datos_evolucion.js ───────────────────────────────────────────────
contenido = (
    '// datos_evolucion.js — Generado automáticamente por generar_datos_evolucion.py\n'
    '// Contiene la evolución de población 1996-2025 por municipio de CyL (INE).\n'
    '// NO editar manualmente.\n\n'
    'const DATOS_EVOLUCION = '
    + json.dumps(resultado_global, ensure_ascii=False, separators=(',', ':'))
    + ';'
)

with open(SALIDA_JS, 'w', encoding='utf-8') as f:
    f.write(contenido)

tamano_kb = os.path.getsize(SALIDA_JS) / 1024
print(f'\nArchivo generado: datos_evolucion.js ({tamano_kb:.0f} KB)')
print(f'Total municipios: {total_procesados}')

# ── Mostrar ejemplos ──────────────────────────────────────────────────────────
print('\nEjemplos:')
for cod in ['47186', '09059', '05001']:
    if cod in resultado_global:
        d = resultado_global[cod]
        print(f"  {cod} {d['nombre']}: {d['años'][0]}={d['total'][0]} → {d['años'][-1]}={d['total'][-1]}")
