"""
generar_datos_vital.py
══════════════════════════════════════════════════════════════════
Descarga y genera datos_vital.js con nacimientos y defunciones
por municipio de Castilla y León, años 2016-2024.

Fuente: INE — Resumen municipal de fenómenos demográficos (Definitivos)
  https://www.ine.es/dynt3/inebase/es/index.htm?padre=3413

Salida:
  - datos_vital.js  → series anuales de nacimientos y defunciones
                      por municipio INE (2016-2024)
"""

import csv
import io
import json
import os
import re
import time
import urllib.request

BASE   = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, 'datos_vital.js')

AÑOS = list(range(2016, 2025))

# tpx IDs por provincia de CyL y año
# Fuente: INE > MNP > Definitivos > Resumen municipal de fenómenos demográficos
TPX = {
    '05': {2016:26556,2017:29489,2018:33142,2019:46093,2020:50374,2021:54740,2022:61221,2023:71283,2024:76695},  # Ávila
    '09': {2016:26560,2017:29493,2018:33146,2019:46097,2020:50378,2021:54744,2022:61225,2023:71287,2024:76699},  # Burgos
    '24': {2016:26575,2017:29508,2018:33161,2019:46112,2020:50393,2021:54759,2022:61240,2023:71302,2024:76714},  # León
    '34': {2016:26585,2017:29518,2018:33171,2019:46122,2020:50403,2021:54769,2022:61250,2023:71312,2024:76724},  # Palencia
    '37': {2016:26588,2017:29521,2018:33174,2019:46125,2020:50406,2021:54772,2022:61253,2023:71315,2024:76727},  # Salamanca
    '40': {2016:26591,2017:29524,2018:33177,2019:46128,2020:50409,2021:54775,2022:61256,2023:71318,2024:76730},  # Segovia
    '42': {2016:26593,2017:29526,2018:33179,2019:46130,2020:50411,2021:54777,2022:61258,2023:71320,2024:76732},  # Soria
    '47': {2016:26598,2017:29531,2018:33184,2019:46135,2020:50416,2021:54782,2022:61263,2023:71325,2024:76737},  # Valladolid
    '49': {2016:26600,2017:29533,2018:33186,2019:46137,2020:50418,2021:54784,2022:61265,2023:71327,2024:76739},  # Zamora
}

PROV_NOMBRES = {
    '05':'Ávila','09':'Burgos','24':'León','34':'Palencia',
    '37':'Salamanca','40':'Segovia','42':'Soria','47':'Valladolid','49':'Zamora'
}

_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def descargar_csv(tpx_id):
    url = f'https://www.ine.es/jaxi/files/tpx/es/csv_bd/{tpx_id}.csv'
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode('latin-1', errors='replace')


def parsear_csv(content):
    nacimientos = {}
    defunciones = {}
    reader = csv.DictReader(io.StringIO(content), delimiter='\t')
    for row in reader:
        muni     = (row.get('Municipios') or '').strip()
        fenomeno = (row.get('Fenómeno demográfico') or '').strip().lower()
        total    = (row.get('Total') or '0').strip().replace('.', '').replace('\xa0', '')

        m = re.match(r'^(\d{5})', muni)
        if not m:
            continue
        cod = m.group(1)

        try:
            valor = int(total)
        except ValueError:
            valor = 0

        if 'nacidos vivos' in fenomeno:
            nacimientos[cod] = valor
        elif 'fallecidos' in fenomeno:
            defunciones[cod] = valor

    return nacimientos, defunciones


# ── Descarga ──────────────────────────────────────────────────────────────────

nacim_data = {}  # {cod_ine: {año: count}}
defun_data = {}  # {cod_ine: {año: count}}

total_req = len(AÑOS) * len(TPX)
req_n = 0

for año in AÑOS:
    print(f'\nAño {año}:')
    for prov_cod, tpx_por_año in TPX.items():
        tpx = tpx_por_año[año]
        nombre = PROV_NOMBRES[prov_cod]
        req_n += 1
        print(f'  [{req_n}/{total_req}] {nombre} (tpx={tpx})...', end=' ', flush=True)

        try:
            content = descargar_csv(tpx)
            nacim, defun = parsear_csv(content)
            for cod, val in nacim.items():
                nacim_data.setdefault(cod, {})[año] = val
            for cod, val in defun.items():
                defun_data.setdefault(cod, {})[año] = val
            print(f'{len(nacim)} municipios')
        except Exception as e:
            print(f'ERROR: {e}')

        time.sleep(0.4)  # respetar servidor INE


# ── Construir resultado ───────────────────────────────────────────────────────

print('\nConstruyendo datos_vital...')

todos = set(nacim_data.keys()) | set(defun_data.keys())
resultado = {}

for cod in sorted(todos):
    n_serie = [nacim_data.get(cod, {}).get(a, 0) for a in AÑOS]
    d_serie = [defun_data.get(cod, {}).get(a, 0) for a in AÑOS]
    b_serie = [n - d for n, d in zip(n_serie, d_serie)]

    if sum(n_serie) == 0 and sum(d_serie) == 0:
        continue

    resultado[cod] = {
        'años':        AÑOS,
        'nacimientos': n_serie,
        'defunciones': d_serie,
        'balance':     b_serie,
    }

print(f'  {len(resultado)} municipios con datos vitales')

total_nacim = sum(sum(v['nacimientos']) for v in resultado.values())
total_defun = sum(sum(v['defunciones']) for v in resultado.values())
print(f'  Total nacimientos 2016-2024: {total_nacim:,}')
print(f'  Total defunciones 2016-2024: {total_defun:,}')
print(f'  Balance total: {total_nacim - total_defun:+,}')


# ── Guardar JS ────────────────────────────────────────────────────────────────

json_str = json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))

with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write('// datos_vital.js — Generado por generar_datos_vital.py\n')
    f.write('// Nacimientos y defunciones por municipio de Castilla y León (2016-2024)\n')
    f.write('// Fuente: INE — Resumen municipal de fenómenos demográficos (Definitivos)\n')
    f.write('// NO editar manualmente.\n\n')
    f.write(f'const DATOS_VITAL = {json_str};\n')

print(f'\nGenerado: {SALIDA}')
